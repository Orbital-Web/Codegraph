from asyncio import Future, Queue
from typing import Literal

from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: Literal["ok"] = "ok"


class CountTokensRequest(BaseModel):
    text: str


class CountTokensResponse(BaseModel):
    token_count: int


class EmbedRequest(BaseModel):
    texts: list[str]
    normalize: bool


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]


EmbedFuture = Future[EmbedResponse]
EmbedQueue = Queue[tuple[EmbedRequest, EmbedFuture]]
