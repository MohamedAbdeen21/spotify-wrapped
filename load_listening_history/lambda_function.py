import boto3
import requests
from datetime import datetime
import base64
import os


def refreshTokens(refresh_token: str) -> dict[str:str]:
    client_id = os.environ.get("client_id")
    client_secret = os.environ.get("client_secret")

    encoded = base64.b64encode(
        (client_id + ":" + client_secret).encode("ascii")
    ).decode("ascii")

    refresh_url = "https://accounts.spotify.com/api/token"

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + encoded,
    }

    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}

    response = requests.post(refresh_url, data=data, headers=headers).json()

    result = {}
    result["access_token"] = response["access_token"]

    if response.get("refresh_token", False):
        result["refresh_token"] = response.get("refresh_token")

    return result


def getRecents(
    email: str, token: str, refresh_token: str, dynamo_table
) -> list[dict[str, str]]:

    new_tokens = refreshTokens(refresh_token)
    token = new_tokens["access_token"]
    refresh_token = new_tokens.get("refresh_token", refresh_token)
    dynamo_table.update_item(
        Key={"email": email},
        UpdateExpression=f"SET #t = :t, #r = :r",
        ExpressionAttributeValues={":r": refresh_token, ":t": token},
        ExpressionAttributeNames={"#t": "token", "#r": "refresh_token"},
    )

    recents = requests.get(
        "https://api.spotify.com/v1/me/player/recently-played?limit=50",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )

    items = recents.json()["items"]

    # rows = [["name", "popularity", "duration_ms", "album", "played_at"]]
    rows = []
    for item in items:
        track = item["track"]
        try:
            time_stamp = int(
                datetime.timestamp(
                    datetime.strptime(item["played_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
                )
            )
        except ValueError:
            time_stamp = int(
                datetime.timestamp(
                    datetime.strptime(item["played_at"], "%Y-%m-%dT%H:%M:%SZ")
                )
            )
        rows.append(
            {
                "email": email,
                "name": track["name"],
                "popularity": track["popularity"],
                "duration_seconds": int(track["duration_ms"] / 1000),
                "album_name": track["album"]["name"],
                "timestamp": time_stamp,
            }
        )

    return rows


def lambda_handler(events, context):
    dynamo = boto3.resource("dynamodb")
    tokens = dynamo.Table("tokens")
    items = tokens.scan()["Items"]
    history = dynamo.Table("listening_history")
    for item in items:
        email = item["email"]
        token = item["token"]
        refresh_token = item["refresh_token"]

        recents = getRecents(email, token, refresh_token, tokens)
        with history.batch_writer() as writer:
            for recent in recents:
                writer.put_item(recent)
    return {"message": "success"}
