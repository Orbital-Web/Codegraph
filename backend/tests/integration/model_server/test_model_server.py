from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest
from requests.exceptions import HTTPError

from codegraph.model_service.client import count_tokens, embed_texts


def test_count_tokens() -> None:
    count1 = count_tokens("")
    count2 = count_tokens("hello")
    count3 = count_tokens("hello world")

    assert count1 == 0
    assert count3 > count2


def test_count_tokens_concurrent() -> None:
    text_base = (
        "We're no strangers to love, You know the rules and so do I. A full commitment's what I'm "
        "thinking of, You wouldn't get this from any other guy. I just wanna tell you how I'm "
        "feeling, Gotta make you understand. Never gonna give you up, Never gonna let you down, "
        "Never gonna run around and desert you. Never gonna make you cry, Never gonna say goodbye, "
        "Never gonna tell a lie and hurt you."
    ).split()
    texts = [" ".join(text_base[:i]) for i in range(len(text_base))]

    # get result sequentially
    counts_truth = [count_tokens(text) for text in texts]

    # get result concurrently and verify consistency
    with ThreadPoolExecutor() as executor:
        counts = list(executor.map(count_tokens, texts))

    assert len(counts) == len(counts_truth)

    prev = 0
    for count, count_truth in zip(counts, counts_truth):
        assert count == count_truth
        assert count >= prev
        prev = count


def test_embed() -> None:
    texts = ["hello world", "how are you", "hello world"]
    embeddings1 = np.array(embed_texts(texts))
    norms1 = np.linalg.norm(embeddings1, axis=1)

    assert embeddings1.shape[0] == 3
    assert np.allclose(norms1, np.ones(3), atol=1e-5)
    assert np.allclose(embeddings1[0, :], embeddings1[2, :], atol=1e-5)

    # make sure the embeddings aren't just all the same
    assert not np.allclose(embeddings1[0, :], embeddings1[1, :], atol=1e-5)

    embeddings2 = np.array(embed_texts(texts, normalize=False))
    norms2 = np.linalg.norm(embeddings2, axis=1)

    # the default model is not a normalized embedding model, thus norm != 1
    assert embeddings2.shape[0] == 3
    assert not np.allclose(norms2, np.ones(3), atol=1e-5)
    assert np.allclose(embeddings2 / norms2[:, np.newaxis], embeddings1, atol=1e-5)


def test_embed_concurrent() -> None:
    texts_all = ["hello world", "nice to meet you", "def test():\n    return 'test'"]
    texts1 = ["hello world", "nice to meet you"]
    texts2 = ["nice to meet you", "def test():\n    return 'test'"]

    # get embeddings
    embeddings_truth = np.array(embed_texts(texts_all))

    # get embeddings concurrently and verify consistency
    with ThreadPoolExecutor() as executor:
        embeddings12 = [np.array(emb) for emb in executor.map(embed_texts, [texts1, texts2])]

    assert np.allclose(embeddings12[0][1, :], embeddings12[1][0, :], atol=1e-5)
    assert np.allclose(embeddings12[0][0, :], embeddings_truth[0, :], atol=1e-5)
    assert np.allclose(embeddings12[0][1, :], embeddings_truth[1, :], atol=1e-5)
    assert np.allclose(embeddings12[1][1, :], embeddings_truth[2, :], atol=1e-5)

    # make sure the embeddings aren't just all the same
    assert not np.allclose(embeddings_truth[0, :], embeddings_truth[1, :], atol=1e-5)
    assert not np.allclose(embeddings_truth[2, :], embeddings_truth[1, :], atol=1e-5)

    # do a mix of normalized and un-normalized requests
    unnormalized_truth = np.array(embed_texts(texts_all, normalize=False))
    with ThreadPoolExecutor() as executor:
        mixed_embeddings12 = [
            np.array(emb) for emb in executor.map(embed_texts, [texts1, texts2], [True, False])
        ]

    assert not np.allclose(mixed_embeddings12, embeddings12, atol=1e-5)
    assert np.allclose(mixed_embeddings12[0][0, :], embeddings_truth[0, :], atol=1e-5)
    assert np.allclose(mixed_embeddings12[0][1, :], embeddings_truth[1, :], atol=1e-5)
    assert np.allclose(mixed_embeddings12[1][0, :], unnormalized_truth[1, :], atol=1e-5)
    assert np.allclose(mixed_embeddings12[1][1, :], unnormalized_truth[2, :], atol=1e-5)


def test_embed_rejects_empty_list() -> None:
    texts: list[str] = []
    with pytest.raises(HTTPError):
        embed_texts(texts)


def test_embed_rejects_list_with_empty_string() -> None:
    texts = ["hello world", ""]
    with pytest.raises(HTTPError):
        embed_texts(texts)
