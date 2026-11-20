# GitHub Stats Generator

This repository generates the animated `stats.svg` profile dashboard from GitHub's GraphQL API.

## Run locally

Preview the layout with deterministic sample-shaped data (no token required):

```bash
python generate_stats.py --sample
```

Generate live statistics:

```bash
# Linux/macOS
GITHUB_TOKEN=YOUR_TOKEN GH_USER=ExcellenceOseagwina python generate_stats.py

# PowerShell
$env:GITHUB_TOKEN = "YOUR_TOKEN"
$env:GH_USER = "ExcellenceOseagwina"
python .\generate_stats.py
```

The token is sent only in the HTTPS Authorization header. Do not commit it, print it, or place it in source files. Public profile data can generally be read with a token that has no additional repository scopes; use the minimum permissions required by your environment.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GH_USER` | `ExcellenceOseagwina` | GitHub login to query |
| `GITHUB_TOKEN` / `GH_TOKEN` | none | GraphQL API authentication |
| `TZ_OFFSET_HOURS` | `1` | Offset used for the commit-by-hour chart |
| `OUT` | `stats.svg` | Generated SVG output path |

Transient network failures and selected HTTP status codes are retried with bounded exponential backoff. A failed generation exits non-zero and does not replace the previous SVG with a partial file.

## Tests

The test suite uses Python's standard library:

```bash
python -m unittest discover -s tests -v
```

## Metric definitions and limitations

- **Contributions and streaks** come from GitHub's contribution calendar. GitHub determines which activity qualifies as a contribution.
- **Public repositories** counts public, non-fork repositories owned by the queried account.
- **Stars** sums stargazers across those repositories.
- **Commit totals** sum the author-filtered commit-history `totalCount` values on each repository's default branch. This is not necessarily the same as all commits across every branch.
- **Commits by hour** uses the timestamps returned in the first 100 matching commit-history nodes per repository. It is therefore a sample of commit timestamps, while the displayed commit total uses GraphQL's `totalCount`.
- **Languages by repository** classifies each repository by its primary language. **Languages by commit** attributes each repository's default-branch commit count to that primary language. **Languages by size** aggregates the language byte sizes returned by GitHub for each repository (up to the API query's top 10 languages per repository). These are different measurements and should not be interpreted as interchangeable percentages.
- The commit-hour chart applies `TZ_OFFSET_HOURS`; contribution-day calculations use calendar dates from GitHub and the runner's local date. Around midnight, the runner's date boundary can differ from the configured commit-hour offset.

The dashboard is a periodic snapshot, not a live connection or proof that the account is currently active.
