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

1. `search_sources.py` runs eight search queries against public search endpoints. No API key and
   no login, just ordinary result pages. It tries DuckDuckGo, then DuckDuckGo lite, then Mojeek,
   moving on when one refuses to answer. The raw rows are cached to `data/search_cache.json`.
2. `extract_candidates.py` turns those rows into one record per URL, keeping the source name,
   publisher, URL, title and description. Nothing else is fetched.
3. `score_candidates.py` scores each candidate and decides whether it passes.
4. `report.py` prints the ranked list with a one line justification per source, then prints the
   limits of what any of this establishes.

The searches are written to look for university labs, clinics, established nonprofits and
material published alongside peer reviewed work. There are deliberately no queries that would
pull in family vlogs or personal channels. It would be strange to go looking for the exact
material the scoring step exists to reject.

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
me five of the eight searches. And an empty result now raises instead of being written to the
cache, because on one run a throttled search overwrote a good snapshot with nothing, which is a
worse failure than crashing.

Backend matters more than I expected. A run that fell back entirely to the smaller index
returned a much weaker set of sources than the same queries against the larger one. The
committed snapshot came from DuckDuckGo. If you refresh and get noticeably worse results, check
which backend answered before blaming the scoring.

## The scoring criteria and why these ones

Ninety points across three criteria, with a pass mark of 55 and two conditions that override the
score entirely.

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

**Personal content red flags, disqualifying.** Phrases like "my son", "day in the life", "vlog",
"subscribe" and "sponsored by" reject a candidate outright regardless of score. These suggest
either a specific identifiable child as the subject or an audience building motive, and both put
a source out of scope. This one disqualifies rather than deducting because a vetting tool should
fail closed. A false rejection costs one candidate. A false acceptance puts a real child's video
into a research pipeline.

I should be honest about the limit here. This reads titles and search snippets, so it catches
the obvious cases and will miss anything subtler. It narrows the pile a human has to look at. It
does not replace the human.

## How appropriateness and relevance are actually verified

They are not, and I want to be exact about this rather than let the word "vetted" do more work
than it should.

The tool establishes that a source looks institutional, reads as research or educational, and
shows no obvious personal content markers. That is a defensible shortlist. It is not
verification. Verification would mean a person opening each source, reading the organization's
terms, and asking them directly what consent the recorded people gave. Everything here is
inference from a title and two lines of text.

A passing score means the source is worth a human looking at. Nothing more.

## Results

The committed snapshot has 80 raw results across 8 queries, which reduce to 68 distinct sources.
Of those, 11 passed and 57 were filtered out.

The top of the list is what I hoped the criteria would surface:

| Score | Source |
|---|---|
| 90 | Rutgers Graduate School of Applied and Professional Psychology, autism diagnostic training |
| 90 | Masonic Institute for the Developing Brain, University of Minnesota |
| 76 | Interagency Autism Coordinating Committee, archived video (hhs.gov) |
| 68 | University of Michigan autism toolkit |
| 68 | Voices of Autism video library, CU Anschutz |
| 68 | Thompson Center for Autism, University of Missouri |
| 68 | AIR-P Network archived webinars, UCLA |

The 57 rejections break down as 29 with no evidence of video, 15 scoring below the pass mark,
and 13 with no research or educational language. Nothing was rejected for personal content
markers, which I come back to below.

See [results/terminal_output.png](results/terminal_output.png) for a full run, and
`results/vetted_candidates.csv` for the complete scored list including everything filtered out.

## Where this is weak

Three things I would want a reviewer to know rather than discover.

The personal content rule never fired on this snapshot. Zero of 57 rejections came from it. That
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

## What a real version would need

IRB approval, before any video is collected rather than after a prototype exists.

Direct agreements with each publishing organization. Not a license file on a web page, an actual
conversation with the people who hold the material, covering what the footage may be used for
and by whom.

A formal consent position for every source, confirmed in writing with the organization. This is
the part the tool cannot touch. It would need to establish what the recorded people or their
guardians actually agreed to, which is a legal and ethical question rather than a technical one,
and the honest answer is often that nobody knows because the recordings predate anyone thinking
to ask.

A data handling plan covering storage, access and retention, since video of identifiable
children is about as sensitive as research data gets.

Human review of every shortlisted source. The scoring here decides what a person looks at first.
It should never decide what gets used.
