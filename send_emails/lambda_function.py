from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl
import smtplib
import json
import os
import jinja2

def lambda_handler(event, context):
    
    users = json.loads(json.loads(event['Records'][0]['body'])['responsePayload'])
    
    for msg_body in users:
        email_sender = os.environ.get("email_sender")
        email_password = os.environ.get("email_password")
        email_reciever = msg_body['email']
        
        subject = 'Weekly Spotify Wrap'
            
        plays = msg_body['plays']
        artists = msg_body['artists']
        time = msg_body['minutes_played']
        env = jinja2.Environment()
        template = env.from_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HTML Email</title>
        <link rel="stylesheet">
        <style type="text/css">
            .wrapper {
                width: 100%;
                margin: 0 auto;
                table-layout: fixed;
                background-color: #FFFFFF;
                padding-bottom: 60px;
            }

            .main {
                background-color: #000000;
                margin: 0 auto;
                width: 100%;
                max-width: 600px;
                border-spacing: 0;
                font-family: sans-serif;
            }

            .spotify-logo {
                background-color: #000000;
                text-align: center;
            }

            .header-text {
                background-color: #000000;
                color: #F2F2F2;
                text-align: center;
                font-size: 32px;
                margin-top: 0 auto;
                font-weight: bold;
            }

            .total-time {
                background-color: #F92A82;
                color: #FFFFFF;
                text-align: center;
                height: 150px;
                font-size: 24px;
                font-style: italic;
                font-weight: bold;
            }

            .songs {
                background-color: #5BC3EB;
                color: black;
                text-align: center;
                height: 75px;
            }

            .card {
                height: 320px;
                padding-top: 10px;
                color: black;
            }

            .card-text{
                font-size: 16px;
                color: black;
            }

            .artist {
                background-color: #F92A82;
                color:#FFFFFF;
                font-size: 16px;
                margin-top: 0 auto;
                text-align: left;            
                height:75px;
                font-style: italic;
            }

            body {
                margin: 0;
            }

        </style>

    </head>
    <body>
        <div class="wrapper">
            <table class="main">
                <!-- top empty bar -->
                <tr>
                    <td height="8" style="background-color: #FFFFFF;"> </td>
                </tr>

                <!-- header icon -->
                <tr>
                    <td class="spotify-logo">
                    </td>
                </tr>

                <!-- header text -->
                <tr class="header-text" height="300">
                    <td>
                        Your weekly Spotify Wrapped is here!
                    </td>
                </tr>

                <!-- listening time -->
                <tr class="total-time">
                    <td>
                    {% if time < 60%}
                        You played music for {{time}} minutes this week.
                    {% elif time is divisibleby 60 %}
                        You played music for {{time//60}} hours this week.
                    {% else %}
                        You played music for {{time//60}} hours and {{time%60}} minutes this week.
                    {% endif %}
                    </td>
                </tr>
                </table>

                <!-- songs listened -->
                <!-- still in progress, need to design cards -->
                <table class="main">
                    <tr class="songs">
                        <td style="text-align: center; font-family: 'Times New Roman'; font-size: 32px;" colspan="2">
                            Your Top Plays
                        </td>
                    </tr>
                    
                    {% for play in plays %}
                    {% if loop.index in [1,3,5] %}
                    <tr class="songs">
                    {%endif%}
                    {% if (loop.last) and (loop.index in [1,3,5]) %}
                        <td colspan="2">
                    {% else %}
                        <td>
                    {% endif %}
                            <div class="card">
                                <div class="img">
                                    <img src="{{play["image"]}}" width="190px" alt="">
                                </div>
                                <div class="card-text" style="font-weight: bold;">
                                    {{play["name"]}}
                                </div>
                                <div class="card-text" style="font-style: italic;">
                                    {{play["plays"]}} plays: {{play["duration"]}} minutes
                                </div>
                            </div>
                        </td>
                    {% if (loop.index is divisibleby 2) or (loop.last) %}
                    </tr>
                    {% endif %}
                    {% endfor %}
                </table>

                <!-- artist listened -->
                <table class="main">
                    <tr class="artist">
                        <td height="30px" style="text-align: center; font-weight: bold; font-size: 32px;"">
                            Your most listened artists
                        </td>
                    </tr>

                    {% for artist in artists %}
                        <tr class="artist">
                        {% if loop.index is divisibleby 2 %}
                            <td style="text-align: right; padding-right:12%">
                        {% else %}
                            <td style="text-align: left; padding-left:12%">
                        {% endif %}
                            #{{loop.index}} {{artist['name']}} <br> 
                            ({{artist['plays']}} plays: {{artist['duration']}} minutes)
                        </td>
                    </tr>
                    {% endfor %}
                </table>
        </div>

    </body>
    </html>
    """)
        
        
        email = MIMEMultipart()
        email['From'] = email_sender
        email['To'] = email_reciever
        email['Subject'] = subject
        part1 = MIMEText(template.render(plays = plays, artists = artists, time = time),'html')
        email.attach(part1)

        ssl_context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host='smtp.gmail.com',port=465,context=ssl_context) as smtp:
            smtp.login(email_sender, email_password)
            smtp.sendmail(email_sender, email_reciever, email.as_string())

    return {"message":"success"}
