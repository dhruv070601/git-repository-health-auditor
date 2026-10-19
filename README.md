 # Git Repository Health Auditor

A lightweight Python CLI that checks a local Git repository for common hygiene risks and generates Markdown and JSON reports. Built as a Git/GitHub portfolio project; it does not require Jenkins or third-party Python dependencies.

## Checks
- Clean or dirty working tree and current branch
- Commit history and potentially stale local branches
- Missing .gitignore, README, or license file
- Large tracked files that may belong in Git LFS or artifact storage
- A small set of possible hard-coded secret patterns
- Actionable recommendations in Markdown and JSON

## Run
Requires Python 3.10+ and Git installed.

    python -m unittest discover -s tests -v
    python -m git_health.auditor --repo . --stale-days 90 --large-mb 10 --out-dir health-results

Reports are written to health-results/health-report.md and health-results/health-report.json.

## GitHub Actions
The workflow runs unit tests and audits the checked-out repository on pushes and pull requests. Reports are uploaded as a workflow artifact.

## Important limitations
- The secret scan is heuristic and can miss credentials or report false positives. It is not a substitute for a dedicated secret scanner.
- Stale branch detection uses the latest commit date for local branches only.
- Large-file checks inspect current tracked working-tree sizes, not historical Git object sizes.
- Review findings before acting; the tool does not delete branches or modify repository content.
