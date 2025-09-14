import os

LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE = os.getenv("LLM_API_BASE")

MAX_LLM_RETRIES = int(os.getenv("MAX_LLM_RETRIES", "3"))
