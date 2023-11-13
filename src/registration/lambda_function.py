import base64
import os
from typing import Optional, Tuple

import boto3
from fastapi import FastAPI
from fastapi import status
from fastapi.requests import Request
from fastapi.responses import RedirectResponse
from fastapi.responses import FileResponse
from mangum import Mangum
from mangum.types import LambdaContext
import requests

app = FastAPI()
lambda_handler = Mangum(app,lifespan='off')

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

# Merged into a single function becuase AWS Lambda 
# URL doesn't work with redirection (maybe I'm doing smth wrong)
@app.get("/", status_code=status.HTTP_200_OK)
async def main(request: Request, code: Optional[str] = None):
    url = getLambdaURL(request.scope["aws.context"])

    client_id = os.environ.get("client_id")
    client_secret = os.environ.get("client_secret")

    if not client_id or not client_secret:
        return {"message":"Server Error: Missing env variable"}

    if not url:
        return {"message": "Lambda URL isn't properly configured"}

    if code == None:
        return authorizeUser(client_id, url)
    else:
        tokens = fetchUserTokens(code, client_id, client_secret, url)
        if not tokens:
            return {"message":"Unathourized account\nContact mohamedabden21@gmail.com"}

        access_token, refresh_token = tokens

        email = fetchUserEmail(access_token=access_token)

        dynamo = boto3.resource("dynamodb")
        tokens = dynamo.Table("tokens_tf")
        item = {"email": email, "token": access_token, "refresh_token": refresh_token}
        tokens.put_item(Item=item)

        return FileResponse('index.html')
