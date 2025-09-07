from time import sleep
from typing import Any, Callable, Literal, TypeVar

import torch
from sentence_transformers import SentenceTransformer

from codegraph.configs.app_configs import (
    MODEL_SERVER_ALLOW_USE_GPU,
    MODEL_SERVER_MAX_RETRIES,
    MODEL_SERVER_RETRY_WAIT_MS,
)
from codegraph.utils.logging import get_logger

logger = get_logger()


def get_best_device() -> Literal["cuda"] | Literal["mps"] | Literal["cpu"]:
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def use_gpu() -> bool:
    return MODEL_SERVER_ALLOW_USE_GPU and torch.cuda.is_available()


def load_model(model_name: str, device: str) -> SentenceTransformer:
    """Loads the model from local cache, or fallback to downloading the model."""
    try:
        return SentenceTransformer(
            model_name, device=device, trust_remote_code=True, local_files_only=True
        )
    except OSError:
        return SentenceTransformer(model_name, device=device, trust_remote_code=True)


OutputType = TypeVar("OutputType")


def run_with_retry(fn: Callable[..., OutputType], *args: Any, **kwargs: Any) -> OutputType:
    """Runs `fn` a maximum of `MODEL_SERVER_MAX_RETRIES + 1` times, waiting
    `MODEL_SERVER_RETRY_WAIT_MS` on failure. Mainly intended to deal with the occasional
    transformers library "RuntimeError: Already Borrowed" bug.
    """
    for i in range(MODEL_SERVER_MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"Attempt {i+1}: "
                f"Failed to run {fn.__name__} with args {args} and kwargs {kwargs}: {e}"
            )
            sleep(MODEL_SERVER_RETRY_WAIT_MS / 1000)
    return fn(*args, **kwargs)
