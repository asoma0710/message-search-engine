"""
Message Search Engine Service (FastAPI)

- Calls the external November 7 /messages/ API
- Caches messages in memory (background preload + periodic refresh)
- Exposes:
    - GET /health     -> simple health check
    - GET /messages/  -> paginated messages (skip, limit) from cache
    - GET /search     -> text search with pagination (q, page, page_size)
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# ================== CONFIG ==================

EXTERNAL_API_BASE_URL = "https://november7-730026606190.europe-west1.run.app"
# NOTE: trailing slash (important, server redirects /messages -> /messages/)
MESSAGES_ENDPOINT = f"{EXTERNAL_API_BASE_URL}/messages/"

# how many items to fetch per call to external API
EXTERNAL_SKIP_DEFAULT = 0
EXTERNAL_LIMIT_DEFAULT = 100

CACHE_TTL_SECONDS = 60          # how long we consider cached data "fresh"
MAX_CACHE_SIZE = 10_000         # cap messages in cache
REQUEST_TIMEOUT_SECONDS = 5     # timeout for external API call
BACKGROUND_REFRESH_SECONDS = 60 # how often to refresh messages in background

app = FastAPI(
    title="Message Search Engine",
    description="A simple search engine on top of the November7 /messages API.",
    version="1.0.0",
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("search_engine")


# ================== MODELS ==================

class Message(BaseModel):
    id: str
    user_id: str
    user_name: str
    timestamp: str
    message: str


class SearchResponse(BaseModel):
    total: int
    items: List[Message]
    page: int
    page_size: int
    query: str
    response_time_ms: float


class PaginatedMessages(BaseModel):
    total: int
    items: List[Message]


# ================== SIMPLE IN-MEMORY CACHE ==================

class MessagesCache:
    def __init__(self) -> None:
        self._messages: List[Message] = []
        self._expires_at: Optional[datetime] = None

    @property
    def is_valid(self) -> bool:
        return self._expires_at is not None and datetime.utcnow() < self._expires_at

    @property
    def messages(self) -> List[Message]:
        return self._messages

    def set(self, messages: List[Message]) -> None:
        # Keep size under control
        if len(messages) > MAX_CACHE_SIZE:
            messages = messages[:MAX_CACHE_SIZE]

        self._messages = messages
        self._expires_at = datetime.utcnow() + timedelta(seconds=CACHE_TTL_SECONDS)
        logger.info(
            "Cache updated: %d messages (valid until %s)",
            len(self._messages),
            self._expires_at.isoformat() if self._expires_at else "None",
        )


messages_cache = MessagesCache()


# ================== EXTERNAL API CALL ==================

async def fetch_messages_from_api(
    skip: int = EXTERNAL_SKIP_DEFAULT,
    limit: int = EXTERNAL_LIMIT_DEFAULT,
) -> List[Message]:
    """
    Call the external /messages/ API and parse the result as a list of Message.

    We fetch a single page (skip, limit). For the assignment, searching over
    this subset is acceptable. You can later extend to fetch all pages.
    """
    logger.info(
        "Fetching messages from external API: %s (skip=%d, limit=%d)",
        MESSAGES_ENDPOINT, skip, limit,
    )

    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,  # important for 307 redirects
        ) as client:
            resp = await client.get(
                MESSAGES_ENDPOINT,
                params={"skip": skip, "limit": limit},
            )

        if resp.status_code != 200:
            logger.error(
                "Unexpected status from external messages API: %s",
                resp.status_code,
            )
            raise HTTPException(
                status_code=502,
                detail=f"Unexpected status from external messages API: {resp.status_code}",
            )

    except httpx.RequestError as e:
        logger.error("Error reaching external messages API: %s", e)
        # message may be empty string, that's okay
        raise HTTPException(
            status_code=503,
            detail=f"Error reaching external messages API: {str(e)}",
        ) from e

    data = resp.json()

    # External API returns: {"total": ..., "items": [ ... ]}
    if isinstance(data, dict) and "items" in data:
        raw_items = data["items"]
        total = data.get("total", len(raw_items))
        logger.info(
            "External API returned %d items (total=%d) for this page",
            len(raw_items), total,
        )
    else:
        # Fallback: treat it as a raw list
        raw_items = data
        logger.info("External API returned %d items (no 'total' field)", len(raw_items))

    messages = [Message(**item) for item in raw_items]
    return messages


async def refresh_messages_once() -> None:
    """
    Fetch messages from external API (one page) and update the cache.
    """
    messages = await fetch_messages_from_api()
    messages_cache.set(messages)


async def get_messages() -> List[Message]:
    """
    Return messages, using cache if still valid.
    If cache is empty (e.g. startup fetch failed), we try to fetch once.
    """
    if messages_cache.is_valid and messages_cache.messages:
        return messages_cache.messages

    logger.info("Cache is empty or expired; refreshing now...")
    await refresh_messages_once()
    return messages_cache.messages


# ================== BACKGROUND TASKS ==================

async def background_refresh_loop():
    """
    Periodically refresh the messages cache in the background.

    This keeps the cache warm, so /search and /messages/ do not block on the
    external API most of the time.
    """
    # Small initial delay so that startup finishes cleanly
    await asyncio.sleep(1)

    while True:
        try:
            logger.info("Background refresh: updating messages cache...")
            await refresh_messages_once()
        except HTTPException as e:
            logger.error("Background refresh failed (HTTPException): %s", e.detail)
        except Exception as e:
            logger.exception("Background refresh failed (unexpected): %s", e)
        finally:
            await asyncio.sleep(BACKGROUND_REFRESH_SECONDS)


@app.on_event("startup")
async def on_startup():
    """
    At app startup:
    1. Preload messages once into cache.
    2. Start the background refresh loop.
    """
    logger.info("App startup: preloading messages and starting background refresh...")

    try:
        await refresh_messages_once()
    except HTTPException as e:
        logger.error("Initial preload failed (HTTPException): %s", e.detail)
    except Exception as e:
        logger.exception("Initial preload failed (unexpected): %s", e)

    asyncio.create_task(background_refresh_loop())


# ================== SEARCH LOGIC ==================

def matches_query(msg: Message, q: str) -> bool:
    """
    Very simple case-insensitive substring search over user_name, user_id and message.
    """
    if not q:
        return True

    q = q.lower().strip()
    if not q:
        return True

    haystack = f"{msg.user_name} {msg.user_id} {msg.message}".lower()
    return q in haystack


def sort_results(results: List[Message]) -> List[Message]:
    """
    Sort results by timestamp (newest first).
    If timestamp parsing fails, use minimal date.
    """
    def parse_ts(m: Message):
        try:
            # Handle both "...Z" and normal ISO
            return datetime.fromisoformat(m.timestamp.replace("Z", "+00:00"))
        except Exception:
            return datetime.min

    return sorted(results, key=parse_ts, reverse=True)


# ================== ENDPOINTS ==================

@app.get("/health", tags=["internal"])
async def health():
    return {"status": "ok"}


@app.get(
    "/messages/",
    response_model=PaginatedMessages,
    tags=["internal"],
)
async def list_cached_messages(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=500, description="Number of items to retrieve"),
):
    """
    Return paginated messages from the in-memory cache, similar to the
    external November 7 /messages/ endpoint.

    This does NOT call the external API on each request; it uses the
    cached data loaded and refreshed in the background.
    """
    all_messages = await get_messages()
    total = len(all_messages)
    items = all_messages[skip : skip + limit]
    return PaginatedMessages(total=total, items=items)


@app.get(
    "/search",
    response_model=SearchResponse,
    tags=["search"],
)
async def search_messages(
    q: str = Query("", description="Search query string"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page (max 100)"),
):
    """
    Search messages by query `q` (case-insensitive substring search) and return
    paginated results.

    Thanks to background caching, this endpoint usually does not call
    the external API and can respond in under 100ms for typical loads.
    """
    start = time.perf_counter()

    all_messages = await get_messages()

    # Filter
    filtered = [m for m in all_messages if matches_query(m, q)]

    # Sort
    filtered = sort_results(filtered)

    total = len(filtered)

    # Pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_items = filtered[start_idx:end_idx]

    elapsed_ms = (time.perf_counter() - start) * 1000.0

    return SearchResponse(
        total=total,
        items=page_items,
        page=page,
        page_size=page_size,
        query=q,
        response_time_ms=round(elapsed_ms, 2),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
