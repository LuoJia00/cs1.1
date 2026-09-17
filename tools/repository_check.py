"""Check the actual Git index before publishing; never prints secret values."""
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PREFIXES = ("data/", "assets/", "output/", "logs/", ".venv/", ".local-backups/", ".private-transfer/")
PRIVATE_FILES = {"history.json", "global_config.json", "static/runninghub/api_providers.json", "static/runninghub/models_registry.json"}
SECRET_KEY = re.compile(r"api.?key|token|password|secret|authorization", re.I)
TOKEN = re.compile(rb"(?:(?<![A-Za-z0-9_-])sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{25,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)")


def known_secrets():
    values = set()
    def walk(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if SECRET_KEY.search(key) and isinstance(value, str) and len(value.strip()) >= 12:
                    if not value.startswith(("http:", "https:")):
                        values.add(value.strip().encode())
                else:
                    walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
    for name in ["data/api_providers.json", "global_config.json", "static/runninghub/api_providers.json"]:
        file = ROOT / name
        if file.exists():
            walk(json.loads(file.read_text(encoding="utf-8-sig")))
    env = ROOT / "API/.env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            key, sep, value = line.partition("=")
            value = value.strip().strip("\"'")
            if sep and SECRET_KEY.search(key) and len(value) >= 12:
                values.add(value.encode())
    return values


def main():
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    secrets = known_secrets()
    problems = []
    total = 0
    count = 0
    for name in filter(None, names):
        count += 1
        if name.startswith(PRIVATE_PREFIXES) or name in PRIVATE_FILES or (Path(name).name.startswith(".env") and not name.endswith(".env.example")):
            problems.append((name, "private file in index"))
        content = subprocess.check_output(["git", "show", ":" + name], cwd=ROOT)
        total += len(content)
        if len(content) >= 95 * 1024 * 1024:
            problems.append((name, "file is too large"))
        if TOKEN.search(content) or any(value in content for value in secrets):
            problems.append((name, "possible credential; value hidden"))
    for name, reason in problems:
        print(f"BLOCKED: {name}: {reason}")
    print(f"Checked {count} staged/tracked files, {total / 1024 / 1024:.1f} MiB; findings: {len(problems)}")
    if not count:
        print("No files staged. Run git add after reviewing .gitignore.")
    return 1 if problems or not count else 0


if __name__ == "__main__":
    raise SystemExit(main())
