"""Pre-commit check: block commits that contain private data.

Scans the files being committed for email addresses, phone numbers and
any private terms listed (one regex per line) in the local, gitignored
file .sensitive-patterns. Keeping those terms out of the repo means this
public script never reveals what it is protecting.
"""
import re
import sys
from pathlib import Path

ALLOWED_EMAIL_DOMAINS = ("example.com", "users.noreply.github.com")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE = re.compile(r"\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")


def load_private_patterns():
    path = Path(".sensitive-patterns")
    if not path.exists():
        print("warning: .sensitive-patterns not found; private-term check skipped")
        return []
    lines = [l.strip() for l in path.read_text().splitlines()]
    return [re.compile(l, re.IGNORECASE) for l in lines if l and not l.startswith("#")]


def main(files):
    private = load_private_patterns()
    problems = []
    for name in files:
        try:
            text = Path(name).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue  # binary or removed file
        for n, line in enumerate(text.splitlines(), 1):
            for m in EMAIL.finditer(line):
                if not m.group(1).lower().endswith(ALLOWED_EMAIL_DOMAINS):
                    problems.append(f"{name}:{n}: email address")
            if PHONE.search(line):
                problems.append(f"{name}:{n}: phone-number pattern")
            for p in private:
                if p.search(line):
                    problems.append(f"{name}:{n}: private term")
    if problems:
        print("Sensitive content found. Commit blocked:")
        print("\n".join(sorted(set(problems))))
        print("Remove it, or if it is a false positive, adjust the file and retry.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
