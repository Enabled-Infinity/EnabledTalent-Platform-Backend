import os
import requests
from dotenv import load_dotenv
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View
from main.models import APICredentials
from main.integrations.helper import get_channel,create_channel
load_dotenv()

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REDIRECT_URI = "http://127.0.0.1:8000/api/channels/zoho/auth/callback"
TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"

######################## Redirect to Zoho OAuth authorization page
def zoho_auth_init(request):
    auth_url = "https://accounts.zoho.com/oauth/v2/auth"
    params = {
        "scope": "ZohoCRM.modules.ALL",
        "client_id": CLIENT_ID,
        "response_type": "code",
        "access_type": "offline",
        "redirect_uri": REDIRECT_URI,
        "prompt": "consent"
    }
    redirect_url = f"{auth_url}?" + "&".join([f"{key}={value}" for key, value in params.items()])
    return redirect(redirect_url)

#################################### OAuth callback
def zoho_auth_callback(request):
    code = request.GET.get("code")
    if not code:
        return JsonResponse({"error": "Authorization code not found"}, status=400)
    
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
        ################ SAVE THE TOKENS ###########################
        access_token = token_info.get("access_token")
        refresh_token = token_info.get("refresh_token")
        user= request.user
        organization= user.organization_set.all()[0]
        try:
            zoho_channel= get_channel(channel_type_num=3, organization=organization)
        except Exception:
            zoho_channel= create_channel(channel_type_num=3, organization=organization)
        
        if zoho_channel.credentials is None:
            credentials = APICredentials.objects.create(key_1=access_token, key_2=refresh_token)
            zoho_channel.credentials = credentials
        else:
            zoho_channel.credentials.key_1= access_token
            zoho_channel.credentials.key_2= refresh_token
            zoho_channel.credentials.save()
        zoho_channel.save()
        print("Access_token" + access_token, "refresh_token" + refresh_token)
        print("Access_toke" + zoho_channel.credentials.key_1, "refresh_token" + zoho_channel.credentials.key_2)
    return JsonResponse(response.json())

#################################### Fetch Leads from Zoho CRM
def fetch_zoho_leads(request):
    organization= request.user.organization_set.all()[0]
    get_data= get_channel(channel_type_num=3, organization=organization)
    print(get_data.credentials.key_1)
    access_token= get_data.credentials.key_1 ####### it will fetch from database by the requested user
    if not access_token:
        access_token = refresh_the_token()
        if not access_token:
            return JsonResponse({"error": "Unable to refresh access token. Please reauthenticate."}, status=400)

    api_url = "https://www.zohoapis.com/crm/v2/Leads"
    headers = {"Authorization":f"Zoho-oauthtoken {access_token}"}
    response = requests.get(api_url, headers=headers)
    return JsonResponse(response.json())
    
    
def refresh_the_token(request):
    organization= request.user.organization_set.all()[0]
    get_channel_data= get_channel(channel_type_num=3, organization=organization)
    data = {
        "refresh_token": get_channel_data.credentials.key_2, ######### FETCH FROM DATABASE 
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }

    response = requests.post(TOKEN_URL, data=data)
    token_data = response.json()

    if "access_token" in token_data:
        new_access_token = token_data["access_token"]
        os.getenv["ZOHO_ACCESS_TOKEN"] = new_access_token  ########## SAVE NEW TOKEN AND REPLACE IT WITH ACCESS TOKEN
        #os.getenv("ZOHO_ACCESS_TOKEN") = new_access_token
        get_channel_data.credentials.key_1= new_access_token
        return JsonResponse({"access_token": new_access_token})
    else:
        return JsonResponse({"error": "Failed to refresh access token", "details": token_data}, status=400)
