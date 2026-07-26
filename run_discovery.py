"""Run the full pipeline: search, extract, score, report."""

import argparse
from pathlib import Path

from src.extract_candidates import build_candidates
from src.report import print_ranked_candidates, print_scope_statement, write_candidates_csv
from src.score_candidates import MAX_TOTAL_POINTS, PASS_THRESHOLD, score_all
from src.search_sources import SEARCH_QUERIES, load_or_search

PROJECT_ROOT = Path(__file__).parent
CACHE_PATH = PROJECT_ROOT / "data" / "search_cache.json"
RESULTS_DIR = PROJECT_ROOT / "results"


def print_heading(text):
    """Print a section heading."""
    print(f"\n--- {text} " + "-" * max(0, 92 - len(text)))


def main():
    """Search for candidate sources, vet them, and print the ranked result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="run a live search instead of using the cached snapshot",
    )
    arguments = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)

    print_heading(f"STEP 1  Search for candidate sources ({len(SEARCH_QUERIES)} queries)")
    raw_rows = load_or_search(CACHE_PATH, refresh=arguments.refresh)
    print(f"{len(raw_rows)} raw search results")

    print_heading("STEP 2  Extract candidate records")
    candidates = build_candidates(raw_rows)
    print(f"{len(candidates)} distinct sources after merging duplicate URLs")
    print("Fields kept: source name, publisher, URL, title, description. No video touched.")

    print_heading(
        f"STEP 3  Score against vetting criteria (pass mark {PASS_THRESHOLD}/{MAX_TOTAL_POINTS})"
    )
    scored_candidates = score_all(candidates)
    passed_count = sum(1 for candidate in scored_candidates if candidate["passed"])
    print(f"{passed_count} passed, {len(scored_candidates) - passed_count} filtered out")

    # The limits come before the shortlist on purpose. A reader should know what
    # a passing score does not mean before they read the names of the sources.
    print_scope_statement()

    print_heading("STEP 4  Ranked candidates")
    print_ranked_candidates(scored_candidates)

    csv_path = write_candidates_csv(scored_candidates, RESULTS_DIR / "vetted_candidates.csv")
    print(f"\nSaved {csv_path.relative_to(PROJECT_ROOT)}\n")


if __name__ == "__main__":
    main()
