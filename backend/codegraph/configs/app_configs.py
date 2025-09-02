import os

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


### General
READINESS_TIMEOUT = int(os.getenv("READINESS_TIMEOUT", "60"))
READINESS_INTERVAL = int(os.getenv("READINESS_INTERVAL", "5"))
