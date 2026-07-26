"""Find candidate public video sources through plain web search.

No API key and no authentication, just ordinary public search result pages.

Three independent endpoints are tried in order for each query. Free search
endpoints throttle aggressively and one of them being unavailable should not stop
a run, which is a lesson learned the hard way while building this. Raw results
are cached so that scoring is reproducible against a fixed snapshot.
"""

import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Identifying as a normal browser. These endpoints return an empty page otherwise.
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

# Kept short enough to work against a small independent index as well as a large
# one. Aimed at the four source types worth trusting: university labs, clinics,
# established nonprofits, and material published alongside peer reviewed work.
# Deliberately nothing that would surface family vlogs or personal channels,
# since those are the exact thing the scoring step exists to reject.
SEARCH_QUERIES = [
    "autism video library university",
    "autism research video archive",
    "autism training videos clinic",
    "autism center video resources",
    "autism nonprofit video library",
    # Half the queries name children explicitly. The brief asks for material about
    # children with autism, and general autism queries return plenty of adult
    # employment and independent living resources that score well on every other
    # criterion. Scoring for children only helps if children are in the corpus.
    "autism children video library",
    "child autism assessment video university",
    "pediatric autism clinical training videos",
    "autism early intervention toddler videos",
    "autism classroom video resources school",
]

# Spaced wide on purpose. At four seconds the independent index started refusing
# after three queries, which quietly cost five of the eight searches.
SECONDS_BETWEEN_QUERIES = 12.0


def _clean_text(element):
    """Pull text out of a result element, keeping spaces around bold fragments."""
    if element is None:
        return ""
    return " ".join(element.get_text(separator=" ", strip=True).split())


def _parse_duckduckgo(html):
    """Parse a DuckDuckGo HTML results page."""
    soup = BeautifulSoup(html, "html.parser")

    rows = []
    for result in soup.select("div.result"):
        link = result.select_one("a.result__a")
        if link is None or not link.get("href"):
            continue
        rows.append(
            {
                "title": _clean_text(link),
                "url": link["href"],
                "snippet": _clean_text(result.select_one("a.result__snippet")),
            }
        )
    return rows


def _parse_mojeek(html):
    """Parse a Mojeek results page."""
    soup = BeautifulSoup(html, "html.parser")

    rows = []
    for result in soup.select("ul.results-standard li"):
        link = result.select_one("h2 a.title")
        if link is None or not link.get("href"):
            continue
        rows.append(
            {
                "title": _clean_text(link),
                "url": link["href"],
                "snippet": _clean_text(result.select_one("p.s")),
            }
        )
    return rows


def _fetch_duckduckgo_html(query, session):
    """Query the DuckDuckGo HTML endpoint."""
    response = session.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query},
        headers=REQUEST_HEADERS,
        timeout=30,
    )
    return _parse_duckduckgo(response.text)


def _fetch_duckduckgo_lite(query, session):
    """Query the DuckDuckGo lite endpoint, which sometimes answers when the main one will not."""
    response = session.post(
        "https://lite.duckduckgo.com/lite/",
        data={"q": query},
        headers=REQUEST_HEADERS,
        timeout=30,
    )
    return _parse_duckduckgo(response.text)


def _fetch_mojeek(query, session):
    """Query Mojeek, an independent index with its own crawler."""
    response = session.get(
        "https://www.mojeek.com/search",
        params={"q": query},
        headers=REQUEST_HEADERS,
        timeout=30,
    )
    return _parse_mojeek(response.text)


SEARCH_BACKENDS = [
    ("duckduckgo", _fetch_duckduckgo_html),
    ("duckduckgo-lite", _fetch_duckduckgo_lite),
    ("mojeek", _fetch_mojeek),
]


def run_single_query(query, session):
    """Return result rows for one query, trying each backend until one answers.

    A throttled endpoint answers with an empty page or drops the connection
    rather than returning an error status, so both are treated the same way:
    move on and try the next backend.
    """
    for backend_name, fetch in SEARCH_BACKENDS:
        try:
            rows = fetch(query, session)
        except requests.RequestException:
            continue

        if rows:
            for row in rows:
                row["query"] = query
                row["backend"] = backend_name
            return rows

    return []


def search_all_queries(queries=None):
    """Run every query and return the combined raw rows."""
    queries = queries if queries is not None else SEARCH_QUERIES

    all_rows = []
    with requests.Session() as session:
        for position, query in enumerate(queries):
            rows = run_single_query(query, session)
            backend = rows[0]["backend"] if rows else "none answered"
            print(f"  [{position + 1}/{len(queries)}] {query}: {len(rows)} results ({backend})")
            all_rows.extend(rows)

            # Spacing the requests out to stay a polite client.
            if position < len(queries) - 1:
                time.sleep(SECONDS_BETWEEN_QUERIES)

    return all_rows


def load_or_search(cache_path, refresh=False):
    """Return raw search rows, from cache when available.

    Live search results drift from day to day. Caching the raw rows means the
    scoring and ranking can be re-run and checked against exactly the snapshot
    that produced a given report.
    """
    cache_path = Path(cache_path)

    if cache_path.exists() and not refresh:
        print(f"Using cached search results from {cache_path.name}")
        return json.loads(cache_path.read_text())

    print("Running live search")
    rows = search_all_queries()

    # Every endpoint throttles by answering 200 with nothing in it. Writing that
    # over a good cache would destroy the snapshot a previous run depended on,
    # so an empty result is treated as a failure rather than as an answer.
    if not rows:
        raise RuntimeError(
            "No search backend returned results, which means all of them are "
            "throttling this address. Any existing cache has been left alone. "
            "Wait several minutes and run again."
        )

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(rows, indent=2))
    print(f"Cached {len(rows)} raw results to {cache_path.name}")
    return rows
