import os
import requests
from celery import shared_task
from django.http import JsonResponse
from main.models import Organization
from main.integrations.helper import get_channel
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")

# Verify environment variables are loaded
if not CLIENT_ID or not CLIENT_SECRET:
    logger.error("Zoho CLIENT_ID or CLIENT_SECRET environment variables not found")

@shared_task(name="refresh_zoho_tokens")
def refresh_all_zoho_tokens():
    """
    Celery task to refresh Zoho access tokens for all organizations.
    Scheduled to run every 50 minutes.
    """
    logger.info("Starting scheduled Zoho token refresh for all organizations")
    
    organizations = Organization.objects.filter(active=True)
    if not organizations.exists():
        logger.warning("No active organizations found for token refresh")
        return {'success': False, 'error': 'No organizations found'}
    
    refresh_count = 0
    error_count = 0
    
    for organization in organizations:
        try:
            zoho_channel = get_channel(channel_type_num=3, organization=organization)
            
            # Log detailed information about the channel
            logger.info(f"Processing organization {organization.id}: Channel exists: {bool(zoho_channel)}")
            
            if not zoho_channel:
                logger.warning(f"No Zoho channel found for organization {organization.id}")
                continue
                
            if not zoho_channel.credentials:
                logger.warning(f"No credentials found for Zoho channel in organization {organization.id}")
                continue
                
            if not zoho_channel.credentials.key_2:
                logger.warning(f"No refresh token (key_2) found for organization {organization.id}")
                continue
            
            # Log that we're attempting refresh for this organization
            logger.info(f"Attempting to refresh token for organization {organization.id}")
            
            result = refresh_zoho_token(organization_id=organization.id)
            if result.get('success'):
                refresh_count += 1
                logger.info(f"Successfully refreshed token for organization {organization.id}")
            else:
                error_count += 1
                logger.error(f"Failed to refresh token for organization {organization.id}: {result.get('error')}")
        except Exception as e:
            error_count += 1
            logger.exception(f"Exception during token refresh for organization {organization.id}: {str(e)}")
    
    logger.info(f"Zoho token refresh complete. Refreshed: {refresh_count}, Errors: {error_count}")
    return {
        'success': True,
        'refreshed': refresh_count,
        'errors': error_count
    }

@shared_task(name="refresh_zoho_token_for_org")
def refresh_zoho_token(organization_id):
    """
    Celery task to refresh Zoho access token for a specific organization.
    
    Args:
        organization_id: ID of the organization to refresh token for
    
    Returns:
        dict: Result with success status and details
    """
    try:
        if not CLIENT_ID or not CLIENT_SECRET:
            return {'success': False, 'error': 'Missing Zoho client credentials in environment'}
            
        organization = Organization.objects.get(id=organization_id)
        get_channel_data = get_channel(channel_type_num=3, organization=organization)
        
        # Detailed validation of channel data
        if not get_channel_data:
            return {'success': False, 'error': 'No Zoho channel found'}
            
        if not get_channel_data.credentials:
            return {'success': False, 'error': 'No credentials found for Zoho channel'}
            
        if not get_channel_data.credentials.key_2:
            return {'success': False, 'error': 'No refresh token found'}
        
        # Validate auth domain
        if not get_channel_data.credentials.key_4:
            return {'success': False, 'error': 'Auth domain not found in credentials.key_4'}
        
        # Construct token URL
        TOKEN_URL = f"{get_channel_data.credentials.key_4.rstrip('/')}/oauth/v2/token"
        logger.debug(f"Token URL for refresh: {TOKEN_URL}")
        
        # Prepare request data
        data = {
            "refresh_token": get_channel_data.credentials.key_2,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token"
        }
        
        # Log request attempt (excluding sensitive data)
        logger.info(f"Sending refresh request to Zoho for organization {organization_id}")
        
        # Make the request with timeout
        response = requests.post(TOKEN_URL, data=data, timeout=30)
        
        # Log response status
        logger.info(f"Received response from Zoho. Status code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                token_data = response.json()
                logger.debug(f"Response keys: {', '.join(token_data.keys())}")
                
                if "access_token" in token_data:
                    new_access_token = token_data.get("access_token")
                    api_domain = token_data.get("api_domain", get_channel_data.credentials.key_3)
                    
                    # Log token update
                    logger.info(f"Updating access token for organization {organization_id}")
                    
                    # Update the credentials
                    get_channel_data.credentials.key_1 = new_access_token
                    if api_domain:
                        get_channel_data.credentials.key_3 = api_domain
                    get_channel_data.credentials.save()
                    
                    logger.info(f"Successfully refreshed access token for organization {organization_id}")
                    return {
                        'success': True,
                        'access_token': new_access_token,
                        'api_domain': api_domain
                    }
                else:
                    error_msg = f"No access_token in response. Keys received: {', '.join(token_data.keys())}"
                    logger.error(error_msg)
                    return {'success': False, 'error': error_msg}
            except ValueError as json_err:
                error_msg = f"Invalid JSON response: {str(json_err)}"
                logger.error(error_msg)
                logger.debug(f"Response content: {response.text[:200]}...")
                return {'success': False, 'error': error_msg}
        else:
            error_msg = f"Failed to refresh token. Status: {response.status_code}"
            logger.error(error_msg)
            logger.error(f"Error response: {response.text[:200]}...")
            return {'success': False, 'error': error_msg, 'response': response.text}
            
    except Organization.DoesNotExist:
        logger.error(f"Organization with ID {organization_id} not found")
        return {'success': False, 'error': f'Organization with ID {organization_id} not found'}
    except requests.RequestException as req_err:
        error_msg = f"Request error during token refresh: {str(req_err)}"
        logger.exception(error_msg)
        return {'success': False, 'error': error_msg}
    except Exception as e:
        logger.exception(f"Unexpected exception during token refresh: {str(e)}")
        return {'success': False, 'error': str(e)}

def refresh_the_token(request):
    """
    View function to manually refresh a token for a specific organization
    based on the authenticated user.
    
    This function delegates to the Celery task for the actual refresh.
    """
    try:
        logger.info(f"Manual token refresh requested by user {request.user.id}")
        
        # Verify the user has organizations
        user_orgs = request.user.organization_set.filter(active=True)
        if not user_orgs.exists():
            return JsonResponse({"error": "No active organizations found for user"}, status=400)
        
        organization = user_orgs.first()
        logger.info(f"Refreshing token for organization {organization.id}")
        
        # Call the Celery task synchronously to get immediate result
        result = refresh_zoho_token(organization_id=organization.id)
        
        if result.get('success'):
            # Return a proper JSON response on success
            return JsonResponse({
                "success": True,
                "message": "Token refreshed successfully", 
                "access_token": result.get('access_token')
            })
        else:
            return JsonResponse({"error": result.get('error')}, status=400)
    except Exception as e:
        logger.exception(f"Error in refresh_the_token view: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)