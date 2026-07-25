"""Turn raw search rows into candidate source records.

Text and links only. Nothing here opens, downloads, or stores video.
"""

import re
from urllib.parse import urlparse

# Platforms that host other people's uploads. The domain tells you nothing about
# who published the video, so these are kept but flagged for the scorer.
USER_UPLOAD_PLATFORMS = {
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "vimeo.com",
    "www.vimeo.com",
    "tiktok.com",
    "www.tiktok.com",
    "instagram.com",
    "www.instagram.com",
    "facebook.com",
    "www.facebook.com",
    "x.com",
    "twitter.com",
}


def get_domain(url):
    """Return the lowercase host for a URL, without the leading www."""
    host = (urlparse(url).netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def normalize_url_for_dedup(url):
    """Reduce a URL to a key that treats the same page written differently as one.

    Search backends return the same page as both http and https, with and without
    a trailing slash. Deduplicating on the raw string counts those as separate
    sources and inflates the candidate list.
    """
    parsed = urlparse(url)
    path = (parsed.path or "").rstrip("/")
    key = f"{get_domain(url)}{path.lower()}"
    if parsed.query:
        key = f"{key}?{parsed.query}"
    return key


def infer_publisher(title, domain):
    """Guess the publishing organization from the result title and domain.

    Search result titles usually carry the organization after a dash or pipe,
    as in "Autism Media Lab - UCLA Disability Studies". When there is no such
    separator the domain is the more reliable answer.
    """
    tail = re.split(r" [-|–—] ", title)[-1].strip()

    # Search engines truncate long titles, leaving a fragment like "Gainesville
    # ..." rather than an organization. A comma usually means the tail is a
    # marketing tagline, as in "ELIJA - Championing Hope, One Child at a Time".
    # The domain is a duller name but a true one, so prefer it over either.
    if tail.endswith("...") or tail.endswith("…"):
        return domain
    if "," in tail:
        return domain
    if 2 < len(tail) < 60:
        return tail

    return domain


def build_candidates(raw_rows):
    """Collapse raw search rows into one record per URL.

    The same source often appears under several queries. Merging on URL keeps
    one record per source and remembers every query that found it, which is a
    weak signal that the source is genuinely relevant rather than a stray hit.
    """
    candidates_by_url = {}

    for row in raw_rows:
        url = row["url"]
        domain = get_domain(url)
        if not domain:
            continue

        dedup_key = normalize_url_for_dedup(url)

        if dedup_key in candidates_by_url:
            existing = candidates_by_url[dedup_key]
            if row["query"] not in existing["found_by_queries"]:
                existing["found_by_queries"].append(row["query"])
            # Prefer the secure form when the same page turns up both ways.
            if url.startswith("https://") and not existing["url"].startswith("https://"):
                existing["url"] = url
            continue

        candidates_by_url[dedup_key] = {
            "title": row["title"],
            "url": url,
            "domain": domain,
            "publisher": infer_publisher(row["title"], domain),
            "description": row["snippet"],
            "is_user_upload_platform": domain in USER_UPLOAD_PLATFORMS,
            "found_by_queries": [row["query"]],
        }

    return list(candidates_by_url.values())
