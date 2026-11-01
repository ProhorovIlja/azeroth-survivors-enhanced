"""Bounded, redacted diagnostic summaries. Raw logs stay local/private."""
import argparse
import collections
import json
import re
from pathlib import Path

ERROR = re.compile(r"error|exception|panic|crash|traceback|failed|fatal|warn", re.I)
REDACT = [
    (re.compile(r"(?i)(authorization:\s*bearer\s+)\S+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(token|password|secret|api[_-]?key)\s*[:=]\s*[^\s,;]+"), r"\1=[REDACTED]"),
    (re.compile(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    (re.compile(r"\b0x[0-9A-Fa-f]+\b"), "0xADDR"),
]
MAX_UNIQUE = 512


def digest(path, max_examples=15):
    cap = min(max(int(max_examples), 0), 40)
    lines, flagged, overflow = 0, 0, 0
    frequencies = collections.Counter()
    examples = []
    with Path(path).open(encoding="utf-8", errors="replace") as stream:
        for raw in stream:
            lines += 1
            if not ERROR.search(raw):
                continue
            flagged += 1
            safe = raw.strip()
            for pattern, replacement in REDACT:
                safe = pattern.sub(replacement, safe)
            safe = safe[:320]
            if safe in frequencies or len(frequencies) < MAX_UNIQUE:
                frequencies[safe] += 1
            else:
                overflow += 1
            if len(examples) < cap and safe not in examples:
                examples.append(safe)
    return {
        "lines": lines, "issue_lines": flagged, "unique_fingerprints_kept": len(frequencies),
        "overflow_unique_lines": overflow,
        "top_fingerprints": [{"text": text, "count": count} for text, count in frequencies.most_common(cap)],
        "examples": examples, "max_chat_chars": 2400,
    }


def main():
    p = argparse.ArgumentParser(description="Summarize private logs, do not paste raw logs into chat")
    p.add_argument("log")
    p.add_argument("--out", default="artifacts/log-summary.json")
    a = p.parse_args()
    result = digest(a.log)
    path = Path(a.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{result['lines']} lines; {result['issue_lines']} flagged; private summary saved to {path}")


if __name__ == "__main__":
    main()
