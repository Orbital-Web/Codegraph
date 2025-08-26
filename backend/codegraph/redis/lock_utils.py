from time import monotonic

from redis.lock import Lock


def extend_lock(lock: Lock, last_locked_at: float) -> float:
    """Extends the lock if apporaching timeout."""
    timeout = lock.timeout

    # if no timeout, no need to extend
    if timeout is None:
        return last_locked_at

    current_time = monotonic()
    if current_time - last_locked_at > timeout / 4:
        lock.extend(timeout, replace_ttl=True)
        return current_time

    return last_locked_at
