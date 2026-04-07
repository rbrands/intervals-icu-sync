import os
from dotenv import load_dotenv

load_dotenv()

API_KEY: str = os.environ.get("INTERVALS_API_KEY", "")
