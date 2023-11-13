import base64
from typing import Optional, Tuple

import boto3
from fastapi.responses import RedirectResponse
from mangum.types import LambdaContext
import requests

def getLambdaURL(context: LambdaContext) -> Optional[str]:
    lambdaName = context.function_name
    client = boto3.client("lambda")
    response = client.get_function_url_config(
            FunctionName = lambdaName
            )
    return response.get("FunctionUrl")

def authorizeUser(client_id: str, redirect_url: str): 
    base = "https://accounts.spotify.com/authorize?"
    base += "response_type=code"
    base += f"&client_id={client_id}"
    base += "&scope=user-read-recently-played user-read-email"
    base += f"&redirect_uri={redirect_url}"
    return RedirectResponse(base)

def fetchUserTokens(code: str, client_id: str, client_secret:str , url: str) -> Optional[Tuple[str,str]]:
    base_url = "https://accounts.spotify.com/api/token"
    
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": url,
    }

    encoded = base64.b64encode(
        (client_id + ":" + client_secret).encode("ascii")
    ).decode("ascii")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + encoded,
    }

    tokens = requests.post(base_url, data=payload, headers=headers).json()
    if 'error' in tokens:
        return None

    refresh_token = tokens["refresh_token"]
    access_token = tokens["access_token"]
    return access_token, refresh_token

def fetchUserEmail(access_token: str) -> str:
    email_base_url = "https://api.spotify.com/v1/me"
    email_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    return requests.get(email_base_url, headers=email_headers).json()["email"]

