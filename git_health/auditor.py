"""Audit a local Git repository and emit a human-readable health report."""
import argparse, json, re, subprocess, time
from pathlib import Path
SECRET_PATTERNS = [
    ("Private key header", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("Possible API token", re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
    ("Possible cloud credential", re.compile(r"(?i)\b(?:aws_access_key_id|client_secret)\s*[:=]\s*['\"]?[A-Za-z0-9/+=_-]{12,}")),
]
def run_git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode: raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()
def audit_repository(repo=".", stale_days=90, large_mb=10):
    root = Path(repo).resolve()
    if run_git(root, "rev-parse", "--is-inside-work-tree") != "true": raise RuntimeError(f"{root} is not a Git working tree")
    findings = []
    def add(severity, title, detail, recommendation):
        findings.append({"severity": severity, "title": title, "detail": detail, "recommendation": recommendation})
    branch = run_git(root, "branch", "--show-current") or "(detached HEAD)"
    status = run_git(root, "status", "--porcelain")
    if status: add("MEDIUM", "Working tree is not clean", f"{len(status.splitlines())} changed or untracked item(s).", "Commit, stash, or intentionally discard changes before a release.")
    else: add("INFO", "Working tree is clean", "No modified, staged, or untracked files.", "Keep the working tree clean for reproducible checks.")
    try:
        count = int(run_git(root, "rev-list", "--count", "--all"))
        add("INFO", "Commit history", f"{count} reachable commit(s); current branch: {branch}.", "Use meaningful commit messages and review history before releases.")
    except (ValueError, RuntimeError): add("LOW", "Commit history unavailable", "Could not count commits.", "Create an initial commit if this repository is new.")
    branches = run_git(root, "for-each-ref", "--format=%(refname:short)|%(committerdate:unix)", "refs/heads").splitlines()
    stale, cutoff = [], int(time.time()) - stale_days * 86400
    for row in branches:
        parts = row.split("|")
        if len(parts) == 2 and parts[1].isdigit() and int(parts[1]) < cutoff: stale.append(parts[0])
    if stale: add("LOW", "Potential stale local branches", ", ".join(stale), f"Review branches older than {stale_days} days; delete only after confirming they are obsolete.")
    else: add("INFO", "Local branch freshness", f"No local branch older than {stale_days} days was detected.", "Periodically prune branches confirmed to be obsolete.")
    tracked = [p for p in run_git(root, "ls-files", "-z").split("\0") if p]
    if not (root / ".gitignore").exists(): add("MEDIUM", "Missing .gitignore", "No root .gitignore exists.", "Exclude caches, local configuration, build output, and secrets.")
    else: add("INFO", ".gitignore present", "A root .gitignore file exists.", "Check that generated files and local secrets are excluded.")
    large_files = []
    for rel in tracked:
        path = root / rel
        try:
            if path.is_file() and path.stat().st_size > large_mb * 1024 * 1024: large_files.append((rel, path.stat().st_size / (1024 * 1024)))
        except OSError: pass
    if large_files: add("MEDIUM", "Large tracked files", ", ".join(f"{name} ({size:.1f} MB)" for name, size in large_files[:20]), "Consider Git LFS or artifact storage for large binaries and generated assets.")
    else: add("INFO", "Tracked file sizes", f"No tracked working-tree file exceeds {large_mb} MB.", "Avoid committing build output and large binary artifacts.")
    secret_hits = []
    for rel in tracked:
        path = root / rel
        if any(part in rel.lower() for part in ("node_modules", "venv", "__pycache__")): continue
        try:
            if not path.is_file() or path.stat().st_size > 1_000_000: continue
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError: continue
        for line_no, line in enumerate(content.splitlines(), 1):
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line): secret_hits.append((rel, line_no, label)); break
    if secret_hits: add("HIGH", "Possible hard-coded secrets", ", ".join(f"{name}:{line} ({label})" for name, line, label in secret_hits[:20]), "Verify findings. Rotate any real exposed credentials and use a secret manager. False positives are possible.")
    else: add("INFO", "Basic secret-pattern scan", "No configured high-signal patterns detected in tracked working-tree files.", "This is not a replacement for a dedicated secret scanner.")
    if not any(n in tracked for n in ("README.md", "README")): add("LOW", "Missing README", "No root README is tracked.", "Document purpose, setup, usage, and contribution workflow.")
    if not any(n in tracked for n in ("LICENSE", "LICENSE.md")): add("LOW", "Missing license file", "No common root license filename is tracked.", "Add an appropriate license if you intend others to reuse the project.")
    return {"repository": str(root), "branch": branch, "finding_count": len(findings), "findings": findings}
def render_markdown(report):
    lines = ["# Git Repository Health Report", "", f"- **Repository:** {report['repository']}", f"- **Branch:** {report['branch']}", f"- **Findings:** {report['finding_count']}", "", "## Findings", ""]
    for item in report["findings"]: lines += [f"### [{item['severity']}] {item['title']}", "", item["detail"], "", f"**Recommendation:** {item['recommendation']}", ""]
    lines += ["---", "_Generated by Git Repository Health Auditor. Findings are heuristic and require human review._", ""]
    return "\n".join(lines)
def main():
    parser = argparse.ArgumentParser(description="Audit Git repository hygiene and generate Markdown/JSON reports.")
    parser.add_argument("--repo", default="."); parser.add_argument("--stale-days", type=int, default=90); parser.add_argument("--large-mb", type=int, default=10); parser.add_argument("--out-dir", default="health-results")
    args = parser.parse_args()
    if args.stale_days < 1 or args.large_mb < 1: parser.error("--stale-days and --large-mb must be positive")
    report = audit_repository(args.repo, args.stale_days, args.large_mb)
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "health-report.md").write_text(render_markdown(report), encoding="utf-8")
    (out / "health-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(render_markdown(report)); print(f"Reports saved to {out.resolve()}")
if __name__ == "__main__": main()
