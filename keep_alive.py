from flask import Flask
from threading import Thread
import logging

app = Flask(__name__)

# Disable flask logging to keep the console clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def home():
    return "Bot is alive and running!"

import os

def run():
    # Render binds to the PORT environment variable. We default to 8080.
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
