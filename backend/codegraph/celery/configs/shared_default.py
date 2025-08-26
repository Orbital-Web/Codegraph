from codegraph.celery.constants import CELERY_REDIS_HEALTH_CHECK_INTERVAL, CELERY_RESULT_EXPIRES
from codegraph.configs.app_configs import (
    REDIS_DB_NUMBER_CELERY,
    REDIS_DB_NUMBER_CELERY_RESULTS,
    REDIS_HOST,
    REDIS_PORT,
)

broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_NUMBER_CELERY}"

result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_NUMBER_CELERY_RESULTS}"
result_expires = CELERY_RESULT_EXPIRES

redis_socket_keepalive = True
redis_retry_on_timeout = True
redis_backend_health_check_interval = CELERY_REDIS_HEALTH_CHECK_INTERVAL

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

timezone = "UTC"
enable_utc = True
