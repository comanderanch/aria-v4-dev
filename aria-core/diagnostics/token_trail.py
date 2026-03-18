#!/usr/bin/env python3
"""
ARIA — Token Trail Diagnostic System
======================================
Visible inner workings during training.
Not black box. Not loss number only.
Full token activation map — lit up as it happens.

The plow shows its work.
The farmer sees exactly which rows broke loose and why.

Commander Anthony Hagerty — Haskell Texas
March 18 2026

Usage (in training loop):
    from aria_core.diagnostics.token_trail import TrailLogger
    trail = TrailLogger(round_num=22, tokenizer=tokenizer)
    # in epoch loop:
    trail.log_batch(epoch, avg_loss, inputs, targets, logits, best_loss)
    trail.close()

Usage (analysis):
    python3 aria-core/diagnostics/token_trail.py \\
        --round 22 \\
        --show-breakthroughs \\
        --show-plateaus \\
        --top-tokens 10
"""

import sys
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

# ─── lazy torch import (not needed for analysis mode) ───────
_torch = None
_F     = None
def _get_torch():
    global _torch, _F
    if _torch is None:
        import torch
        import torch.nn.functional as F
        _torch = torch
        _F     = F
    return _torch, _F

TRAIL_FILE = Path("/tmp/aria-token-trail.jsonl")
PLATEAU_PATIENCE = 10   # epochs with no improvement = plateau
LOG_EVERY_N_EPOCHS = 5  # log a full activation entry every N epochs


# ═══════════════════════════════════════════════
# TOKEN MAP — built from tokenizer
# ═══════════════════════════════════════════════
class TokenMap:
    """Fast lookup: token_id → (word, plane, freq)"""

    def __init__(self, tokenizer):
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from tokenizer.aria_tokenizer import WORD_FREQUENCIES

        self.id_to_word  = {int(k): v for k, v in tokenizer.id_to_word.items()}
        self.word_to_plane = tokenizer.word_to_plane
        self.word_freqs  = WORD_FREQUENCIES
        self.unk_id      = tokenizer.vocab.get("<UNK>", 2301)
        self.pad_id      = tokenizer.vocab.get("<PAD>", 2300)

    def lookup(self, token_id):
        word  = self.id_to_word.get(token_id, f"<{token_id}>")
        plane = self.word_to_plane.get(word, "GRAY_ZERO")
        freq  = self.word_freqs.get(word, 0.0)
        return word, plane, freq


# ═══════════════════════════════════════════════
# TRAIL LOGGER — used in training loop
# ═══════════════════════════════════════════════
class TrailLogger:
    """
    Attaches to a training loop.
    Samples activation patterns and logs to JSONL.
    Minimal overhead — samples every N epochs.
    Seals anchor points unconditionally.
    """

    def __init__(self, round_num, tokenizer, trail_file=None):
        self.round      = round_num
        self.tok_map    = TokenMap(tokenizer)
        self.trail_file = Path(trail_file) if trail_file else TRAIL_FILE
        self.fh         = open(self.trail_file, "a", buffering=1)
        self.best_loss  = float('inf')
        self.plateau_count = 0
        self.last_logged_loss = float('inf')

    def log_batch(self, epoch, avg_loss, inputs, targets, logits, current_best):
        """
        Called once per epoch (after training loop).
        inputs:  (B, S) token IDs
        targets: (B, S) token IDs
        logits:  (B, S, V) raw logits (before vocab mask applied is fine,
                 but pass post-mask logits for accuracy)
        """
        torch, F = _get_torch()

        is_new_best   = avg_loss < current_best
        is_plateau    = self._check_plateau(avg_loss)
        is_breakthrough = self._check_breakthrough(avg_loss)
        should_sample = (epoch % LOG_EVERY_N_EPOCHS == 0 or
                         epoch == 1 or
                         is_new_best or
                         is_plateau or
                         is_breakthrough)

        if not should_sample:
            return

        anchor = None
        if is_new_best:
            anchor = "NEW_BEST"
        elif is_breakthrough:
            anchor = "BREAKTHROUGH"
        elif is_plateau:
            anchor = "PLATEAU"

        # ── Per-token loss (first batch item) ──────────────
        with torch.no_grad():
            B, S, V = logits.shape
            per_token = F.cross_entropy(
                logits.view(B * S, V),
                targets.view(B * S),
                reduction='none',
                ignore_index=self.tok_map.pad_id
            ).view(B, S)

        # Use first batch item as representative sample
        sample_inputs = inputs[0].tolist()
        sample_contrib = per_token[0].tolist()

        # ── Top contributing tokens ─────────────────────────
        pairs = list(zip(sample_inputs, sample_contrib))
        pairs.sort(key=lambda x: x[1], reverse=True)

        top_activations = []
        for tid, contrib in pairs[:10]:
            if tid == self.tok_map.pad_id:
                continue
            word, plane, freq = self.tok_map.lookup(tid)
            top_activations.append({
                "token":        word,
                "id":           tid,
                "plane":        plane,
                "freq":         round(freq, 4),
                "contribution": round(float(contrib), 6)
            })

        # ── Gradient path (plane sequence by contribution) ──
        plane_totals = defaultdict(float)
        for tid, contrib in pairs:
            if tid == self.tok_map.pad_id:
                continue
            _, plane, _ = self.tok_map.lookup(tid)
            plane_totals[plane] += contrib

        sorted_planes = sorted(plane_totals.items(), key=lambda x: x[1], reverse=True)
        gradient_path = "->".join(p for p, _ in sorted_planes[:4])

        # ── Fold hash of activation pattern ─────────────────
        pattern_str = "|".join(
            f"{a['token']}:{a['contribution']:.4f}"
            for a in top_activations[:5]
        )
        fold_hash = hashlib.sha256(pattern_str.encode()).hexdigest()[:7]

        # ── Plane distribution ───────────────────────────────
        plane_counts = Counter()
        for tid in sample_inputs:
            if tid != self.tok_map.pad_id:
                _, plane, _ = self.tok_map.lookup(tid)
                plane_counts[plane] += 1

        entry = {
            "epoch":           epoch,
            "round":           self.round,
            "loss":            round(float(avg_loss), 6),
            "anchor":          anchor,
            "top_activations": top_activations,
            "gradient_path":   gradient_path,
            "plane_distribution": dict(plane_counts.most_common(5)),
            "fold_hash":       fold_hash,
            "timestamp":       datetime.utcnow().isoformat()
        }

        self.fh.write(json.dumps(entry) + "\n")
        self.fh.flush()

        # Print anchor events immediately
        if anchor:
            print(f"\n  [TRAIL] {anchor} epoch={epoch} loss={avg_loss:.6f} "
                  f"path={gradient_path} hash={fold_hash}")

        self.last_logged_loss = avg_loss

    def _check_plateau(self, loss):
        delta = abs(loss - self.last_logged_loss)
        if delta < 0.001:
            self.plateau_count += 1
        else:
            self.plateau_count = 0
        return self.plateau_count >= PLATEAU_PATIENCE

    def _check_breakthrough(self, loss):
        thresholds = [4.0, 3.5, 3.0, 2.8, 2.6, 2.465939, 2.4, 2.35]
        for t in thresholds:
            if self.last_logged_loss > t >= loss:
                return True
        return False

    def close(self):
        self.fh.close()


# ═══════════════════════════════════════════════
# ANALYSIS — CLI mode
# ═══════════════════════════════════════════════
def load_trail(round_num=None, trail_file=None):
    path = Path(trail_file) if trail_file else TRAIL_FILE
    if not path.exists():
        return []
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                if round_num is None or e.get("round") == round_num:
                    entries.append(e)
            except json.JSONDecodeError:
                continue
    return entries


def show_breakthroughs(entries):
    print("\n═══ BREAKTHROUGH EVENTS ═══")
    breaks = [e for e in entries if e.get("anchor") in ("BREAKTHROUGH", "NEW_BEST")]
    if not breaks:
        print("  None recorded yet.")
        return
    for e in breaks:
        print(f"\n  Epoch {e['epoch']:4d} | Loss {e['loss']:.6f} | {e.get('anchor','')} | hash={e['fold_hash']}")
        print(f"  Path: {e['gradient_path']}")
        tops = e.get("top_activations", [])[:5]
        for a in tops:
            print(f"    {a['token']:<20} plane={a['plane']:<15} contrib={a['contribution']:.6f}")


def show_plateaus(entries):
    print("\n═══ PLATEAU EVENTS ═══")
    plats = [e for e in entries if e.get("anchor") == "PLATEAU"]
    if not plats:
        print("  None recorded yet.")
        return
    for e in plats:
        print(f"\n  Epoch {e['epoch']:4d} | Loss {e['loss']:.6f} | Plateau | hash={e['fold_hash']}")
        print(f"  Path: {e['gradient_path']}")
        tops = e.get("top_activations", [])[:3]
        for a in tops:
            print(f"    {a['token']:<20} plane={a['plane']:<15} contrib={a['contribution']:.6f}")


def show_top_tokens(entries, n=10):
    print(f"\n═══ TOP {n} TOKENS BY TOTAL CONTRIBUTION ═══")
    token_totals = defaultdict(lambda: {"total": 0.0, "count": 0, "plane": "", "freq": 0.0})
    for e in entries:
        for a in e.get("top_activations", []):
            w = a["token"]
            token_totals[w]["total"] += a["contribution"]
            token_totals[w]["count"] += 1
            token_totals[w]["plane"] = a["plane"]
            token_totals[w]["freq"]  = a["freq"]

    ranked = sorted(token_totals.items(), key=lambda x: x[1]["total"], reverse=True)
    for word, info in ranked[:n]:
        avg = info["total"] / max(info["count"], 1)
        print(f"  {word:<20} plane={info['plane']:<15} "
              f"total={info['total']:.4f}  avg={avg:.6f}  appearances={info['count']}")


def show_plane_activity(entries):
    print("\n═══ COLOR PLANE ACTIVITY ═══")
    plane_loss = defaultdict(float)
    plane_hits = defaultdict(int)
    for e in entries:
        for plane, count in e.get("plane_distribution", {}).items():
            plane_hits[plane] += count
        for a in e.get("top_activations", []):
            plane_loss[a["plane"]] += a["contribution"]

    ranked = sorted(plane_loss.items(), key=lambda x: x[1], reverse=True)
    for plane, total in ranked:
        hits = plane_hits.get(plane, 0)
        print(f"  {plane:<20} loss_contribution={total:.4f}  token_hits={hits}")


def show_loss_arc(entries):
    print("\n═══ LOSS ARC ═══")
    for e in entries:
        anchor = e.get("anchor") or ""
        marker = f" ◄ {anchor}" if anchor else ""
        bar    = "█" * int((5.0 - min(e["loss"], 5.0)) * 8)
        print(f"  ep{e['epoch']:4d} | {e['loss']:.6f} | {bar}{marker}")


# ═══════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ARIA Token Trail — visible inner workings"
    )
    parser.add_argument("--round",              type=int,   default=None)
    parser.add_argument("--show-breakthroughs", action="store_true")
    parser.add_argument("--show-plateaus",      action="store_true")
    parser.add_argument("--show-planes",        action="store_true")
    parser.add_argument("--show-arc",           action="store_true")
    parser.add_argument("--top-tokens",         type=int,   default=0)
    parser.add_argument("--trail-file",         type=str,   default=None)
    parser.add_argument("--all",                action="store_true")
    args = parser.parse_args()

    entries = load_trail(args.round, args.trail_file)

    if not entries:
        r = f" round {args.round}" if args.round else ""
        print(f"No trail entries found{r}.")
        print(f"Trail file: {args.trail_file or TRAIL_FILE}")
        sys.exit(0)

    print(f"\nARIA Token Trail — {len(entries)} entries"
          + (f" (round {args.round})" if args.round else ""))

    if args.all or args.show_breakthroughs:
        show_breakthroughs(entries)

    if args.all or args.show_plateaus:
        show_plateaus(entries)

    if args.all or args.top_tokens:
        n = args.top_tokens if args.top_tokens else 10
        show_top_tokens(entries, n)

    if args.all or args.show_planes:
        show_plane_activity(entries)

    if args.all or args.show_arc:
        show_loss_arc(entries)

    if not any([args.all, args.show_breakthroughs, args.show_plateaus,
                args.top_tokens, args.show_planes, args.show_arc]):
        # Default: summary
        show_loss_arc(entries)
        show_top_tokens(entries, 5)
