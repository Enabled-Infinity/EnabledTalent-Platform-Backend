import os
import requests
from dotenv import load_dotenv
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View

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
        print("Access_toke" + access_token, "refresh_token" + refresh_token)
    return JsonResponse(response.json())

#################################### Fetch Leads from Zoho CRM
def fetch_zoho_leads(request):
    access_token = "aCESStoken" ####### it will fetch from database by the requested user
    if not access_token:
        access_token = refresh_the_token()
        if not access_token:
            return JsonResponse({"error": "Unable to refresh access token. Please reauthenticate."}, status=400)

    api_url = "https://www.zohoapis.com/crm/v2/Leads"
    headers = {"Authorization":f"Zoho-oauthtoken {access_token}"}
    response = requests.get(api_url, headers=headers)
    return JsonResponse(response.json())
    
    
def refresh_the_token(request):

    data = {
        "refresh_token": "FETCH FROM DATABASE", ######### FETCH FROM DATABASE 
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }

    response = requests.post(TOKEN_URL, data=data)
    token_data = response.json()

    if "access_token" in token_data:
        new_access_token = token_data["access_token"]
        os.getenv["ZOHO_ACCESS_TOKEN"] = new_access_token  ########## SAVE NEW TOKEN AND REPLACE IT WITH ACCESS TOKEN
        return JsonResponse({"access_token": new_access_token})
    else:
        return JsonResponse({"error": "Failed to refresh access token", "details": token_data}, status=400)
