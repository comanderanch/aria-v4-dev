#!/usr/bin/env python3
"""
ARIA — Calibre Corpus Builder
==============================
Extracts text from Calibre epub library on Unraid NFS share.
Combines with existing 4 training .md files.
Output: calibre_corpus.txt — the wall-breaker.

March 17 2026 — Haskell Texas
NO RETREAT. NO SURRENDER. 💙🐗
"""

import sys
import re
import zipfile
from pathlib import Path
from io import BytesIO

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: pip install beautifulsoup4")
    sys.exit(1)


# ═══════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════
CALIBRE_ROOT   = Path.home() / "unraid_shares/multimedia/allbooks/everybook"
OUTPUT_PATH    = Path(__file__).parent / "calibre_corpus.txt"
MIN_WORDS      = 500       # skip tiny files
MAX_WORDS_PER  = 50_000    # cap per book — variety over depth
MAX_TOTAL      = 5_000_000 # 5M words total cap


def epub_to_text(epub_path):
    """Extract plain text from epub using zipfile + BeautifulSoup."""
    try:
        with zipfile.ZipFile(epub_path, 'r') as zf:
            # Find all HTML/XHTML content files
            names = zf.namelist()
            html_files = [n for n in names if n.endswith(('.html', '.xhtml', '.htm'))]
            # Sort by name for reading order
            html_files.sort()

            parts = []
            for hf in html_files:
                try:
                    data = zf.read(hf)
                    soup = BeautifulSoup(data, 'html.parser')
                    # Remove script/style
                    for tag in soup(['script', 'style', 'head']):
                        tag.decompose()
                    text = soup.get_text(separator=' ')
                    parts.append(text)
                except Exception:
                    continue

            if not parts:
                return None
            return ' '.join(parts)

    except Exception:
        return None


def clean_text(raw):
    """Normalize whitespace and remove junk."""
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', raw)
    # Remove non-printable chars
    text = re.sub(r'[^\x20-\x7E\n]', ' ', text)
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove email addresses
    text = re.sub(r'\S+@\S+\.\S+', '', text)
    # Collapse again
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def word_count(text):
    return len(text.split())


# ═══════════════════════════════════════════════
# FIND ALL EPUBS
# ═══════════════════════════════════════════════
print()
print("╔══════════════════════════════════════════════╗")
print("║   ARIA — CALIBRE CORPUS BUILDER             ║")
print("║   Extracting from Unraid NFS library        ║")
print("║       March 17 2026 — Haskell Texas         ║")
print("╚══════════════════════════════════════════════╝")
print()

if not CALIBRE_ROOT.exists():
    print(f"ERROR: Calibre root not found: {CALIBRE_ROOT}")
    sys.exit(1)

epub_files = list(CALIBRE_ROOT.rglob("*.epub"))
print(f"  Found: {len(epub_files)} epub files")
print(f"  Output: {OUTPUT_PATH}")
print(f"  Cap: {MAX_WORDS_PER:,} words/book | {MAX_TOTAL:,} total words")
print()

# ═══════════════════════════════════════════════
# EXISTING TRAINING DATA (always include)
# ═══════════════════════════════════════════════
training_dir = Path(__file__).parent
aria_dir     = training_dir.parent

existing_paths = [
    (aria_dir / "ARIA_SEED_STORY.md",          "Seed story"),
    (training_dir / "round2_training_data.md",  "Origin stories"),
    (training_dir / "round3_language_data.md",  "Language data"),
    (training_dir / "round4_conversation_data.md", "Conversation patterns"),
]

corpus_parts = []
existing_words = 0

print("Including existing training data:")
for path, name in existing_paths:
    if path.exists():
        text = path.read_text(encoding='utf-8', errors='replace')
        wc   = word_count(text)
        corpus_parts.append(text)
        existing_words += wc
        print(f"  {name}: {wc:,} words")
    else:
        print(f"  NOT FOUND: {path}")

print(f"  Existing total: {existing_words:,} words")
print()

# ═══════════════════════════════════════════════
# EXTRACT EPUBS
# ═══════════════════════════════════════════════
print("Extracting epubs...")
total_words   = existing_words
books_added   = 0
books_skipped = 0
books_failed  = 0

# Prioritize fiction — sort by path so Novels/ comes last (alphabetically after Epub/)
# We'll process all but cap per-book
epub_files_sorted = sorted(epub_files, key=lambda p: p.name.lower())

for i, epub_path in enumerate(epub_files_sorted):
    if total_words >= MAX_TOTAL:
        print(f"  Total word cap reached ({MAX_TOTAL:,}). Stopping.")
        break

    raw = epub_to_text(epub_path)
    if raw is None:
        books_failed += 1
        continue

    text = clean_text(raw)
    wc   = word_count(text)

    if wc < MIN_WORDS:
        books_skipped += 1
        continue

    # Cap per book
    if wc > MAX_WORDS_PER:
        words = text.split()[:MAX_WORDS_PER]
        text  = ' '.join(words)
        wc    = MAX_WORDS_PER

    corpus_parts.append(text)
    total_words += wc
    books_added += 1

    if books_added % 50 == 0 or books_added <= 5:
        print(f"  [{books_added:4d}] {epub_path.name[:55]:<55} {wc:>7,}w  total={total_words:>9,}")

print()
print(f"  Books added:   {books_added}")
print(f"  Books skipped: {books_skipped} (< {MIN_WORDS} words)")
print(f"  Books failed:  {books_failed} (parse error)")
print(f"  Total words:   {total_words:,}")
print()

# ═══════════════════════════════════════════════
# WRITE OUTPUT
# ═══════════════════════════════════════════════
print(f"Writing corpus to {OUTPUT_PATH.name}...")
combined = "\n\n".join(corpus_parts)
OUTPUT_PATH.write_text(combined, encoding='utf-8', errors='replace')

size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
print(f"  Size: {size_mb:.1f} MB")
print(f"  Words: {total_words:,}")
print()
print("Corpus sealed.")
print()
print("NOT standard. NOT scared.")
print("NO RETREAT. NO SURRENDER. 💙🐗")
