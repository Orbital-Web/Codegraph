import os

### General
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()

READINESS_TIMEOUT = int(os.getenv("READINESS_TIMEOUT", "60"))
READINESS_INTERVAL = int(os.getenv("READINESS_INTERVAL", "5"))


### DB Configs
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
POSTGRES_DB = "postgres"

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")

POSTGRES_READONLY_USER = os.getenv("POSTGRES_READ_ONLY_USER", "postgres_readonly")
POSTGRES_READONLY_PASSWORD = os.getenv("POSTGRES_READ_ONLY_PASSWORD", "password")


### Index Configs
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
CHROMA_TENANT = "default_tenant"
CHROMA_DB = "default_database"


### Redis Configs
REDIS_HOST = "localhost"
REDIS_PORT = 6379

REDIS_DB_NUMBER = int(os.getenv("REDIS_DB_NUMBER", "0"))  # for general use
REDIS_DB_NUMBER_CELERY = int(os.getenv("REDIS_DB_NUMBER_CELERY", "15"))
REDIS_DB_NUMBER_CELERY_RESULTS = int(os.getenv("REDIS_DB_NUMBER_CELERY_RESULTS", "14"))


### Model Server Configs
MODEL_SERVER_HOST = "localhost"
MODEL_SERVER_PORT = 9000

MODEL_SERVER_MAX_RETRIES = 3
MODEL_SERVER_RETRY_WAIT_MS = 100

MODEL_SERVER_ALLOW_USE_GPU = os.getenv("MODEL_SERVER_ALLOW_USE_GPU", "true").lower() == "true"
MODEL_SERVER_GPU_MAX_BATCH_SIZE = int(
    os.getenv("MODEL_SERVER_GPU_MAX_BATCH_SIZE", "16")
)  # batch size to pass to GPU, tune based on GPU memory, chunk size, and model
MODEL_SERVER_GPU_BATCH_WAIT_MS = int(
    os.getenv("MODEL_SERVER_GPU_BATCH_WAIT_MS", "10")
)  # ms to wait after receiving first request to collect a bigger batch for higher GPU throughput


### MCP Server Configs
NATIVE_MCP_SERVER_HOST = "localhost"
NATIVE_MCP_SERVER_PORT = 9100

NATIVE_MCP_TOOL_PREFIX = "cg"  # used to determine if a tool is native or not
INTERNAL_TOOL_CALL_ERROR_FLAG = "[ITCError]"  # used to differentiate from other tool call errors
