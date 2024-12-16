import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# API Settings
API_BASE_URL = os.getenv("API_BASE_URL")
FINMIND_TOKEN = os.getenv("FINMIND_TOKEN")

# Server Settings
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", 8000))

# Logging Settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"