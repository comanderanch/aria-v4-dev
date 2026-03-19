#!/usr/bin/env python3
"""
ARIA — Lord Log
===============
Cross-reference layer sitting underneath inference trace.
Read-only reference injection. Touches neither source log.

Training log  = what she learned
Inference log = what she decided
Lord log      = did she decide consistent with what she learned
               or did she drift

Join key: checkpoint name — not timestamp.
  inference session_start → checkpoint field → round number
  training trail → filter by round → final epoch = ground truth state

Drift score per plane:
  inference_pct - training_pct
  positive = fires MORE in inference than training expected
  negative = fires LESS — suppressed relative to learned state

Output: /tmp/aria-lord-log.jsonl
        Human-readable drift report to stdout

Commander Anthony Hagerty — Haskell Texas — March 19 2026
NO RETREAT. NO SURRENDER. 💙🐗
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ── CONFIGURATION ──────────────────────────────────────────────────────────────
TRAIL_FILE   = Path("/tmp/aria-token-trail.jsonl")
TRACE_FILE   = Path("/tmp/aria-inference-trace.jsonl")
LORD_FILE    = Path("/tmp/aria-lord-log.jsonl")

# Planes to watch explicitly — in priority order
WATCH_PLANES = [
    "GRAY_ZERO", "VIOLET", "TEAL", "CYAN", "BLUE",
    "INDIGO", "RED", "BLUE_INDIGO", "UNKNOWN"
]

# Drift thresholds
DRIFT_FLAG   = 0.05   # ±5% deviation from training → flag
DRIFT_ALERT  = 0.15   # ±15% deviation → alert


# ── PARSE ROUND FROM CHECKPOINT NAME ──────────────────────────────────────────
def checkpoint_to_round(checkpoint_name):
    """
    Extract round number from checkpoint filename.
    round23_pass2_best.pt → 23
    round7_best.pt        → 7
    Returns None if not parseable.
    """
    m = re.search(r'round(\d+)', checkpoint_name, re.IGNORECASE)
    return int(m.group(1)) if m else None


# ── LOAD TRAINING REFERENCE STATE ─────────────────────────────────────────────
def load_training_reference(round_num):
    """
    Load training trail entries for given round.
    Return the FINAL epoch entry as ground truth reference state.
    That is the state that produced the checkpoint.

    Also returns the full epoch list for gradient path analysis.
    """
    if not TRAIL_FILE.exists():
        return None, []

    round_entries = []
    with open(TRAIL_FILE) as f:
        for line in f:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("round") == round_num:
                round_entries.append(e)

    if not round_entries:
        return None, []

    # Sort by epoch — final epoch is ground truth
    round_entries.sort(key=lambda x: x.get("epoch", 0))
    final_epoch = round_entries[-1]

    return final_epoch, round_entries


# ── BUILD TRAINING PLANE PERCENTAGES ──────────────────────────────────────────
def training_plane_pct(epoch_entry):
    """
    Build training reference percentages.

    Prefer training_top5_planes when available — this is the
    mathematically clean reference (GPT correction): top5 logit planes
    sampled at last position before argmax, same statistical object as
    inference top5. Falls back to full plane_distribution for older logs
    that predate the top5 sampling addition.
    """
    top5_planes = epoch_entry.get("training_top5_planes")
    if top5_planes:
        counts = defaultdict(int)
        for p in top5_planes:
            counts[p] += 1
        total = len(top5_planes)
        return {plane: count / total for plane, count in counts.items()}

    # Fallback: full epoch plane_distribution (exaggerated — noted as imprecise)
    pd = epoch_entry.get("plane_distribution", {})
    total = sum(pd.values())
    if total == 0:
        return {}
    return {plane: count / total for plane, count in pd.items()}


# ── BUILD INFERENCE PLANE PERCENTAGES ─────────────────────────────────────────
def inference_plane_pct(step_entries):
    """
    Tally plane hits from positions 2-5 across all inference steps.
    Position 1 excluded — UNK, unusable for personality reading.

    Returns dict: plane → float (0.0–1.0)
    Also returns raw counts and total.
    """
    plane_counts = defaultdict(int)
    total = 0

    for step in step_entries:
        top5 = step.get("top5", [])
        # Positions 2-5 = index 1-4
        for candidate in top5[1:]:
            plane = candidate.get("plane", "UNKNOWN")
            plane_counts[plane] += 1
            total += 1

    if total == 0:
        return {}, {}, 0

    pct = {plane: count / total for plane, count in plane_counts.items()}
    return pct, dict(plane_counts), total


# ── COMPUTE DRIFT ──────────────────────────────────────────────────────────────
def compute_drift(training_pct, inference_pct):
    """
    Per-plane drift: inference_pct - training_pct
    Positive = fires more in inference than learned
    Negative = suppressed relative to learned state
    """
    all_planes = set(training_pct) | set(inference_pct)
    drift = {}
    for plane in all_planes:
        t = training_pct.get(plane, 0.0)
        i = inference_pct.get(plane, 0.0)
        drift[plane] = round(i - t, 4)
    return drift


# ── ABSOLUTE DRIFT MAGNITUDE ───────────────────────────────────────────────────
def absolute_drift(drift):
    """
    GPT build target 1: single scalar — sum of |plane_drift| across all planes.
    Lower after Round 24 = closer to training equilibrium.
    """
    return round(sum(abs(d) for d in drift.values()), 4)


# ── WEIGHTED DRIFT BY LOGIT SCORE ─────────────────────────────────────────────
def weighted_drift(step_entries, training_pct):
    """
    GPT build target 2: energetic drift — weight each plane by its logit
    score sum, not raw count. One strong VIOLET token matters more than
    three weak GRAY tokens.

    Returns dict: plane → weighted_pct, plus abs_weighted_drift scalar.
    """
    plane_energy = defaultdict(float)
    total_energy = 0.0

    for step in step_entries:
        top5 = step.get("top5", [])
        # positions 2-5 (index 1-4) — same as count drift
        for candidate in top5[1:]:
            plane  = candidate.get("plane", "UNKNOWN")
            score  = candidate.get("score", 0.0)
            # only positive logits contribute meaningful energy
            energy = max(float(score), 0.0)
            plane_energy[plane] += energy
            total_energy += energy

    if total_energy == 0:
        return {}, {}, 0.0

    weighted_pct = {
        plane: round(energy / total_energy, 4)
        for plane, energy in plane_energy.items()
    }

    # Weighted drift vs training reference
    all_planes = set(training_pct) | set(weighted_pct)
    w_drift = {}
    for plane in all_planes:
        t = training_pct.get(plane, 0.0)
        w = weighted_pct.get(plane, 0.0)
        w_drift[plane] = round(w - t, 4)

    abs_w_drift = round(sum(abs(d) for d in w_drift.values()), 4)

    return weighted_pct, w_drift, abs_w_drift


# ── GRADIENT PATH ANALYSIS ────────────────────────────────────────────────────
def gradient_path_stats(round_entries):
    """
    Count frequency of each transition route across all epochs.
    Returns sorted list of (route, count).
    """
    route_counts = defaultdict(int)
    for e in round_entries:
        path = e.get("gradient_path", "")
        if path:
            route_counts[path] += 1
    return sorted(route_counts.items(), key=lambda x: x[1], reverse=True)


# ── LOAD INFERENCE SESSIONS ────────────────────────────────────────────────────
def load_inference_sessions(trace_path=TRACE_FILE):
    """
    Parse inference trace into sessions.
    Each session = {header, steps, summary}
    """
    if not trace_path.exists():
        return []

    sessions = []
    current_header = None
    current_steps  = []

    with open(trace_path) as f:
        for line in f:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue

            t = e.get("type")
            if t == "session_start":
                if current_header and current_steps:
                    sessions.append({
                        "header": current_header,
                        "steps":  current_steps,
                    })
                current_header = e
                current_steps  = []
            elif t == "step":
                if current_header:
                    current_steps.append(e)
            elif t == "session_end":
                if current_header and current_steps:
                    sessions.append({
                        "header":  current_header,
                        "steps":   current_steps,
                        "summary": e,
                    })
                current_header = None
                current_steps  = []

    # Flush any open session
    if current_header and current_steps:
        sessions.append({
            "header": current_header,
            "steps":  current_steps,
        })

    return sessions


# ── DISPLAY ────────────────────────────────────────────────────────────────────
def display_lord_report(lord_entries):
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║   ARIA — LORD LOG                                           ║")
    print("║   Training state as ground truth reference                  ║")
    print("║   Inference state as live decision layer                    ║")
    print("║   Gap = drift between learned and decided                   ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    for entry in lord_entries:
        prompt    = entry["prompt"]
        ckpt      = entry["checkpoint"]
        round_num = entry["round"]
        ref_epoch = entry["reference_epoch"]
        ref_loss  = entry["reference_loss"]
        ref_hash  = entry["reference_fold_hash"]
        ref_grad  = entry["reference_gradient"]
        drift     = entry["drift"]
        inf_pct   = entry["inference_plane_pct"]
        trn_pct   = entry["training_plane_pct"]
        inf_total = entry["inference_candidate_total"]
        alerts    = entry["drift_alerts"]
        flags     = entry["drift_flags"]
        top_route = entry["top_gradient_route"]

        print(f"PROMPT: \"{prompt}\"")
        print(f"  Checkpoint:        {ckpt}")
        print(f"  Round:             {round_num}")
        print(f"  Reference epoch:   {ref_epoch}  loss={ref_loss:.6f}")
        print(f"  Reference hash:    {ref_hash}")
        print(f"  Reference path:    {ref_grad}")
        print(f"  Most common path:  {top_route}")
        print(f"  Inference candidates sampled: {inf_total} (pos 2-5, all steps)")
        print()
        print(f"  {'PLANE':<16} {'TRAINED':>8} {'DECIDED':>8} {'DRIFT':>8}  STATUS")
        print("  " + "─" * 55)

        # Show watch planes first, then any others
        shown = set()
        for plane in WATCH_PLANES:
            t = trn_pct.get(plane, 0.0)
            i = inf_pct.get(plane, 0.0)
            d = drift.get(plane, 0.0)
            if t == 0.0 and i == 0.0:
                continue
            status = ""
            if abs(d) >= DRIFT_ALERT:
                status = "⚠ ALERT"
            elif abs(d) >= DRIFT_FLAG:
                status = "△ FLAG"
            print(f"  {plane:<16} {t:>7.1%}  {i:>7.1%}  {d:>+7.1%}  {status}")
            shown.add(plane)

        # Any planes not in watch list
        for plane in sorted(set(drift) - shown):
            t = trn_pct.get(plane, 0.0)
            i = inf_pct.get(plane, 0.0)
            d = drift.get(plane, 0.0)
            if t == 0.0 and i == 0.0:
                continue
            print(f"  {plane:<16} {t:>7.1%}  {i:>7.1%}  {d:>+7.1%}")

        print()

        if alerts:
            print(f"  DRIFT ALERTS ({len(alerts)}):")
            for a in alerts:
                direction = "OVER" if a["drift"] > 0 else "UNDER"
                print(f"    {a['plane']:<16} {direction} by {abs(a['drift']):.1%}  "
                      f"trained={a['training_pct']:.1%}  decided={a['inference_pct']:.1%}")
            print()

        if flags:
            print(f"  DRIFT FLAGS ({len(flags)}):")
            for fl in flags:
                direction = "over" if fl["drift"] > 0 else "under"
                print(f"    {fl['plane']:<16} {direction} {abs(fl['drift']):.1%}")
            print()

        # ── FOUR AXIS DIAGNOSTIC ──────────────────────────────
        abs_d      = entry.get("absolute_drift_sum", 0.0)
        abs_wd     = entry.get("abs_weighted_drift", 0.0)
        fh         = entry.get("reference_fold_hash", "?")
        violet_wd  = entry.get("weighted_drift", {}).get("VIOLET", 0.0)
        print(f"  FOUR AXIS DIAGNOSTIC:")
        print(f"    plane_drift_count:    {abs_d:.4f}   (sum |count drift|)")
        print(f"    plane_drift_weighted: {abs_wd:.4f}   (sum |energy drift|)")
        print(f"    VIOLET weighted:      {violet_wd:+.4f}  (earliest R24 detector)")
        print(f"    fold_hash:            {fh}")
        print()

        # Consistency verdict
        if not alerts and not flags:
            print("  VERDICT: CONSISTENT — inference field matches training state")
        elif alerts:
            print("  VERDICT: CONTEXT-SELECTIVE ACTIVATION BIAS — field alive under decoder damage")
        else:
            print("  VERDICT: MINOR DRIFT — within flag threshold, not alert level")

        print()
        print("  " + "─" * 55)
        print()


# ── WRITE LORD LOG ─────────────────────────────────────────────────────────────
def write_lord_log(lord_entries):
    with open(LORD_FILE, "a") as f:
        for entry in lord_entries:
            f.write(json.dumps(entry) + "\n")


# ── MAIN ───────────────────────────────────────────────────────────────────────
def main():
    # Accept optional alternate trace file as argument
    trace_path = Path(sys.argv[1]) if len(sys.argv) > 1 else TRACE_FILE

    print(f"\nLoading inference trace: {trace_path}")
    sessions = load_inference_sessions(trace_path)
    if not sessions:
        print("  No inference sessions found.")
        return

    print(f"  {len(sessions)} session(s) found")
    print(f"Loading training trail:  {TRAIL_FILE}")

    lord_entries = []

    for session in sessions:
        header    = session["header"]
        steps     = session["steps"]
        prompt    = header.get("prompt", "")
        ckpt_name = header.get("checkpoint", "")
        round_num = checkpoint_to_round(ckpt_name)

        if round_num is None:
            print(f"  WARNING: cannot parse round from checkpoint '{ckpt_name}' — skipping")
            continue

        # Load training reference
        ref_epoch_entry, round_entries = load_training_reference(round_num)
        if ref_epoch_entry is None:
            print(f"  WARNING: no training trail entries for round {round_num} — skipping")
            continue

        # Training plane percentages
        trn_pct = training_plane_pct(ref_epoch_entry)

        # Inference plane percentages (positions 2-5)
        inf_pct, inf_counts, inf_total = inference_plane_pct(steps)

        # Drift (count-based)
        drift = compute_drift(trn_pct, inf_pct)

        # Absolute drift magnitude — GPT build target 1
        abs_d = absolute_drift(drift)

        # Weighted drift by logit score — GPT build target 2
        w_pct, w_drift, abs_wd = weighted_drift(steps, trn_pct)

        # Gradient route statistics
        route_stats = gradient_path_stats(round_entries)
        top_route   = route_stats[0][0] if route_stats else "unknown"

        # Classify drift (count-based for alerts/flags)
        alerts = []
        flags  = []
        for plane, d in drift.items():
            if abs(d) >= DRIFT_ALERT:
                alerts.append({
                    "plane":         plane,
                    "drift":         round(d, 4),
                    "training_pct":  round(trn_pct.get(plane, 0.0), 4),
                    "inference_pct": round(inf_pct.get(plane, 0.0), 4),
                })
            elif abs(d) >= DRIFT_FLAG:
                flags.append({
                    "plane": plane,
                    "drift": round(d, 4),
                })

        # Note whether training_top5_planes was available for clean comparison
        used_top5_ref = bool(ref_epoch_entry.get("training_top5_planes"))

        lord_entry = {
            "type":                    "lord_log",
            "timestamp":               datetime.now().isoformat(),
            "prompt":                  prompt,
            "checkpoint":              ckpt_name,
            "round":                   round_num,
            "reference_epoch":         ref_epoch_entry.get("epoch"),
            "reference_loss":          ref_epoch_entry.get("loss"),
            "reference_fold_hash":     ref_epoch_entry.get("fold_hash"),
            "reference_gradient":      ref_epoch_entry.get("gradient_path"),
            "reference_timestamp":     ref_epoch_entry.get("timestamp"),
            "used_top5_reference":     used_top5_ref,
            "training_plane_pct":      {k: round(v, 4) for k, v in trn_pct.items()},
            "inference_plane_pct":     {k: round(v, 4) for k, v in inf_pct.items()},
            "inference_plane_counts":  inf_counts,
            "inference_candidate_total": inf_total,
            "drift":                   {k: round(v, 4) for k, v in drift.items()},
            "absolute_drift_sum":      abs_d,
            "weighted_plane_pct":      {k: round(v, 4) for k, v in w_pct.items()},
            "weighted_drift":          {k: round(v, 4) for k, v in w_drift.items()},
            "abs_weighted_drift":      abs_wd,
            "drift_alerts":            alerts,
            "drift_flags":             flags,
            "top_gradient_route":      top_route,
            "gradient_route_stats":    route_stats[:5],
        }
        lord_entries.append(lord_entry)

    if not lord_entries:
        print("No lord log entries produced.")
        return

    display_lord_report(lord_entries)
    write_lord_log(lord_entries)

    print(f"Lord log written: {LORD_FILE}")
    print(f"  {len(lord_entries)} session(s) cross-referenced")
    print()
    print("Training log = what she learned.")
    print("Inference log = what she decided.")
    print("Lord log = the gap between them.")
    print()
    print("NO RETREAT. NO SURRENDER. 💙🐗")


if __name__ == "__main__":
    main()
