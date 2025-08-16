import os

### DB Constants
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
POSTGRES_DB = "postgres"

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")

POSTGRES_READONLY_USER = os.getenv("POSTGRES_READ_ONLY_USER", "postgres_readonly")
POSTGRES_READONLY_PASSWORD = os.getenv("POSTGRES_READ_ONLY_PASSWORD", "password")


### Index Constants
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Salesforce/codet5p-110m-embedding")
