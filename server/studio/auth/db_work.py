"""Keep synchronous transactions off the ASGI loop and settle them before cleanup."""

import asyncio
from collections.abc import Callable

from starlette.concurrency import run_in_threadpool


async def run_db[**P, T](function: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    # Use Starlette/AnyIO's bounded worker pool. The callable owns the entire
    # transaction; no Session is shared across an await or between workers.
    work = asyncio.create_task(run_in_threadpool(function, *args, **kwargs))
    try:
        return await asyncio.shield(work)
    except asyncio.CancelledError:
        # A Python thread cannot be cancelled. Let its bounded DB transaction
        # settle before caller cleanup can release/fence a still-running commit.
        while not work.done():
            try:
                await asyncio.shield(work)
            except asyncio.CancelledError:
                continue
            except Exception:  # noqa: BLE001 -- preserve cancellation; consume worker failure.
                break
        if not work.cancelled():
            work.exception()
        raise
