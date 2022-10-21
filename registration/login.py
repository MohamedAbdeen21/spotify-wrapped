import os
import boto3
import requests
import base64
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from client import client_id, client_secret

app = FastAPI()


@app.get("/")
def root():
    return RedirectResponse("/login/")


@app.get("/home/")
def main(code: str):
    encoded = base64.b64encode(
        (client_id + ":" + client_secret).encode("ascii")
    ).decode("ascii")

    base = "https://accounts.spotify.com/api/token"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://localhost:8000/home/",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + encoded,
    }
    tokens = requests.post(base, data=payload, headers=headers).json()
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
    tokens = dynamo.Table("tokens")
    item = {"email": email, "token": access_token, "refresh_token": refresh_token}
    tokens.put_item(Item=item)

    return {"message": "success"}


@app.get("/login/")
def login():
    base = "https://accounts.spotify.com/authorize?"
    base += "response_type=code"
    base += f"&client_id={client_id}"
    base += "&scope=user-read-recently-played user-read-email"
    base += "&redirect_uri=http://localhost:8000/home/"
