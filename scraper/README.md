# The polite scraper

This module collects the first three catalogue pages from [Books to Scrape](https://books.toscrape.com/), a public sandbox created for scraping practice. It discovers book links from each page's `next` link, visits the 60 detail pages, validates normalized records with Pydantic, and writes `output/books.json`, `output/errors.json`, and `output/run-report.json`.

## Target classification and ethics

- Target: Books to Scrape, a practice sandbox intended for this use.
- Scope: exactly the first three catalogue pages and their 60 book detail pages.
- Data: title, canonical product URL, raw and numeric price, availability, rating, optional description, source catalogue page, and fetch time.
- Robots check: the runner requests `robots.txt` once, caches the result when present, and records the outcome in the run report. A missing file is recorded as `no robots file found`; it is not treated as permission.
- I will not reuse this code on another site without checking its rules and terms first.

Prefer an official API when one exists. Never bypass authentication, paywalls, rate limits, or blocks, and collect only what is needed. This assignment needs no browser because the product data is present in the HTML returned by the server; adding a browser would only increase time and memory cost.

## Run

From the repository root:

```bash
python -m scraper.src.main
```

The first run makes real requests. Every request uses an identifying user-agent, a timeout, status checks, at least a 500 ms delay, and one retry only for timeouts/network failures or 5xx responses. Responses are cached; later development runs print `CACHE HIT` and make no duplicate requests.

Prove failure isolation without attacking the target:

```bash
python -m scraper.src.main --inject-broken-url
```

The deliberate 404 is not retried. The run still writes the 60 valid records and reports one failed page.

Latest verified failure-isolation run (29 September 2026):

```json
{
  "catalogue_pages": 3,
  "discovered": 61,
  "unique_urls": 61,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 1,
  "failed_pages": 1,
  "robots_status": "no robots file found"
}
```

## Record schema

Every stored record has: `title`, `product_url`, `price_text`, numeric `price_gbp`, `availability_text`, `rating_text`, nullable `description`, `source_page`, and `fetched_at`. The canonical product URL is the identity, so reruns overwrite the deterministic output rather than append duplicates. Invalid records are excluded from `books.json` and written to `errors.json` with a reason.

## Tests and limitation

Run `pytest -q scraper/tests`. Tests cover price normalization, URL resolution, missing descriptions, duplicate removal, malformed pages, and cache behavior without using the network.

This is a deliberately single-process educational crawler. It does not implement distributed scheduling or crawl arbitrary sites, and it should not be repurposed without a new target review.
