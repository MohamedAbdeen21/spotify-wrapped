from jinja2 import Environment

def landingPage(message: str, show_closing_message: bool):
    env = Environment()
    template = env.from_string("""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Registration Result - Spotify</title>
        <style>
            body {
                font-family: 'Helvetica', sans-serif;
                background: linear-gradient(to right, #0B0B0B, #1DB954);
                color: #fff;
                text-align: center;
                padding: 50px;
                margin: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
            }

            .container {
                max-width: 600px;
                background: linear-gradient(to right, #1E1E1E, #0D0D0D);
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
            }

            .spotify-logo {
                width: 20%;
                max-width: 50%;
                margin-bottom: 20px;
            }

            .message {
                font-size: 24px;
                margin-bottom: 30px;
            }

            .closing-message {
                font-size: 18px;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
        <img src="https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_RGB_White.png" alt="Spotify Logo" class="spotify-logo">
            <div class="message">
                <p>{{ message }}</p>
            </div>
            {% if show_closing_message %}
            <div class="closing-message">
                <p>You can close this window now.</p>
            </div>
            {% endif %}
        </div>
    </body>
    </html>
    """
    )

    result_html = template.render(message=message, show_closing_message=show_closing_message)

    return result_html
