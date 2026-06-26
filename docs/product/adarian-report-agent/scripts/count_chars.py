#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Count Chinese characters in a text file.

手动调试用。T3 使用 LLM 自估字数，不调用此脚本。
Outputs machine-readable format for manual debugging.
"""
import re
import sys
import argparse
from pathlib import Path


# Ranges that constitute "Chinese characters" for word-count purposes.
# CJK Unified Ideographs + Extensions + Compatibility
_CJK_RANGES = [
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs (core hanzi)
    (0x3400, 0x4DBF),   # CJK Extension A
    (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
]

# Chinese punctuation counted as part of word count
_PUNCT_RANGES = [
    (0x3000, 0x303F),   # CJK Symbols and Punctuation
    (0xFF00, 0xFFEF),   # Fullwidth Forms
]


def _in_ranges(cp, ranges):
    for lo, hi in ranges:
        if lo <= cp <= hi:
            return True
    return False


def count_chinese_chars(text):
    """Return count of Chinese characters (hanzi + punctuation) in text."""
    count = 0
    for ch in text:
        cp = ord(ch)
        if _in_ranges(cp, _CJK_RANGES) or _in_ranges(cp, _PUNCT_RANGES):
            count += 1
    return count


def strip_markdown(text):
    """Remove common markdown syntax to count only rendered text."""
    # Remove code blocks (```...```)
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove inline code
    text = re.sub(r'`[^`]+`', '', text)
    # Remove headings markers (##, ###, etc.) but keep heading text
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    # Remove links: [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove images: ![alt](url)
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
    # Remove blockquote markers
    text = re.sub(r'^>\s?', '', text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Remove list markers
    text = re.sub(r'^\s*[-*+]\s', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s', '', text, flags=re.MULTILINE)
    return text


def main():
    parser = argparse.ArgumentParser(
        description="Count Chinese characters in a text file"
    )
    parser.add_argument("file", help="Path to text file")
    parser.add_argument(
        "--target", type=int, default=None,
        help="Target character count; if given, also prints delta"
    )
    parser.add_argument(
        "--target-min", type=int, default=None,
        help="Minimum target; prints how many below if under"
    )
    parser.add_argument(
        "--target-max", type=int, default=None,
        help="Maximum target; prints how many over if above"
    )
    parser.add_argument(
        "--strip-md", action="store_true",
        help="Strip markdown syntax before counting"
    )
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    text = path.read_text(encoding="utf-8")
    if args.strip_md:
        text = strip_markdown(text)

    count = count_chinese_chars(text)

    # Machine-readable output for agents
    print(f"chinese_char_count: {count}")

    if args.target_min is not None and count < args.target_min:
        delta = args.target_min - count
        print(f"BELOW_MIN: need {delta} more chars (current={count}, min={args.target_min})")
    if args.target_max is not None and count > args.target_max:
        delta = count - args.target_max
        print(f"ABOVE_MAX: need {delta} fewer chars (current={count}, max={args.target_max})")
    if args.target is not None:
        delta = count - args.target
        if delta >= 0:
            print(f"delta: +{delta} (target={args.target}, current={count})")
        else:
            print(f"delta: {delta} (target={args.target}, current={count})")


if __name__ == "__main__":
    main()
