from time import monotonic, sleep

import requests

from codegraph.configs.app_configs import (
    MODEL_SERVER_HOST,
    MODEL_SERVER_PORT,
    READINESS_INTERVAL,
    READINESS_TIMEOUT,
)
from codegraph.model_service.shared_models import (
    CountTokensRequest,
    CountTokensResponse,
    EmbedRequest,
    EmbedResponse,
)
from codegraph.utils.logging import get_logger

logger = get_logger()


def count_tokens(text: str) -> int:
    req = CountTokensRequest(text=text)
    resp = requests.post(
        f"http://{MODEL_SERVER_HOST}:{MODEL_SERVER_PORT}/count_tokens", json=req.model_dump()
    )
    resp.raise_for_status()
    result = CountTokensResponse(**resp.json())
    return result.token_count


def embed_texts(texts: list[str]) -> list[list[float]]:
    req = EmbedRequest(texts=texts)
    resp = requests.post(
        f"http://{MODEL_SERVER_HOST}:{MODEL_SERVER_PORT}/embed", json=req.model_dump()
    )
    resp.raise_for_status()
    result = EmbedResponse(**resp.json())
    return result.embeddings


def wait_for_model_server() -> bool:
    logger.info("Model Server: readiness probe starting")

    start_time = monotonic()
    ready = False

    while True:
        try:
            if requests.get(f"http://{MODEL_SERVER_HOST}:{MODEL_SERVER_PORT}/health"):
                ready = True
                break
        except Exception:
            pass

        elapsed = monotonic() - start_time
        if elapsed > READINESS_TIMEOUT:
            break

        logger.warning(
            f"Model Server: readiness probe ongoing, elapsed: {elapsed:.1f}s "
            f"timeout={READINESS_TIMEOUT:.1f}s)"
        )
        sleep(READINESS_INTERVAL)

    if not ready:
        logger.error(f"Model Server: readiness probe did not succeed in {READINESS_TIMEOUT}")
        return False

    logger.info(f"Model Server: readiness probe succeeded")
    return True
