# utils.py

import re

def format_tags(tags):
    """
    Converts a list of tags to a string of Telegram hashtags.
    Example: ['vpn', 'cloud'] -> "#vpn #cloud"
    """
    cleaned = [re.sub(r'\W+', '', tag.lower()) for tag in tags if tag.strip()]
    return ' '.join([f"#{tag}" for tag in cleaned])


def clean_text(text):
    """
    Removes extra whitespace and non-printable characters from text.
    """
    return re.sub(r'\s+', ' ', text.strip())

def shorten_offer_text(text, max_length=200):
    """
    Trims the offer text to a maximum character length.
    """
    text = clean_text(text)
    return text if len(text) <= max_length else text[:max_length].rstrip() + '...'

import os
import logging
from datetime import datetime

def setup_logger(name="bot_logger"):
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)   # <-- This line ensures the folder exists!

    log_file = os.path.join(
        log_dir,
        f"software_bot_{datetime.now().strftime('%Y-%m-%d')}.log"
    )
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid adding multiple handlers in repeated runs
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.propagate = False
    return logger

