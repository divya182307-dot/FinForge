"""
sec_client.py - Robust SEC EDGAR HTTP client with rate limiting, retries, and caching.

FinAudit AI - Member 1: SEC EDGAR Integration & Financial Extraction
Official SEC API Reference: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
"""

import os
import time
import random
import logging
import threading
from typing import Optional, Dict, Any, Union
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("SECClient")

DEFAULT_USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "FinAuditAI/1.0 (hackathon@finaudit.ai)")
SEC_MAX_REQUESTS_PER_SECOND = 8.0  # SEC limit is 10/s; use 8.0 for a safe safety buffer
REQUEST_TIMEOUT_SECONDS = 30


class SECClientError(Exception):
    """Base exception for SEC EDGAR client errors."""
    pass


class SECNotFoundError(SECClientError):
    """Raised when an SEC resource (CIK, filing, fact) is not found (404)."""
    pass


class SECRateLimitError(SECClientError):
    """Raised when SEC returns 429 Too Many Requests repeatedly."""
    pass


class RateLimiter:
    """Thread-safe token-bucket rate limiter to enforce SEC EDGAR's 10 req/sec maximum."""
    def __init__(self, max_rate: float = SEC_MAX_REQUESTS_PER_SECOND):
        self.interval = 1.0 / max_rate
        self.lock = threading.Lock()
        self.last_request_time = 0.0

    def wait(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.interval:
                time.sleep(self.interval - elapsed)
            self.last_request_time = time.time()


class SECClient:
    """
    Standard HTTP client for SEC EDGAR APIs.
    
    Handles:
    - User-Agent compliance
    - Token bucket rate limiting (<= 8 req/sec)
    - Exponential backoff retry logic
    - In-memory / disk response caching
    """

    def __init__(
        self,
        user_agent: Optional[str] = None,
        max_rate: float = SEC_MAX_REQUESTS_PER_SECOND,
        max_retries: int = 5,
        enable_cache: bool = True
    ):
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.rate_limiter = RateLimiter(max_rate)
        self.max_retries = max_retries
        self.enable_cache = enable_cache
        self._memory_cache: Dict[str, Any] = {}
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, text/html, application/xhtml+xml, */*",
        })

    def get(self, url: str, is_json: bool = True, use_cache: bool = True) -> Union[Dict[str, Any], str, bytes]:
        """
        Perform a rate-limited GET request with exponential backoff retries.
        """
        if use_cache and self.enable_cache and url in self._memory_cache:
            logger.debug("Cache hit for URL: %s", url)
            return self._memory_cache[url]

        attempt = 0
        backoff = 1.0

        while attempt < self.max_retries:
            attempt += 1
            self.rate_limiter.wait()

            try:
                logger.debug("GET (attempt %d/%d): %s", attempt, self.max_retries, url)
                response = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)

                if response.status_code == 200:
                    if is_json:
                        data = response.json()
                    else:
                        data = response.text
                    
                    if self.enable_cache and use_cache:
                        self._memory_cache[url] = data
                    return data

                elif response.status_code == 404:
                    raise SECNotFoundError(f"SEC Resource not found (404): {url}")

                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    sleep_time = float(retry_after) if retry_after else (backoff + random.uniform(0.5, 1.5))
                    logger.warning("SEC Rate limit hit (429) on %s. Sleeping %.2fs", url, sleep_time)
                    time.sleep(sleep_time)
                    backoff *= 2.0
                    continue

                elif response.status_code in (500, 502, 503, 504):
                    sleep_time = backoff + random.uniform(0.2, 0.8)
                    logger.warning("SEC Server error (%d) on %s. Retrying in %.2fs", response.status_code, url, sleep_time)
                    time.sleep(sleep_time)
                    backoff *= 2.0
                    continue

                else:
                    response.raise_for_status()

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                sleep_time = backoff + random.uniform(0.2, 0.8)
                logger.warning("Network error on %s: %s. Retrying in %.2fs", url, e, sleep_time)
                time.sleep(sleep_time)
                backoff *= 2.0
                if attempt >= self.max_retries:
                    raise SECClientError(f"Failed to connect to SEC EDGAR after {self.max_retries} attempts: {e}") from e

        raise SECRateLimitError(f"Failed to retrieve {url} after {self.max_retries} retries.")

    def get_json(self, url: str, use_cache: bool = True) -> Dict[str, Any]:
        """Convenience method to retrieve and parse JSON."""
        return self.get(url, is_json=True, use_cache=use_cache)

    def get_text(self, url: str, use_cache: bool = True) -> str:
        """Convenience method to retrieve text/HTML."""
        return self.get(url, is_json=False, use_cache=use_cache)

    def clear_cache(self):
        """Clear the in-memory response cache."""
        self._memory_cache.clear()

