import boto3
import requests
import base64
import os
from typing import Optional
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi import status
from mangum import Mangum

app = FastAPI()
lambda_handler = Mangum(app,lifespan='off')

client_id = os.environ.get("client_id")
client_secret = os.environ.get("client_secret")
url = os.environ.get("own_lambda_url")

# Merged into a single call becuase AWS Lambda 
# URL doesn't work with redirection
@app.get("/", status_code=status.HTTP_200_OK)
async def main(code: Optional[str] = None):
    if not client_id or not client_secret or not url:
        return {"message":"Server Error: Missing env variable"}
    if code == None:
        base = "https://accounts.spotify.com/authorize?"
        base += "response_type=code"
        base += f"&client_id={client_id}"
        base += "&scope=user-read-recently-played user-read-email"
        base += f"&redirect_uri={url}/"
        return RedirectResponse(base)
    else:
        encoded = base64.b64encode(
            (client_id + ":" + client_secret).encode("ascii")
        ).decode("ascii")

        base = "https://accounts.spotify.com/api/token"
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": f"{url}/",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Basic " + encoded,
        }

        tokens = requests.post(base, data=payload, headers=headers).json()
        if 'error' in tokens:
            return {"message":"Failed Unauthorized access\nContact: Mohamedabden21@gmail.com"}
        refresh_token = tokens["refresh_token"]
        access_token = tokens["access_token"]

        email_base_url = "https://api.spotify.com/v1/me"
        email_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        email = requests.get(email_base_url, headers=email_headers).json()["email"]

        dynamo = boto3.resource("dynamodb")
        tokens = dynamo.Table("tokens_tf")
        item = {"email": email, "token": access_token, "refresh_token": refresh_token}
        tokens.put_item(Item=item)

        return {"message": "success"}
