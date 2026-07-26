"""Score candidate sources on legitimacy, intent, relevance and red flags.

Every rule here is a plain list or a plain comparison, so a reviewer can disagree
with a specific criterion and change it without reverse engineering a model.
"""

# Weighting reflects what actually protects a study. A legitimate institutional
# publisher is worth more than promising words in a page title, because the
# institution is the thing that can be contacted, audited, and held to an
# agreement later. Wording is cheap, accountability is not.
MAX_PUBLISHER_POINTS = 40
MAX_INTENT_POINTS = 30
MAX_RELEVANCE_POINTS = 20
MAX_PEDIATRIC_POINTS = 20

MAX_TOTAL_POINTS = (
    MAX_PUBLISHER_POINTS + MAX_INTENT_POINTS + MAX_RELEVANCE_POINTS + MAX_PEDIATRIC_POINTS
)

PASS_THRESHOLD = 65

# Academic and government domains carry an institutional review structure behind
# them, which is the closest thing to a guarantee available from a search result.
ACADEMIC_SUFFIXES = (".edu", ".ac.uk", ".edu.au", ".ac.jp")
GOVERNMENT_SUFFIXES = (".gov", ".nih.gov", ".gov.uk")

# Publishers of peer reviewed work. Material here has already passed some form of
# editorial and ethics screening before publication.
RESEARCH_PUBLISHER_DOMAINS = (
    "jove.com",
    "nature.com",
    "sciencedirect.com",
    "springer.com",
    "wiley.com",
    "tandfonline.com",
    "sagepub.com",
    "frontiersin.org",
    "plos.org",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "bmj.com",
    "apa.org",
)

# Words suggesting the material exists to teach or to document a study, rather
# than to entertain or to attract an audience.
RESEARCH_INTENT_TERMS = (
    "research",
    "study",
    "clinical",
    "training",
    "curriculum",
    "assessment",
    "intervention",
    "evidence",
    "protocol",
    "laboratory",
    "lab",
    "university",
    "faculty",
    "professional development",
    "continuing education",
    "diagnostic",
    "therapist",
    "practitioner",
    "peer reviewed",
)

RELEVANCE_AUTISM_TERMS = ("autism", "autistic", "asd", "neurodivergent", "developmental disabilit")
RELEVANCE_VIDEO_TERMS = ("video", "recording", "footage", "media library", "webinar", "clip")

# The brief asks for material relevant to children specifically, not to autism in
# general. Without this an adult employment or independent living resource scores
# exactly as well as a pediatric one. "parent" and "family" are included because
# a resource written for the parents of an autistic person is nearly always about
# a child, and "early intervention" and "school" are pediatric by definition.
PEDIATRIC_TERMS = (
    "child",
    "children",
    "pediatric",
    "paediatric",
    "infant",
    "toddler",
    "adolescent",
    "youth",
    "young people",
    "early intervention",
    "school",
    "student",
    "classroom",
    "parent",
    "family",
    "developmental screening",
)

# Phrases that suggest a specific identifiable child is the subject, or that the
# material exists to build an audience. Either one makes a source unusable for
# research regardless of how good the rest of it looks, so these disqualify
# outright instead of subtracting points. A vetting tool should fail closed.
PERSONAL_CONTENT_RED_FLAGS = (
    "my son",
    "my daughter",
    "my child",
    "my kid",
    "our son",
    "our daughter",
    "our journey",
    "vlog",
    "day in the life",
    "meltdown",
    "family channel",
    "subscribe",
    "sponsored by",
    "merch",
    "storytime",
    "prank",
)


def _searchable_text(candidate):
    """Combine the fields worth matching against, lowercased."""
    parts = [candidate["title"], candidate["description"], candidate["publisher"]]
    return " ".join(parts).lower()


def score_publisher_legitimacy(candidate):
    """Rate how much the publishing organization can be trusted and traced.

    Returns (points, reason).
    """
    domain = candidate["domain"]

    for suffix in ACADEMIC_SUFFIXES:
        if domain.endswith(suffix):
            return MAX_PUBLISHER_POINTS, "university domain"

    for suffix in GOVERNMENT_SUFFIXES:
        if domain.endswith(suffix):
            return MAX_PUBLISHER_POINTS, "government domain"

    for publisher_domain in RESEARCH_PUBLISHER_DOMAINS:
        if domain.endswith(publisher_domain):
            return 35, "peer reviewed publisher"

    # A real organization may well run its outreach through a video platform, but
    # the platform itself vouches for nobody, so this cannot score as a
    # legitimate publisher on domain alone.
    if candidate["is_user_upload_platform"]:
        return 5, "user upload platform, publisher not verifiable from domain"

    if domain.endswith(".org"):
        return 20, "nonprofit domain, organization not independently verified"

    return 10, "general commercial domain"


def score_research_intent(candidate):
    """Rate how strongly the description reads as research or educational."""
    text = _searchable_text(candidate)

    matched_terms = []
    for term in RESEARCH_INTENT_TERMS:
        if term in text:
            matched_terms.append(term)

    # Diminishing value per term. One mention of "research" is weak evidence,
    # four overlapping signals is a much better one, but nothing beyond that.
    points = min(MAX_INTENT_POINTS, len(matched_terms) * 8)

    if not matched_terms:
        return 0, "no research or educational language"
    return points, f"research language ({', '.join(matched_terms[:3])})"


def score_relevance(candidate):
    """Rate whether the source is actually about autism and actually about video."""
    text = _searchable_text(candidate)

    mentions_autism = False
    for term in RELEVANCE_AUTISM_TERMS:
        if term in text:
            mentions_autism = True
            break

    mentions_video = False
    for term in RELEVANCE_VIDEO_TERMS:
        if term in text:
            mentions_video = True
            break

    if mentions_autism and mentions_video:
        return MAX_RELEVANCE_POINTS, "autism and video both present"
    if mentions_autism:
        return 10, "autism only, video content not evident"
    if mentions_video:
        return 5, "video only, autism relevance not evident"
    return 0, "neither autism nor video evident"


def score_pediatric_relevance(candidate):
    """Rate whether the source is about children rather than autism in general."""
    text = _searchable_text(candidate)

    matched_terms = []
    for term in PEDIATRIC_TERMS:
        if term in text:
            matched_terms.append(term)

    if not matched_terms:
        return 0, "no stated focus on children"
    return MAX_PEDIATRIC_POINTS, f"focus on children ({', '.join(matched_terms[:2])})"


def find_red_flags(candidate):
    """Return any personal or promotional content markers found.

    This reads titles and search snippets only, so it catches the obvious cases
    and will miss anything subtler. It is a first filter, not a substitute for a
    human looking at the source.
    """
    text = _searchable_text(candidate)

    found = []
    for phrase in PERSONAL_CONTENT_RED_FLAGS:
        if phrase in text:
            found.append(phrase)
    return found


def score_candidate(candidate):
    """Score one candidate and explain the outcome in a single line."""
    publisher_points, publisher_reason = score_publisher_legitimacy(candidate)
    intent_points, intent_reason = score_research_intent(candidate)
    relevance_points, relevance_reason = score_relevance(candidate)
    pediatric_points, pediatric_reason = score_pediatric_relevance(candidate)
    red_flags = find_red_flags(candidate)

    total = publisher_points + intent_points + relevance_points + pediatric_points

    # Two gates that a high score alone cannot satisfy. A source with no evidence
    # of video is not a candidate video source however good the publisher is, and
    # a source with no research or educational language is not evidently a
    # research resource even on a university domain. Without the second gate a
    # university news post about a video scores 60 and ranks first, which
    # happened. Both are held back for a human rather than dropped, since a
    # terse search snippet is weak evidence of absence.
    shows_video_evidence = relevance_points >= MAX_RELEVANCE_POINTS
    shows_research_intent = intent_points > 0

    if red_flags:
        passed = False
        category = "personal or promotional markers"
        justification = f"Rejected: personal or promotional markers ({', '.join(red_flags)})"
    elif not shows_video_evidence:
        passed = False
        category = "no video evidence, worth a manual check"
        justification = f"Held back: {relevance_reason}, worth a manual check ({publisher_reason})"
    elif not shows_research_intent:
        passed = False
        category = "no research language, worth a manual check"
        justification = f"Held back: {intent_reason}, worth a manual check ({publisher_reason})"
    elif total >= PASS_THRESHOLD:
        passed = True
        category = "passed"
        justification = (
            f"Passed: {publisher_reason}, {intent_reason}, {relevance_reason}, {pediatric_reason}"
        )
    else:
        passed = False
        category = f"scored below the pass mark of {PASS_THRESHOLD}"
        justification = f"Rejected: scored {total} below {PASS_THRESHOLD}, {publisher_reason}"

    scored = dict(candidate)
    scored.update(
        {
            "publisher_points": publisher_points,
            "intent_points": intent_points,
            "relevance_points": relevance_points,
            "pediatric_points": pediatric_points,
            "total_score": total,
            "red_flags": red_flags,
            "passed": passed,
            "category": category,
            "justification": justification,
        }
    )
    return scored


def score_all(candidates):
    """Score every candidate and return them ranked best first."""
    scored_candidates = []
    for candidate in candidates:
        scored_candidates.append(score_candidate(candidate))

    scored_candidates.sort(key=lambda item: (item["passed"], item["total_score"]), reverse=True)
    return scored_candidates
