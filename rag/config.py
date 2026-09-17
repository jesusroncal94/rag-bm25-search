import os

RETRIEVAL_FLOOR = 0.30

MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
MODEL_API_KEY = os.getenv("MODEL_API_KEY", "")
MODEL_TIMEOUT_SECONDS = 8.0
