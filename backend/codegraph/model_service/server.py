import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, cast

import torch.nn.functional as F
from fastapi import FastAPI, HTTPException

from codegraph.configs.app_configs import (
    MODEL_SERVER_GPU_BATCH_WAIT_MS,
    MODEL_SERVER_GPU_MAX_BATCH_SIZE,
)
from codegraph.configs.indexing import EMBEDDING_MODEL
from codegraph.model_service.server_utils import (
    get_best_device,
    load_model,
    run_with_retry,
    use_gpu,
)
from codegraph.model_service.shared_models import (
    CountTokensRequest,
    CountTokensResponse,
    EmbedFuture,
    EmbedQueue,
    EmbedRequest,
    EmbedResponse,
    HealthStatus,
)
from codegraph.utils.logging import get_logger

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(f"Starting Model Server with model loaded on device={DEVICE}")

    # if using GPU, spawn batch worker tasks which handle GPU request batching
    if USE_GPU:
        asyncio.create_task(batch_worker())
    yield


app = FastAPI(title="Model Server", lifespan=lifespan)


DEVICE = get_best_device()
USE_GPU = use_gpu()
model = load_model(EMBEDDING_MODEL, DEVICE)
queue: EmbedQueue | None = asyncio.Queue() if USE_GPU else None


@app.get("/health")
async def health_check() -> HealthStatus:
    return HealthStatus()


@app.post("/count_tokens")
async def tokenize(request: CountTokensRequest) -> CountTokensResponse:
    """Returns the token count for a given text."""
    if not request.text:
        return CountTokensResponse(token_count=0)

    loop = asyncio.get_event_loop()
    tokens = await loop.run_in_executor(
        None,
        lambda: run_with_retry(model.tokenizer.encode, request.text, return_tensors="pt"),
    )
    return CountTokensResponse(token_count=tokens.shape[1])


@app.post("/embed")
async def embed(request: EmbedRequest) -> EmbedResponse:
    """Returns a list of normalized embeddings for each text."""
    if not request.texts:
        raise HTTPException(status_code=400, detail="Input texts list cannot be empty.")
    if not all(request.texts):
        raise HTTPException(status_code=400, detail="Input texts cannot contain empty strings.")

    loop = asyncio.get_event_loop()

    # CPU mode: run in thread pool for concurrency
    if not USE_GPU:
        logger.debug(f"Embedding {len(request.texts)} texts on the {DEVICE.upper()}")
        embeddings = await loop.run_in_executor(
            None,
            lambda: run_with_retry(
                model.encode,
                request.texts,
                convert_to_tensor=True,
                normalize_embeddings=request.normalize,
            ),
        )
        return EmbedResponse(embeddings=embeddings.tolist())

    # GPU mode: enqueue request for batching
    fut: EmbedFuture = loop.create_future()
    await cast(EmbedQueue, queue).put((request, fut))
    return await fut


async def batch_worker() -> None:
    """A worker which batches embedding requests in a `MODEL_SERVER_GPU_BATCH_WAIT_MS` window to
    maximize GPU throughput. Should only be used if the model is on the GPU.
    """
    assert queue is not None

    while True:
        # wait for first request
        request, fut = await queue.get()
        batch_texts: list[str] = request.texts.copy()
        futures = [(request, fut)]
        n_requests = 1

        # wait and collect more requests to embed as one batch
        await asyncio.sleep(MODEL_SERVER_GPU_BATCH_WAIT_MS / 1000)
        while not queue.empty():
            try:
                request, fut = queue.get_nowait()
                batch_texts.extend(request.texts)
                futures.append((request, fut))
                n_requests += 1
            except asyncio.QueueEmpty:
                break

        # embed batch and send embeddings back
        try:
            logger.debug(
                f"Embedding {len(batch_texts)} texts from {n_requests} requests on the GPU"
            )
            embs = run_with_retry(
                model.encode,
                batch_texts,
                batch_size=MODEL_SERVER_GPU_MAX_BATCH_SIZE,
                convert_to_tensor=True,
                normalize_embeddings=False,
            )

            # split embeddings back into individual requests
            idx = 0
            for request, fut in futures:
                n = len(request.texts)
                embeddings = embs[idx : idx + n]
                if request.normalize:
                    embeddings = F.normalize(embeddings, p=2, dim=1)
                fut.set_result(EmbedResponse(embeddings=embeddings.tolist()))
                idx += n
        except Exception as e:
            for _, fut in futures:
                fut.set_exception(e)
