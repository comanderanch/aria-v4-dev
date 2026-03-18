#!/usr/bin/env python3
"""
ARIA — Filtered Corpus Builder
================================
Takes calibre_corpus.txt (5M words, 70% known).
Keeps only sequences where ≥75% of words are known.
Eliminates UNK noise — clean gradient signal only.
Output: filtered_corpus.txt

March 18 2026 — Haskell Texas
NO RETREAT. NO SURRENDER. 💙🐗
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tokenizer.aria_tokenizer import ARIATokenizer

SEQ_LENGTH    = 64
STRIDE        = 32          # same as training
MIN_KNOWN_PCT = 0.75        # ≥75% of words must be known
OUTPUT_PATH   = Path(__file__).parent / "filtered_corpus.txt"
CORPUS_PATH   = Path(__file__).parent / "calibre_corpus.txt"

print()
print("╔══════════════════════════════════════════════╗")
print("║   ARIA — FILTERED CORPUS BUILDER            ║")
print("║   Keep sequences ≥75% known words          ║")
print("║       March 18 2026 — Haskell Texas         ║")
print("╚══════════════════════════════════════════════╝")
print()

tokenizer = ARIATokenizer.load()
vocab = set(tokenizer.vocab.keys()) - {"<PAD>","<UNK>","<BOS>","<EOS>"}
print(f"Vocabulary: {len(vocab)} words")
print()

# Load corpus
print(f"Loading corpus: {CORPUS_PATH.name}")
text = CORPUS_PATH.read_text(encoding='utf-8', errors='replace').lower()
words = [w.strip(".,!?;:\"'()-[]{}") for w in text.split()]
total_words = len(words)
print(f"Total words: {total_words:,}")
print()

# Slide a window and keep sequences that pass the known threshold
kept_sequences = []
total_seqs     = 0
kept_count     = 0
rejected_count = 0

for i in range(0, len(words) - SEQ_LENGTH, STRIDE):
    window = words[i:i + SEQ_LENGTH]
    total_seqs += 1

    known = sum(1 for w in window if w in vocab)
    pct   = known / SEQ_LENGTH

    if pct >= MIN_KNOWN_PCT:
        kept_sequences.append(' '.join(window))
        kept_count += 1
    else:
        rejected_count += 1

    if total_seqs % 500_000 == 0:
        print(f"  Processed {total_seqs:,} seqs | Kept: {kept_count:,} "
              f"({100*kept_count//max(total_seqs,1)}%)")

print()
print(f"Total sequences scanned: {total_seqs:,}")
print(f"Kept (≥75% known):       {kept_count:,} ({100*kept_count//max(total_seqs,1)}%)")
print(f"Rejected:                {rejected_count:,}")
print()

if kept_count == 0:
    print("ERROR: No sequences passed the filter. Lower the threshold.")
    sys.exit(1)

# Write filtered corpus — one sequence per line
print(f"Writing to {OUTPUT_PATH.name}...")
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    for seq in kept_sequences:
        f.write(seq + "\n")

size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
print(f"Size: {size_mb:.1f} MB")
print()

# Measure known% in kept sequences
sample_words = ' '.join(kept_sequences[:1000]).split()
known_in_kept = sum(1 for w in sample_words if w in vocab)
pct_in_kept   = 100 * known_in_kept // max(len(sample_words), 1)
print(f"Known% in kept sequences (sample): {pct_in_kept}%")
print()
print("Filtered corpus sealed.")
print("Clean gradient signal — ready for Round 21.")
print()
print("NO RETREAT. NO SURRENDER. 💙🐗")
