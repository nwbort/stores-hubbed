# stores-hubbed

A daily snapshot of every [HUBBED](https://hubbed.com/) parcel collection point,
scraped from HUBBED's public store-locator API and committed to
[`stores.json`](stores.json).

## Data

`stores.json` contains the full API record for every location — no fields are
trimmed apart from `distanceFromSearchedLocationInKm`, which is only meaningful
for a proximity search:

```json
{
  "count": 1940,
  "source": "https://production-api.hubbed.com.au/v1/hubbed/storelocations",
  "stores": [
    {
      "address": { "city": "...", "state": "...", "postcode": "...", "street1": "...", "street2": "...", "country": "..." },
      "businessHours": [{ "day": "Monday", "open_time": "09:00", "close_time": "17:00" }],
      "channel": { "channel_id": 6, "channel_name": "Community", "...": "..." },
      "droplocation_id": 1618,
      "latitude": -33.75,
      "longitude": 151.22,
      "locationType": { "id": 8, "name": "Other" },
      "name": "...",
      "products": [{ "id": 1, "productname": "Click and Collect", "status": true }],
      "services": [{ "id": 2, "name": "Over the counter" }],
      "storeDlb": "AU007560",
      "...": "..."
    }
  ]
}
```

Coverage is `CountryCode=ALL`, which currently spans Australia, New Zealand and
the Philippines. Stores are sorted by `droplocation_id` and object keys are
sorted alphabetically, so diffs between snapshots show only real upstream
changes.

## How it works

[`.github/workflows/scrape.yml`](.github/workflows/scrape.yml) runs
[`scrape.py`](scrape.py) every day at 18:00 UTC (early morning Australian
eastern time), and can also be run on demand from the Actions tab. The output is
deterministic, so the workflow commits only when the upstream data has actually
changed — the commit history is a change log of HUBBED's network.

## Running locally

No dependencies beyond the Python standard library:

```sh
python scrape.py                    # writes stores.json
python scrape.py -o /tmp/out.json   # write elsewhere
python scrape.py --country-code AU  # limit to one country
```

The scraper uses the same public bearer token that hubbed.com's own store
locator sends. If it ever rotates, set the `HUBBED_TOKEN` environment variable
(or a repository secret of that name, which the workflow already passes through)
to override it.
