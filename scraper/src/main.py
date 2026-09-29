from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError


ROOT = Path(__file__).resolve().parent.parent
TARGET_URL = "https://books.toscrape.com/catalogue/page-1.html"
ROBOTS_URL = "https://books.toscrape.com/robots.txt"
DEFAULT_USER_AGENT = "FlyRankInternship-A9/1.0 (+local educational project)"


class FetchFailure(RuntimeError):
    def __init__(self, url: str, reason: str):
        super().__init__(f"{url}: {reason}")
        self.url = url
        self.reason = reason


class BookRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    product_url: HttpUrl
    price_text: str = Field(min_length=1)
    price_gbp: float = Field(ge=0)
    availability_text: str = Field(min_length=1)
    rating_text: str = Field(min_length=1)
    description: str | None = None
    source_page: HttpUrl
    fetched_at: datetime


class Fetcher:
    def __init__(
        self,
        cache_dir: Path,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout_seconds: float = 10.0,
        delay_seconds: float = 0.5,
        client: httpx.Client | None = None,
    ):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay_seconds = max(delay_seconds, 0.5)
        self.client = client or httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": user_agent},
        )
        self.pages_fetched = 0
        self.cache_hits = 0
        self._last_request_at = 0.0

    def cache_path(self, url: str) -> Path:
        parsed = urlparse(url)
        stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", Path(parsed.path).name or "index")
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
        return self.cache_dir / f"{stem}-{digest}.cache"

    @staticmethod
    def _timestamp(path: Path) -> str:
        value = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        return value.isoformat().replace("+00:00", "Z")

    def _wait(self) -> None:
        remaining = self.delay_seconds - (time.monotonic() - self._last_request_at)
        if remaining > 0:
            time.sleep(remaining)

    def fetch(self, url: str) -> tuple[str, str]:
        cache_path = self.cache_path(url)
        if cache_path.exists():
            text = cache_path.read_text(encoding="utf-8")
            self.cache_hits += 1
            print(f"CACHE HIT bytes={len(text.encode('utf-8'))} url={url}")
            return text, self._timestamp(cache_path)

        last_reason = "request failed"
        for attempt in (1, 2):
            self._wait()
            try:
                response = self.client.get(url)
                self._last_request_at = time.monotonic()
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                self._last_request_at = time.monotonic()
                last_reason = type(exc).__name__
                if attempt == 1:
                    time.sleep(1)
                    continue
                raise FetchFailure(url, last_reason) from exc

            if response.status_code == 200:
                cache_path.write_text(response.text, encoding="utf-8")
                self.pages_fetched += 1
                print(f"FETCH status=200 bytes={len(response.content)} url={url}")
                return response.text, self._timestamp(cache_path)

            last_reason = f"HTTP {response.status_code}"
            if response.status_code in {403, 404}:
                raise FetchFailure(url, last_reason)
            if response.status_code >= 500 and attempt == 1:
                time.sleep(1)
                continue
            raise FetchFailure(url, last_reason)

        raise FetchFailure(url, last_reason)


def normalize_price(price_text: str) -> float:
    match = re.search(r"(\d+(?:\.\d{1,2})?)", price_text.replace(",", ""))
    if not match:
        raise ValueError("price does not contain a number")
    try:
        return float(Decimal(match.group(1)))
    except InvalidOperation as exc:
        raise ValueError("price is not a valid decimal") from exc


def absolute_url(href: str, page_url: str) -> str:
    return urljoin(page_url, href)


def discover_catalogue(
    fetcher: Fetcher,
    *,
    start_url: str = TARGET_URL,
    max_pages: int = 3,
) -> tuple[list[str], dict[str, str], int]:
    current_url = start_url
    discovered: list[str] = []
    sources: dict[str, str] = {}
    pages = 0

    while current_url and pages < max_pages:
        html, _ = fetcher.fetch(current_url)
        soup = BeautifulSoup(html, "html.parser")
        links = soup.select("article.product_pod h3 a[href]")
        if not links:
            raise FetchFailure(current_url, "catalogue page contains no book links")
        for link in links:
            product_url = absolute_url(str(link["href"]), current_url)
            discovered.append(product_url)
            sources.setdefault(product_url, current_url)
        pages += 1
        next_link = soup.select_one("li.next a[href]")
        current_url = absolute_url(str(next_link["href"]), current_url) if next_link else ""

    unique_urls = list(dict.fromkeys(discovered))
    print(f"catalogue_pages={pages} discovered={len(discovered)} unique_urls={len(unique_urls)}")
    return unique_urls, sources, pages


def extract_raw_record(html: str, product_url: str, source_page: str, fetched_at: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    product = soup.select_one("div.product_main")
    if product is None:
        raise ValueError("missing product area")

    title_node = product.select_one("h1")
    price_node = product.select_one("p.price_color")
    availability_node = product.select_one("p.availability")
    rating_node = product.select_one("p.star-rating")
    if not all((title_node, price_node, availability_node, rating_node)):
        raise ValueError("missing required product field")

    rating_classes = [value for value in rating_node.get("class", []) if value != "star-rating"]
    description_node = soup.select_one("#product_description + p")
    return {
        "title": title_node.get_text(" ", strip=True),
        "product_url": product_url,
        "price_text": price_node.get_text(" ", strip=True),
        "availability_text": availability_node.get_text(" ", strip=True),
        "rating_text": rating_classes[0] if rating_classes else "",
        "description": description_node.get_text(" ", strip=True) if description_node else None,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }


def normalize_and_validate(raw: dict[str, Any]) -> BookRecord:
    return BookRecord(**raw, price_gbp=normalize_price(raw["price_text"]))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_pipeline(
    *,
    root: Path = ROOT,
    max_pages: int = 3,
    inject_broken_url: bool = False,
    delay_seconds: float = 0.5,
    timeout_seconds: float = 10.0,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    started_clock = time.monotonic()
    fetcher = Fetcher(
        root / "cache",
        delay_seconds=delay_seconds,
        timeout_seconds=timeout_seconds,
        client=client,
    )
    errors: list[dict[str, str]] = []
    failed_urls: list[str] = []
    robots_status = "not checked"

    try:
        fetcher.fetch(ROBOTS_URL)
        robots_status = "robots.txt fetched"
    except FetchFailure as exc:
        robots_status = "no robots file found" if "404" in exc.reason else f"robots check failed: {exc.reason}"

    urls, sources, catalogue_pages = discover_catalogue(fetcher, max_pages=max_pages)
    if inject_broken_url:
        fake = "https://books.toscrape.com/catalogue/this-book-does-not-exist/index.html"
        urls.append(fake)
        sources[fake] = TARGET_URL

    records_by_url: dict[str, dict[str, Any]] = {}
    for product_url in urls:
        try:
            html, fetched_at = fetcher.fetch(product_url)
            raw = extract_raw_record(html, product_url, sources[product_url], fetched_at)
            record = normalize_and_validate(raw)
            records_by_url[product_url] = record.model_dump(mode="json")
        except (FetchFailure, ValidationError, ValueError) as exc:
            failed_urls.append(product_url)
            errors.append({"product_url": product_url, "reason": str(exc)})
            print(f"SKIP url={product_url} reason={exc}")

    records = list(records_by_url.values())
    output_dir = root / "output"
    write_json(output_dir / "books.json", records)
    write_json(output_dir / "errors.json", errors)
    report = {
        "started_at": started_at.isoformat().replace("+00:00", "Z"),
        "duration_seconds": round(time.monotonic() - started_clock, 3),
        "target": "Books to Scrape practice sandbox",
        "catalogue_pages": catalogue_pages,
        "discovered": len(urls),
        "unique_urls": len(set(urls)),
        "pages_fetched": fetcher.pages_fetched,
        "cache_hits": fetcher.cache_hits,
        "valid_records": len(records),
        "invalid_records": len(errors),
        "failed_pages": len(failed_urls),
        "failed_page_urls": failed_urls,
        "robots_status": robots_status,
    }
    write_json(output_dir / "run-report.json", report)
    print(json.dumps(report, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cache-first polite Books to Scrape pipeline")
    parser.add_argument("--max-catalogue-pages", type=int, default=3, choices=range(1, 4))
    parser.add_argument("--inject-broken-url", action="store_true")
    parser.add_argument("--delay-seconds", type=float, default=0.5)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_pipeline(
        max_pages=args.max_catalogue_pages,
        inject_broken_url=args.inject_broken_url,
        delay_seconds=args.delay_seconds,
        timeout_seconds=args.timeout_seconds,
    )
    if report["valid_records"] != 20 * args.max_catalogue_pages:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
