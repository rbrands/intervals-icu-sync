import os
from dotenv import load_dotenv

load_dotenv()

API_KEY: str = os.environ.get("INTERVALS_API_KEY", "")
ATHLETE_ID: str = os.environ.get("ATHLETE_ID", "")
if not API_KEY:
    raise ValueError("API key not found. Set INTERVALS_API_KEY in .env")
if not ATHLETE_ID:
    raise ValueError("Athlete ID not found. Set ATHLETE_ID in .env")