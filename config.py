import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
POST_DELAY = int(os.environ.get("POST_DELAY", "2"))  # default 2 seconds if not set
