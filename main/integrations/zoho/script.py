import os
import requests
import logging
from dotenv import load_dotenv
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View
from main.models import APICredentials
from main.integrations.helper import get_channel, create_channel
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny

logger = logging.getLogger(__name__)

load_dotenv()

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REDIRECT_URI = "http://127.0.0.1:8000/api/channels/zoho/auth/callback"  ############# NEED TO PUT THE CALLBACK URL IN .env
ZOHO_DEFAULT_AUTH_DOMAIN = os.getenv("ZOHO_DEFAULT_AUTH_DOMAIN", "https://accounts.zoho.com")


####### Redirect to Zoho OAuth authorization page ####################
@csrf_exempt
@api_view(("GET",))
@permission_classes([IsAuthenticated])
def zoho_auth_init(request):
    try:
        auth_url = f"{ZOHO_DEFAULT_AUTH_DOMAIN}/oauth/v2/auth"
        params = {
            "scope": "ZohoRecruit.modules.ALL",
            "client_id": CLIENT_ID,
            "response_type": "code",
            "access_type": "offline",
            "redirect_uri": REDIRECT_URI,
            "prompt": "consent"
        }
        redirect_url = f"{auth_url}?" + "&".join([f"{key}={value}" for key, value in params.items()])
        logger.info(f"Redirecting user {request.user.username} to Zoho OAuth page")
        return redirect(redirect_url)
    except Exception as e:
        logger.error(f"Error initiating Zoho OAuth flow: {str(e)}")
        return JsonResponse({"error": "Failed to initiate OAuth flow"}, status=500)


########## OAuth callback ################
@csrf_exempt
@api_view(("GET",))
@permission_classes([IsAuthenticated])
def zoho_auth_callback(request):
    try:
        code = request.GET.get("code")
        auth_domain = request.GET.get("accounts-server", ZOHO_DEFAULT_AUTH_DOMAIN)
        user = request.user
        organization = user.organization_set.all()[0]

        logger.debug(f"Received OAuth callback for user {user.username}, organization {organization.id}")
        
        if not code:
            logger.warning("Authorization code not found in callback")
            return JsonResponse({"error": "Authorization code not found"}, status=400)
        
        TOKEN_URL = f"{auth_domain}/oauth/v2/token"
        data = {
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        response = requests.post(TOKEN_URL, data=data)        

        if response.status_code == 200:
            token_info = response.json()
            access_token = token_info.get("access_token")
            refresh_token = token_info.get("refresh_token")
            api_domain = token_info.get("api_domain")
            domain = api_domain[20:]
            print(refresh_token, "Api_domain: " + api_domain , "domain: " + domain)
            

            try:
                zoho_channel = get_channel(channel_type_num=3, organization=organization)
                logger.debug(f"Found existing Zoho channel for organization {organization.id}")
            except Exception:
                logger.info(f"Creating new Zoho channel for organization {organization.id}")
                zoho_channel = create_channel(channel_type_num=3, organization=organization)
            
            if zoho_channel.credentials is None:
                credentials = APICredentials.objects.create(
                    key_1=access_token,  
                    key_2=refresh_token,  
                    key_3=api_domain,    
                    key_4=auth_domain,
                    key_5=domain  
                )
                zoho_channel.credentials = credentials
            else:
                zoho_channel.credentials.key_1 = access_token
                zoho_channel.credentials.key_2 = refresh_token
                zoho_channel.credentials.key_3 = api_domain
                zoho_channel.credentials.key_4 = auth_domain
                zoho_channel.credentials.key_5 = domain
                zoho_channel.credentials.save()
            
            zoho_channel.save()
            logger.info(f"Successfully saved Zoho credentials for organization {organization.id}")
            
            return JsonResponse({
                "status": "success",
                "message": "Zoho integration successfully authorized"
            })
        else:
            logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
            return JsonResponse({
                "error": "Failed to exchange authorization code for tokens",
                "details": response.text
            }, status=response.status_code)
            
    except Exception as e:
        logger.exception(f"Error in OAuth callback: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


#################################### Fetch Leads from Zoho CRM FOR AUTHENTICATED USER ##################
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def fetch_zoho_recruit_candidates(request):
    """
    Fetches a list of candidates from Zoho Recruit.
    """
    print("Fetching...")
    organization = request.user.organization_set.all()[0]
    channel = get_channel(channel_type_num=3, organization=organization)

    access_token = channel.credentials.key_1
    domain = channel.credentials.key_5  # Retrieved from OAuth response

    if not access_token or not domain:
        return JsonResponse({"error": "No access token or API domain available. Please reauthenticate."}, status=400)

    api_url = f"https://recruit.zoho{domain}/recruit/v2/Candidates" 
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    
    response = requests.get(api_url, headers=headers)

    if response.status_code != 200:
        return JsonResponse({"error": "Failed to fetch candidates", "details": response.json()}, status=response.status_code)

    return JsonResponse(response.json())


@api_view(("GET",))
@permission_classes([IsAuthenticated])
def revoke_zoho_token(request):
    try:
        organization = request.user.organization_set.all()[0]
        get_data = get_channel(channel_type_num=3, organization=organization)

        if not get_data or not get_data.credentials:
            logger.warning(f"No Zoho channel found for organization {organization.id}")
            return JsonResponse({"message": "No active Zoho integration found"}, status=200)

        refresh_token = get_data.credentials.key_2
        auth_domain = get_data.credentials.key_4

        if not refresh_token:
            logger.warning(f"No refresh token to revoke for organization {organization.id}")
            get_data.credentials.key_1 = None
            get_data.credentials.key_2 = None
            get_data.credentials.key_3 = None
            get_data.credentials.key_4 = None
            get_data.credentials.save()
            return JsonResponse({"message": "Zoho integration cleared"})

        if not auth_domain:
            logger.error(f"Auth domain missing for organization {organization.id}")
            return JsonResponse({"error": "Auth domain is missing"}, status=400)

        revoke_url = f"{auth_domain}/oauth/v2/token/revoke?token={refresh_token}"
        
        logger.info(f"Revoking Zoho token for organization {organization.id}")
        response = requests.get(url=revoke_url)
        

        if response.status_code == 200:
            get_data.credentials.key_1 = None
            get_data.credentials.key_2 = None
            get_data.credentials.key_3 = None
            get_data.credentials.key_4 = None
            get_data.credentials.save()
            logger.info(f"Successfully revoked Zoho token for organization {organization.id}")
            return JsonResponse({"message": "Zoho integration successfully disconnected"})
        else:
            logger.warning(f"Token revocation API error: {response.status_code} - {response.text}")
            return JsonResponse({
                "message": "Zoho integration revocation failed",
                "details": response.text
            }, response.status_code())  
            
    except Exception as e:
        logger.exception(f"Error revoking Zoho token: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

    
