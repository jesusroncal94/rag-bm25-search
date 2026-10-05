import os

RETRIEVAL_FLOOR = 0.30

MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen/qwen3.8-27b")
MODEL_API_KEY = os.getenv("MODEL_API_KEY", "")
MODEL_TIMEOUT_SECONDS = 8.0

GROUNDING_THRESHOLD = 0.8
