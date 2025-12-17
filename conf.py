import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("BOT_TOKEN")
USERNAME = os.getenv("API_USERNAME")
API_KEY = os.getenv("API_KEY")

BASE_URL = "https://ftc-api.firstinspires.org/v2.0"
BASE_URL_SCOUT = "https://api.ftcscout.org/graphql"
