from email.message import EmailMessage
import ssl
import smtplib
import json
import os

def lambda_handler(event, context):
    
    msg_body = json.loads(event['Records'][0]['body'])

    
    email_sender = os.environ.get("email_sender")
    email_password = os.environ.get("email_password")
    email_reciever = msg_body['email']
    
    subject = 'Daily Spotify Wrap'
    

    if msg_body['plays'] == []:
        plays = "No plays found."
    else:
        plays = ''
        for i in msg_body['plays']:
            for key, value in i.items():
                plays += f'\t{key}: {value}\n'
            
    body = f"""\nHey {msg_body['email']}, this is a test email.\nYour plays:\n\n{plays}\nTotal minutes played: {msg_body['minutes_played']}"""
    
    
    email = EmailMessage()
    email['From'] = email_sender
    email['To'] = email_reciever
    email['Subject'] = subject
    email.set_content(body)
    
    ssl_context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host='smtp.gmail.com',port=465,context=ssl_context) as smtp:
        smtp.login(email_sender, email_password)
        smtp.sendmail(email_sender, email_reciever, email.as_string())
        
    return {"message":"success"}
