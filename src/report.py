"""Print the ranked candidate list and the limits of what this tool established."""

import csv

LINE_WIDTH = 100
NEAR_MISS_COUNT = 6

# The shortlist is printed in full up to this many. Past it the terminal output
# stops being readable in one screen, and the CSV holds every row anyway.
SHORTLIST_DISPLAY_COUNT = 10

SCOPE_STATEMENT = """
WHAT THIS TOOL DOES NOT DO

  It does not download, stream, store, or look at any video. Every field above comes
  from a public search result, meaning a title, a link, and a snippet of text.

  It does not store personal data about any person, and it makes no judgement about
  any individual appearing in any linked material.

  It does not verify consent. Nothing in a search result can establish whether the
  people recorded agreed to research use, and a high score here does not imply that
  they did.

  A passing score means one thing only: this source is worth a human looking at. It
  is a shortlist, not an approval.

  Real data collection from any source listed here would require IRB review, a direct
  agreement with the publishing organization, and a consent position confirmed in
  writing with that organization rather than inferred from a web page.
"""


def print_ranked_candidates(scored_candidates):
    """Print every candidate in rank order with a one line justification."""
    passed = []
    rejected = []
    for candidate in scored_candidates:
        if candidate["passed"]:
            passed.append(candidate)
        else:
            rejected.append(candidate)

    print(f"\nVETTED CANDIDATES ({len(passed)} passed)")
    print("=" * LINE_WIDTH)
    if not passed:
        print("  None of the candidates cleared the threshold.")

    for position, candidate in enumerate(passed[:SHORTLIST_DISPLAY_COUNT]):
        print(f"\n{position + 1}. [{candidate['total_score']}] {candidate['publisher']}")
        print(f"   {candidate['title'][:88]}")
        print(f"   {candidate['url'][:88]}")
        print(f"   {candidate['justification']}")

    if len(passed) > SHORTLIST_DISPLAY_COUNT:
        remaining = len(passed) - SHORTLIST_DISPLAY_COUNT
        print(f"\n  ... and {remaining} more that passed, listed in full in the CSV.")

    print(f"\n\nFILTERED OUT ({len(rejected)})")
    print("=" * LINE_WIDTH)

    # Listing every rejection buries the shortlist, and the reasons repeat. The
    # counts carry the same information, and the CSV holds every row in full.
    counts_by_category = {}
    for candidate in rejected:
        category = candidate["category"]
        counts_by_category[category] = counts_by_category.get(category, 0) + 1

    for category in sorted(counts_by_category, key=counts_by_category.get, reverse=True):
        print(f"  {counts_by_category[category]:>3}  {category}")

    print(f"\n  Closest {min(NEAR_MISS_COUNT, len(rejected))} below the line:")
    for candidate in rejected[:NEAR_MISS_COUNT]:
        print(f"    [{candidate['total_score']:>2}] {candidate['domain'][:32]:<32} {candidate['category'][:44]}")
    print("\n  Every rejected source with its full reasoning is in the CSV.")


def print_scope_statement():
    """Print the explicit limits of what this tool establishes."""
    print("\n" + "=" * LINE_WIDTH)
    print(SCOPE_STATEMENT.rstrip())
    print("=" * LINE_WIDTH)


def write_candidates_csv(scored_candidates, output_path):
    """Save the full scored list so the ranking can be checked by hand."""
    columns = [
        "passed",
        "total_score",
        "publisher",
        "domain",
        "url",
        "title",
        "publisher_points",
        "intent_points",
        "relevance_points",
        "pediatric_points",
        "justification",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for candidate in scored_candidates:
            writer.writerow(candidate)

    return output_path
