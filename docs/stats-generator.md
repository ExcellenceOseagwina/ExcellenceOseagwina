# GitHub Stats Generator

This repository generates the animated `stats.svg` profile dashboard from GitHub's GraphQL API.

## Run locally

```bash
python generate_stats.py --sample
```

For live data, set `GITHUB_TOKEN` and optionally `GH_USER`, `TZ_OFFSET_HOURS`, and `OUT` before running `python generate_stats.py`. In PowerShell:

```powershell
$env:GITHUB_TOKEN = "YOUR_TOKEN"
$env:GH_USER = "ExcellenceOseagwina"
python .\generate_stats.py
python .\scripts\validate_svg.py .\stats.svg
```

Never commit or print tokens. Use a fine-grained token with the minimum access required; public profile reads generally need no additional repository scopes.

## Quality and security checks

Install development tools with `python -m pip install ruff bandit`, then run:

```bash
ruff check generate_stats.py tests scripts
bandit -q -r generate_stats.py scripts
python -m unittest discover -s tests -v
python scripts/validate_svg.py stats.svg
```

The SVG validator parses the XML and rejects script-capable/embedded elements, event-handler attributes, and external or executable resource references. It is a focused safety check, not a complete SVG sanitizer.

GitHub Actions runs quality checks in a read-only job. Only the separate generation job receives `contents: write`, and only the generation step receives the API token. Third-party actions are pinned to full commit SHAs.

## Metrics and limitations

- Contributions and streaks come from GitHub's contribution calendar.
- Public repository and star totals cover public, non-fork repositories owned by the queried account.
- Commit totals sum author-filtered commit-history `totalCount` values on each repository's default branch, not every branch.
- Commits-by-hour uses only the first 100 matching commit timestamps per repository, while the total uses GraphQL's `totalCount`.
- Language-by-repository uses each repository's primary language; language-by-commit attributes default-branch commit totals to that primary language; language-by-size aggregates GitHub's returned language byte sizes. These metrics are not interchangeable.
- Commit-hour calculations apply `TZ_OFFSET_HOURS`. Contribution-day calculations use GitHub calendar dates and the runner's local date, so date boundaries may differ near midnight.
- The dashboard is a periodic snapshot, not a live connection or proof that the account is currently active.
