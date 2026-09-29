from pathlib import Path

import httpx
import pytest

from scraper.src.main import (
    Fetcher,
    absolute_url,
    discover_catalogue,
    extract_raw_record,
    normalize_and_validate,
    normalize_price,
)


PRODUCT_HTML = """
<html><body>
  <div class="product_main">
    <h1>Example Book</h1>
    <p class="price_color">£12.34</p>
    <p class="availability"> In stock (7 available) </p>
    <p class="star-rating Four"></p>
  </div>
  <div id="product_description"><h2>Product Description</h2></div>
  <p> A useful description. </p>
</body></html>
"""


def test_price_normalization():
    assert normalize_price("£51.77") == 51.77
    with pytest.raises(ValueError):
        normalize_price("price unavailable")


def test_relative_url_becomes_absolute():
    page = "https://books.toscrape.com/catalogue/page-1.html"
    assert absolute_url("../catalogue/a-book/index.html", page) == "https://books.toscrape.com/catalogue/a-book/index.html"


def test_missing_description_is_null_and_record_validates():
    html = PRODUCT_HTML.replace(
        '<div id="product_description"><h2>Product Description</h2></div>\n  <p> A useful description. </p>',
        "",
    )
    raw = extract_raw_record(
        html,
        "https://books.toscrape.com/catalogue/example/index.html",
        "https://books.toscrape.com/catalogue/page-1.html",
        "2026-09-29T00:00:00Z",
    )
    assert raw["description"] is None
    assert normalize_and_validate(raw).price_gbp == 12.34


def test_discovery_removes_duplicate_urls_and_follows_next():
    page_1 = """
    <article class="product_pod"><h3><a href="book-a/index.html">A</a></h3></article>
    <article class="product_pod"><h3><a href="book-a/index.html">A duplicate</a></h3></article>
    <li class="next"><a href="page-2.html">next</a></li>
    """
    page_2 = """
    <article class="product_pod"><h3><a href="book-b/index.html">B</a></h3></article>
    """

    class StubFetcher:
        def fetch(self, url):
            return (page_2 if url.endswith("page-2.html") else page_1), "2026-09-29T00:00:00Z"

    urls, sources, pages = discover_catalogue(
        StubFetcher(),
        start_url="https://books.toscrape.com/catalogue/page-1.html",
        max_pages=2,
    )
    assert pages == 2
    assert len(urls) == 2
    assert len(sources) == 2


def test_malformed_product_page_is_rejected():
    with pytest.raises(ValueError, match="missing product area"):
        extract_raw_record(
            "<html><body>broken</body></html>",
            "https://books.toscrape.com/catalogue/broken/index.html",
            "https://books.toscrape.com/catalogue/page-1.html",
            "2026-09-29T00:00:00Z",
        )


def test_fetcher_uses_cache_after_first_request(tmp_path: Path):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, text="<html>cached</html>")

    fetcher = Fetcher(
        tmp_path,
        delay_seconds=0.5,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    first, _ = fetcher.fetch("https://example.test/page")
    second, _ = fetcher.fetch("https://example.test/page")
    assert first == second
    assert len(calls) == 1
    assert fetcher.pages_fetched == 1
    assert fetcher.cache_hits == 1
