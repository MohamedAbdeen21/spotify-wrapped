import os
from typing import Optional

import boto3
from fastapi import FastAPI
from fastapi import status
from fastapi.requests import Request
from fastapi.responses import  HTMLResponse
from mangum import Mangum

from template import landingPage
from internal import authorizeUser, fetchUserEmail, fetchUserTokens, getLambdaURL

app = FastAPI()
lambda_handler = Mangum(app,lifespan='off')

# Merged into a single function becuase AWS Lambda 
# URL doesn't work with redirection (maybe I'm doing smth wrong)
@app.get("/", status_code=status.HTTP_200_OK)
async def main(request: Request, code: Optional[str] = None):
    url = getLambdaURL(request.scope["aws.context"])

    client_id = os.environ.get("client_id")
    client_secret = os.environ.get("client_secret")

    if not client_id or not client_secret or not url:
        return HTMLResponse(landingPage("Internal Server Error\nPlease contact mohamedabden21@gmail.com", False))

    if code == None:
        return authorizeUser(client_id, url)
    else:
        tokens = fetchUserTokens(code, client_id, client_secret, url)
        if not tokens:
            return HTMLResponse(landingPage("Unauthorized Account\nPlease contact mohamedabden21@gmail.com", False))

        access_token, refresh_token = tokens

        email = fetchUserEmail(access_token=access_token)

        dynamo = boto3.resource("dynamodb")
        tokens = dynamo.Table("tokens_tf")
        item = {"email": email, "token": access_token, "refresh_token": refresh_token}
        tokens.put_item(Item=item)

        return HTMLResponse(landingPage("Registration Successful!", True))
