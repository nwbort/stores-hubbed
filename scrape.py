#!/usr/bin/env python3
"""Scrape HUBBED store locations into stores.json.

Uses only the Python standard library so the GitHub Actions job needs no
dependency install step.

The output is written deterministically (stores sorted by id, keys sorted, no
run timestamp) so re-running against unchanged upstream data produces a
byte-identical file and the workflow makes no commit.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

API_URL = "https://production-api.hubbed.com.au/v1/hubbed/storelocations"

# Public token used by hubbed.com's own store locator. Override with the
# HUBBED_TOKEN environment variable (e.g. a repository secret) if it rotates.
DEFAULT_TOKEN = (
    "eyJhbGciOiJIUzI1NiJ9."
    "eyJDb3VyaWVyQ29kZSI6ImFkbWluIiwiSHViYmVkVXNlcklkIjoiNiIsImp0aSI6IjZmN2Q1"
    "OWEwLWFjMzYtNDBhMy1hNmIzLWU1YWM5MjQ0ZjBmNyIsIm5iZiI6MTU3MTkyMzM3NSwiZXhw"
    "IjoyMTA4NDY3Mzc1LCJpc3MiOiJodHRwOi8vaHViYmVkLmNvbSIsImF1ZCI6Imh0dHA6Ly9o"
    "dWJiZWQuY29tIn0."
    "44HwneC7GdwTB74f81w6ZR8KNE5mca6oZ6_o199OkFM"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
)

PER_PAGE = 10000
COUNTRY_CODE = "ALL"


def fetch_page(page, token, per_page, country_code, retries=4, timeout=120):
    """Fetch one page of store locations, retrying on transient failures."""
    url = f"{API_URL}?page={page}&perpage={per_page}&CountryCode={country_code}"
    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "authorization": f"Bearer {token}",
        "origin": "https://hubbed.com",
        "referer": "https://hubbed.com/",
        "user-agent": USER_AGENT,
    }

    last_error = None
    for attempt in range(retries):
        if attempt:
            delay = 2**attempt
            print(
                f"  retrying page {page} in {delay}s ({last_error})",
                file=sys.stderr,
            )
            time.sleep(delay)
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            last_error = exc

    raise RuntimeError(f"failed to fetch page {page}: {last_error}")


def fetch_all(token, per_page, country_code):
    """Fetch every page of store locations."""
    stores = []
    page = 1
    total_pages = 1
    total_records = None

    while page <= total_pages:
        payload = fetch_page(page, token, per_page, country_code)

        code = str(payload.get("responseCode", ""))
        if code != "200":
            raise RuntimeError(
                f"API returned responseCode={code!r} "
                f"message={payload.get('responseMessage')!r}"
            )

        data = payload.get("data") or []
        stores.extend(data)

        total_pages = payload.get("totalPages") or 1
        total_records = payload.get("totalRecords")
        print(f"page {page}/{total_pages}: {len(data)} stores", file=sys.stderr)
        page += 1

    if total_records is not None and len(stores) != total_records:
        raise RuntimeError(f"expected {total_records} stores, got {len(stores)}")

    return stores


def normalise(stores):
    """Sort stores and drop fields that are meaningless for a full dump."""
    for store in stores:
        # Only relevant to a proximity search; always 0.0 here, and it would
        # otherwise add noise to diffs.
        store.pop("distanceFromSearchedLocationInKm", None)

    return sorted(
        stores,
        key=lambda s: (s.get("droplocation_id") is None, s.get("droplocation_id") or 0),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o", "--output", default="stores.json", help="output file (default: stores.json)"
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=PER_PAGE,
        help=f"records per request (default: {PER_PAGE})",
    )
    parser.add_argument(
        "--country-code",
        default=COUNTRY_CODE,
        help=f"CountryCode filter (default: {COUNTRY_CODE})",
    )
    args = parser.parse_args()

    token = os.environ.get("HUBBED_TOKEN") or DEFAULT_TOKEN

    stores = normalise(fetch_all(token, args.per_page, args.country_code))
    if not stores:
        raise RuntimeError("API returned no stores; refusing to write output")

    ids = [s.get("droplocation_id") for s in stores]
    if len(set(ids)) != len(ids):
        print("warning: duplicate droplocation_id values in response", file=sys.stderr)

    document = {
        "source": API_URL,
        "count": len(stores),
        "stores": stores,
    }

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")

    print(f"wrote {len(stores)} stores to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
