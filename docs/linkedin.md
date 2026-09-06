# LinkedIn

## No connector, and why

A LinkedIn API integration is the wrong shape for this workspace, on three
grounds.

**It cannot do the thing you would want.** There is no API to update your profile
headline, About section, or experience. Sign In with LinkedIn returns name, email,
and picture, and nothing else. Posting to a personal feed needs partner approval
for a product you would have to apply for and justify. The write path that would
make a connector worth building does not exist for individuals.

**Scraping risks the asset you are protecting.** Automated collection breaches the
user agreement, and enforcement lands on the account. This project exists to
strengthen a professional presence; the connector most likely to be built is the
one most likely to get that presence restricted.

**The export is better than the API anyway.** Settings, then Data privacy, then
Get a copy of your data. The archive is richer than anything the API exposes, and
it is a file drop, which this workspace already handles.

## What the export gives you that a resume does not

`Positions.csv` and `Education.csv` are employment and education with dates, which
is exactly what the `employment` records need and what a resume PDF renders as
fragile two-column text.

`Recommendations_Received.csv` is the interesting one. **It is written by other
people.** Almost everything in a datapack is self-asserted, because a resume and a
LinkedIn profile are both authored by the subject. A recommendation is a named
third party describing your work in their own words, which is the only material in
a normal career archive that can move an atom to `corroborated` and name the
person who would confirm it.

`Skills.csv` endorsements are weaker but still third-party.

## How to use it

Unzip into `data/sources/linkedin-export/` and run `build-career-pack`. Ingestion
should:

- Build `employment` records from `Positions.csv`, preferring its dates over any
  resume PDF, and ask about `employer_of_record` where a role looks like client
  work.
- Read `Recommendations_Received.csv` and, for each atom a recommendation
  supports, add a `corroborators` entry naming the recommender by role and quoting
  the line that supports it. Record the recommendation as a source with
  `independent: true`.
- Treat the profile text itself as self-authored. It is not corroboration, however
  many times a claim appears across your own documents.

The recommendation path is the highest-value ingestion this workspace has, because
corroboration is the pack's structural weakness and recommendations are the only
third-party writing most people already own.
