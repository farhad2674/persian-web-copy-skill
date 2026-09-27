#!/usr/bin/env python3
"""Read-only Persian copy hints. Python 3.9+, standard library, no AI/SEO score."""
import argparse
import json
import re
import sys
from pathlib import Path

RULES = [
    ("arabic_letters", re.compile(r"[كي]"),
     "ی/ک عربی دیده شد؛ در نثر فارسی و با حفظ نقل‌قول/نام بررسی کنید."),
    ("tatweel", re.compile("\u0640+"),
     "کشیدهٔ دستی دیده شد؛ نیاز واقعی آن را بررسی کنید."),
    ("bidi_control", re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]"),
     "کنترل جهت نامرئی دیده شد؛ ممکن است لازم باشد. خودکار حذف نکنید."),
    ("space_before_punctuation", re.compile(r"(?<=[\u0600-\u06ff]) +[،؛؟.!]"),
     "فاصلهٔ پیش از نشانه را بررسی کنید."),
    ("possible_zwnj", re.compile(
        r"(?<![\w\u200c])(?:نمی|می) +(?:توان(?:م|ی|د|یم|ید|ند)|شود|شوند|کنید|کنیم|کند|کنند)(?![\w\u200c])"),
     "در این فعل احتمالاً نیم‌فاصله لازم است؛ با جمله تطبیق دهید."),
    ("repeated_punctuation", re.compile(r"[!！؟?]{2,}"),
     "تأکید نگارشیِ تکراری را با لحن برند مقایسه کنید."),
    ("stock_phrase", re.compile(
        r"در دنیای امروز|تحول شگرف|تجربه[‌ ]ای بی[‌ ]نظیر|می[‌ ]باشد|می[‌ ]گردد|لازم به ذکر است"),
     "عبارت کلیشه‌ای/اداری احتمالی؛ فقط اگر به پیام کمک نمی‌کند بازنویسی کنید."),
]
# Mask protected text while preserving positions and newlines. This is not a parser.
PROTECTED = re.compile(
    r"https?://[^\s<>]+|www\.[^\s<>]+|`[^`\n]*`|"
    r"\{\{[^{}\n]*\}\}|\{[A-Za-z_][A-Za-z0-9_.]*\}|"
    r"%\([A-Za-z_][A-Za-z0-9_]*\)[sdf]|%[sdf]|<[^>\n]+>"
)


def blank(match):
    return re.sub(r"[^\n]", " ", match.group(0))


def mask_text(text):
    # Ignore fenced Markdown code; leave other Markdown available for review.
    lines = text.splitlines(keepends=True)
    fence = None
    out = []
    for line in lines:
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if fence is None and marker:
            fence = marker.group(1)
            out.append(re.sub(r"[^\n]", " ", line))
        elif fence is not None:
            out.append(re.sub(r"[^\n]", " ", line))
            if (marker and marker.group(1)[0] == fence[0]
                    and len(marker.group(1)) >= len(fence)
                    and not line[marker.end():].strip()):
                fence = None
        else:
            out.append(line)
    return PROTECTED.sub(blank, "".join(out))


def strings(value, pointer=""):
    if isinstance(value, str):
        yield pointer or "/", value
    elif isinstance(value, dict):
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            yield from strings(child, pointer + "/" + escaped)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from strings(child, pointer + "/" + str(index))


def audit(segments):
    findings = []
    characters = 0
    words = 0
    for location, original in segments:
        text = mask_text(original)
        characters += len(original)
        words += len(re.findall(r"[^\W\d_]+(?:\u200c[^\W\d_]+)*", text))
        for code, pattern, hint in RULES:
            for match in pattern.finditer(text):
                offset = match.start()
                line = original.count("\n", 0, offset) + 1
                column = offset - original.rfind("\n", 0, offset)
                findings.append({
                    "location": location, "line": line, "column": column,
                    "code": code, "text": original[match.start():match.end()],
                    "hint": hint,
                })
    return {
        "notice": "سرنخ ویرایشی؛ بدون تغییر فایل و بدون امتیاز انسانی‌بودن یا سئو.",
        "counts": {"characters": characters, "approximate_words": words,
                   "hints": len(findings)},
        "findings": findings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="UTF-8 .txt, .md, or .json copy")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()
    if args.path.suffix.lower() not in {".txt", ".md", ".json"}:
        parser.error("Use extracted copy in a .txt, .md, or .json file, not source code.")
    try:
        raw = args.path.read_text(encoding="utf-8-sig")
        if args.path.suffix.lower() == ".json":
            segments = list(strings(json.loads(raw)))
        else:
            segments = [(str(args.path), raw)]
        if not segments or not any(value.strip() for _, value in segments):
            parser.error("The input has no nonempty text values to inspect.")
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    report = audit(segments)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(report["notice"])
        print("تعداد سرنخ‌ها:", report["counts"]["hints"])
        for item in report["findings"]:
            print(f'{item["location"]}:{item["line"]}:{item["column"]} '
                  f'[{item["code"]}] {item["hint"]}')
        if not report["findings"]:
            print("سرنخی در قواعد محدود ابزار پیدا نشد؛ این نتیجه تأیید کیفیت متن نیست.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
