# Autism video source discovery and vetting

This finds public video sources that could be relevant to research on children with autism, and
scores each one against explicit criteria for whether it is appropriate to approach. It produces
a ranked shortlist of candidate sources with a reason attached to every decision.

It does not collect video. That is deliberate, and it is the main design decision in the project.

## Why this vets sources instead of collecting video

The obvious reading of "locate video data relevant to children with autism" is a scraper. I did
not build one, for a reason I would rather state plainly than bury.

Downloading and storing video of real children creates a consent problem that no amount of
careful engineering solves. The children in that footage did not agree to be in my dataset.
Their parents may have agreed to a therapy clinic publishing a teaching example, which is a
completely different thing from agreeing to research use by a stranger. A public URL is not
consent, and a permissive license is not consent either. Building the scraper first and sorting
out the ethics afterwards gets the order backwards, and in a take home exercise there is no IRB
standing between me and a folder full of video of identifiable children.

So the tool stops one step earlier, at the point that is actually useful and actually safe. It
finds the organizations that hold relevant material and works out which of them are worth
contacting. That shortlist is the real bottleneck in this kind of work. The download step is
easy once you have permission, and it should not happen before.

The output is a list of institutions to talk to. It is not a dataset.

## What it does

```bash
pip install -r requirements.txt
python run_discovery.py
```

Add `--refresh` to run a live search instead of reading the cached snapshot.

Four steps, one module each under `src/`:

1. `search_sources.py` runs ten search queries against public search endpoints. No API key and
   no login, just ordinary result pages. It tries DuckDuckGo, then DuckDuckGo lite, then Mojeek,
   moving on when one refuses to answer. The raw rows are cached to `data/search_cache.json`.
2. `extract_candidates.py` turns those rows into one record per URL, keeping the source name,
   publisher, URL, title and description. Nothing else is fetched.
3. `score_candidates.py` scores each candidate and decides whether it passes.
4. `report.py` states the limits of what any of this establishes, then prints the ranked list
   with a one line justification per source. The limits come first on purpose, so a reader knows
   what a passing score does not mean before they read the names.

The searches are written to look for university labs, clinics, established nonprofits and
material published alongside peer reviewed work. There are deliberately no queries that would
pull in family vlogs or personal channels. It would be strange to go looking for the exact
material the scoring step exists to reject.

Half the queries name children explicitly. That was not true in my first version and it should
have been. General autism queries return a lot of adult employment and independent living
material that scores well on every other criterion, and scoring for children only helps if
children are in the results to begin with.

## A note on reproducibility

Live search results move around. Run the same query a week apart and you get a different list,
which makes a scoring tool impossible to check.

The raw search rows are cached to `data/search_cache.json` and the committed snapshot is the one
that produced the output shown here. So the scoring is reproducible even though the search is
not. If you want current results, use `--refresh` and expect the ranking to differ. That is the
web changing, not the scorer.

These endpoints also thin out or block entirely if queries arrive too fast, and they do it by
answering normally with an empty page rather than by returning an error. I ran into all of this
while building the tool, so three things came out of it. Queries fall back across three
independent endpoints instead of depending on one. Queries are spaced twelve seconds apart,
because at four seconds the smaller index started refusing after three of them and quietly cost
me most of the run. And an empty result now raises instead of being written to the
cache, because on one run a throttled search overwrote a good snapshot with nothing, which is a
worse failure than crashing.

Backend matters more than I expected. A run that fell back entirely to the smaller index
returned a much weaker set of sources than the same queries against the larger one. The
committed snapshot came from DuckDuckGo. If you refresh and get noticeably worse results, check
which backend answered before blaming the scoring.

## The scoring criteria and why these ones

One hundred and ten points across four criteria, with a pass mark of 65 and three conditions that
override the score entirely.

**Publisher legitimacy, 40 points.** University and government domains score full marks. Peer
reviewed publishers score 35. A `.org` scores 20, because the suffix means less than people
assume and I have not verified the organization behind it. A general commercial domain scores
10. A user upload platform scores 5, and that last one is the point worth explaining: a real
research institute may well run its outreach through a video platform, but the platform vouches
for nobody, so the domain tells you nothing about who actually published the material.

This criterion carries the most weight on purpose. An institution is a thing you can contact,
audit, and hold to a written agreement later. Promising words in a page title are not. When the
two disagree, I would rather trust the institution.

**Research or educational intent, 30 points.** Counts terms like research, clinical, training,
curriculum, assessment, protocol and practitioner, at 8 points each up to the cap. One mention
of "research" is weak evidence. Four overlapping signals is a decent one. Beyond that it stops
telling you anything, hence the cap.

**Relevance, 20 points.** Full marks only when the source shows evidence of both autism and
video. A source with no sign of video cannot pass at all, whatever else it scores, because a
video source with no video is not a candidate. Those are reported as held back for a manual
check rather than dropped, since a strong university centre with an uninformative snippet is
often worth a human look.

**Focus on children, 20 points.** The brief asks for material relevant to children with autism,
not to autism in general, and this is the criterion I originally left out. Without it an adult
employment resource scored exactly as well as a pediatric clinic, and only 3 of 11 sources on my
first shortlist showed any child focus at all. It now matches on terms like child, pediatric,
toddler, early intervention, classroom and parent. Parent and family are included because a
resource written for the parents of an autistic person is nearly always about a child.

I scored this rather than making it a hard requirement. A university autism centre that serves
children often will not say so in two lines of snippet text, and gating on that would throw away
real sources for want of a word. Sources with no child signal can still pass on the strength of
the other criteria, they just rank below the ones that do, and the justification line says which
is which.

**Personal content red flags, disqualifying.** Phrases like "my son", "day in the life", "vlog",
"subscribe" and "sponsored by" reject a candidate outright regardless of score. These suggest
either a specific identifiable child as the subject or an audience building motive, and both put
a source out of scope. This one disqualifies rather than deducting because a vetting tool should
fail closed. A false rejection costs one candidate. A false acceptance puts a real child's video
into a research pipeline.

I should be honest about the limit here. This reads titles and search snippets, so it catches
the obvious cases and will miss anything subtler. It narrows the pile a human has to look at. It
does not replace the human.

## Results

The committed snapshot has 100 raw results across 10 queries, which reduce to 75 distinct
sources. Of those, 19 passed and 56 were filtered out.

The top of the list:

| Score | Source | Child focus |
|---|---|---|
| 104 | Oregon Health and Science University, ACCESS provider training | toddler |
| 96 | Interagency Autism Coordinating Committee, archived video (hhs.gov) | child, children |
| 96 | Southern Connecticut State University, teaching students with autism | student, parent |
| 80 | WMU Autism Center of Excellence, training videos | pediatric |
| 76 | World Autism Conference, video streaming library | parent |
| 76 | ELIJA, autism training videos | child, children |
| 74 | Autism Research Centre, resources | child, children |
| 68 | University of Michigan autism toolkit | none stated |
| 68 | Voices of Autism video library, CU Anschutz | none stated |
| 68 | Thompson Center for Autism, University of Missouri | none stated |

15 of the 19 that passed carry a child focus signal. The four that do not are strong
institutional sources that passed on the other criteria and are worth a look regardless, which
is the behaviour I wanted from scoring this rather than gating on it.

The 56 rejections break down as 33 with no evidence of video, 18 with no research or educational
language, and 5 scoring below the pass mark. Nothing was rejected for personal content markers,
which I come back to below.

See [results/terminal_output.png](results/terminal_output.png) for a full run, and
`results/vetted_candidates.csv` for the complete scored list including everything filtered out.

## Where this is weak

Three things I would want a reviewer to know rather than discover.

The personal content rule never fired on this snapshot. Zero of 56 rejections came from it. That
is the expected result given the queries deliberately avoid personal channels, but it does mean
the criterion is untested against real data here. I checked it separately against constructed
examples and it behaves correctly, including rejecting a source that otherwise scores a perfect
90. Still, "it works on examples I wrote" is a weaker claim than "it works on the corpus."

Domain suffix is a proxy for legitimacy, and proxies fail at the edges. The WMU Autism Center of
Excellence sits on a `.com` and scored as a general commercial domain, which understates it by
about 30 points. It passed anyway on the strength of the other criteria, but a real university
centre being marked commercial is the kind of error to expect from this approach.

Everything is inferred from a title and roughly two lines of snippet text. Whether a source
actually holds usable video, and under what terms, is not something a search result can tell
you.

Related to that, the tool finds source pages rather than individual videos. The output is a
shortlist of organizations that appear to hold relevant material, not a list of specific videos.
Going from one to the other means a person opening each site, and for a real project that is the
right order anyway, since you would want the agreement in place before cataloguing anything.
