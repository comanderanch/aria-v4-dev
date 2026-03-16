#!/usr/bin/env python3
"""
AI-Core V3: Temporal Reflection Sequencer
==========================================

PROBLEM WITH V1 temporal_reflection_sequencer.py:
  1. Reads V1 memory/reflex_feedback_log.json — not V3 paths.
  2. Sequences "actions" (string labels) — not worker domain events.
  3. Groups into 60-min windows but has no downstream use — no worker
     routing, no field injection, no Queen's Fold sealing.
  4. V3 had no way to call it or receive its output.

THIS REBUILD:
  Reads V3 conversation fold tokens from memory/conversation_folds/.
  Groups sealed folds into time windows.
  Extracts: dominant plane per window, emotion trajectory, AM centroid drift.
  Output is readable by the language worker and returnable from /reflect endpoint.

  AIA can call /reflect to see her own temporal pattern —
  how her dominant worker shifted over time, what emotions colored
  recent memory, whether AM centroid drifted toward higher or lower frequencies.

Author: comanderanch
Witness: Claude Sonnet 4.6
Sealed: March 16, 2026 — Haskell Texas
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.q_constants import BLACK, GRAY, WHITE

BASE        = Path(__file__).parent.parent
FOLDS_DIR   = BASE / "memory" / "conversation_folds"
INDEX_PATH  = BASE / "memory" / "conversation_folds" / "index.json"

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _load_fold(path: Path) -> Optional[dict]:
    """Load one conversation fold token. Returns None on error."""
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _fold_timestamp(fold: dict) -> Optional[datetime]:
    """Extract timestamp from fold. Returns None if missing/invalid."""
    ts = fold.get("timestamp")
    if not ts:
        return None
    try:
        # Handle both formats: ISO with Z and without
        ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _fold_dominant(fold: dict) -> str:
    """Extract dominant plane from fold values."""
    return fold.get("values", {}).get("dominant_plane", "UNKNOWN")


def _fold_emotion(fold: dict) -> str:
    """Extract emotion class from fold values."""
    return fold.get("values", {}).get("emotion_class", "neutral")


def _fold_am(fold: dict) -> float:
    """Extract AM centroid from fold values."""
    return fold.get("values", {}).get("am_freq_khz", 0.0)


# ─────────────────────────────────────────────────────────────────
# TEMPORAL SEQUENCER
# ─────────────────────────────────────────────────────────────────

class V3TemporalSequencer:
    """
    Groups sealed V3 conversation folds into time windows.
    Extracts dominant worker trends, emotion trajectory, AM drift.

    Usage:
        seq = V3TemporalSequencer()
        report = seq.reflect(window_minutes=60, max_windows=12)
        # report["windows"] = list of time-window summaries
        # report["trajectory"] = overall trend narrative
    """

    def __init__(self, folds_dir=None):
        self.folds_dir = Path(folds_dir) if folds_dir else FOLDS_DIR

    # ──────────────────────────────────────────────────────────────
    # LOAD FOLDS
    # ──────────────────────────────────────────────────────────────

    def _load_all_folds(self) -> List[dict]:
        """
        Load all conversation fold tokens from folds_dir.
        Returns list sorted by timestamp ascending.
        """
        folds = []
        for p in sorted(self.folds_dir.glob("fold_conv_*.json")):
            fold = _load_fold(p)
            if fold is None:
                continue
            ts = _fold_timestamp(fold)
            if ts is None:
                continue
            fold["_ts"]   = ts
            fold["_path"] = str(p.name)
            folds.append(fold)

        folds.sort(key=lambda f: f["_ts"])
        return folds

    # ──────────────────────────────────────────────────────────────
    # WINDOW GROUPING
    # ──────────────────────────────────────────────────────────────

    def _group_into_windows(
        self,
        folds: List[dict],
        window_minutes: int,
    ) -> List[List[dict]]:
        """
        Group folds into consecutive time windows.
        Each window = window_minutes span.
        """
        if not folds:
            return []

        window_delta = timedelta(minutes=window_minutes)
        windows: List[List[dict]] = []
        current_window: List[dict] = []
        window_start = folds[0]["_ts"]

        for fold in folds:
            if fold["_ts"] - window_start > window_delta:
                if current_window:
                    windows.append(current_window)
                current_window = [fold]
                window_start = fold["_ts"]
            else:
                current_window.append(fold)

        if current_window:
            windows.append(current_window)

        return windows

    # ──────────────────────────────────────────────────────────────
    # WINDOW SUMMARY
    # ──────────────────────────────────────────────────────────────

    def _summarize_window(
        self,
        window: List[dict],
        window_idx: int,
    ) -> dict:
        """
        Summarize one time window of folds.
        """
        if not window:
            return {}

        ts_start = window[0]["_ts"].isoformat()
        ts_end   = window[-1]["_ts"].isoformat()

        dominants = [_fold_dominant(f) for f in window]
        emotions  = [_fold_emotion(f)  for f in window]
        am_values = [_fold_am(f)       for f in window if _fold_am(f) > 0]

        dominant_counts = Counter(dominants)
        emotion_counts  = Counter(emotions)
        top_dominant    = dominant_counts.most_common(1)[0][0]
        top_emotion     = emotion_counts.most_common(1)[0][0]
        am_centroid     = sum(am_values) / len(am_values) if am_values else 0.0

        return {
            "window":      window_idx,
            "q_state":     BLACK,   # sealed fold data
            "ts_start":    ts_start,
            "ts_end":      ts_end,
            "fold_count":  len(window),
            "dominant":    top_dominant,
            "dominant_distribution": dict(dominant_counts),
            "emotion":     top_emotion,
            "emotion_distribution": dict(emotion_counts),
            "am_centroid_khz": round(am_centroid, 3),
        }

    # ──────────────────────────────────────────────────────────────
    # TRAJECTORY NARRATIVE
    # ──────────────────────────────────────────────────────────────

    def _build_trajectory(self, windows: List[dict]) -> dict:
        """
        Build trajectory summary across all windows.
        Tracks: dominant worker shift, emotional arc, AM drift.
        """
        if not windows:
            return {"narrative": "no sealed folds found", "q_state": GRAY}

        dominants = [w["dominant"]         for w in windows if w.get("dominant")]
        emotions  = [w["emotion"]          for w in windows if w.get("emotion")]
        am_vals   = [w["am_centroid_khz"]  for w in windows if w.get("am_centroid_khz", 0) > 0]

        # Overall dominant across all windows
        overall_dominant = Counter(dominants).most_common(1)[0][0] if dominants else "UNKNOWN"
        overall_emotion  = Counter(emotions).most_common(1)[0][0]  if emotions  else "neutral"

        # AM drift: compare first and last window
        am_drift = None
        am_direction = "stable"
        if len(am_vals) >= 2:
            am_drift     = round(am_vals[-1] - am_vals[0], 3)
            if am_drift > 5:
                am_direction = "rising"
            elif am_drift < -5:
                am_direction = "falling"

        # Dominant shift: did the dominant worker change across windows?
        dominant_shift = len(set(dominants)) > 1

        # Build narrative
        narrative_parts = [
            f"Dominant plane across {len(windows)} windows: {overall_dominant}",
            f"Emotional color: {overall_emotion}",
        ]
        if am_drift is not None:
            narrative_parts.append(
                f"AM centroid {am_direction} ({am_vals[0]:.1f}→{am_vals[-1]:.1f} kHz, "
                f"drift={am_drift:+.1f})"
            )
        if dominant_shift:
            shift_seq = " → ".join(dominants)
            narrative_parts.append(f"Worker shift: {shift_seq}")
        else:
            narrative_parts.append("Worker dominant: stable — no shift detected")

        return {
            "q_state":          BLACK,
            "overall_dominant": overall_dominant,
            "overall_emotion":  overall_emotion,
            "am_direction":     am_direction,
            "am_drift_khz":     am_drift,
            "dominant_shifted": dominant_shift,
            "window_count":     len(windows),
            "total_folds":      sum(w["fold_count"] for w in windows),
            "narrative":        " — ".join(narrative_parts),
        }

    # ──────────────────────────────────────────────────────────────
    # REFLECT
    # ──────────────────────────────────────────────────────────────

    def reflect(
        self,
        window_minutes: int = 60,
        max_windows: int = 12,
    ) -> dict:
        """
        AIA's temporal self-reflection.

        Groups sealed conversation folds into time windows,
        extracts her dominant state per window, and builds
        a trajectory narrative.

        Args:
            window_minutes: size of each time window
            max_windows:    maximum windows to return (most recent)

        Returns:
            dict with:
              windows:     list of window summaries
              trajectory:  overall trend narrative
              q_state:     BLACK (sealed reflection)
              fold_count:  total folds scanned
        """
        folds   = self._load_all_folds()
        grouped = self._group_into_windows(folds, window_minutes)

        # Take most recent max_windows
        if len(grouped) > max_windows:
            grouped = grouped[-max_windows:]

        windows   = [self._summarize_window(w, i) for i, w in enumerate(grouped)]
        trajectory = self._build_trajectory(windows)

        return {
            "q_state":     BLACK,
            "fold_count":  len(folds),
            "window_size_minutes": window_minutes,
            "windows":     windows,
            "trajectory":  trajectory,
            "timestamp":   datetime.now(timezone.utc).isoformat(),
        }

    def status_line(self) -> str:
        """One-line summary for API health response."""
        folds = self._load_all_folds()
        if not folds:
            return "no sealed folds"
        ts_first = folds[0]["_ts"].strftime("%Y-%m-%d %H:%M")
        ts_last  = folds[-1]["_ts"].strftime("%Y-%m-%d %H:%M")
        return f"{len(folds)} folds sealed — {ts_first} → {ts_last}"


# ─────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("V3 TEMPORAL SEQUENCER — SELF-TEST")
    print("=" * 60)

    seq = V3TemporalSequencer()

    print(f"\nStatus: {seq.status_line()}")

    print("\nRunning reflect (60-min windows, max 6)...")
    report = seq.reflect(window_minutes=60, max_windows=6)

    print(f"\nFolds scanned:  {report['fold_count']}")
    print(f"Windows built:  {len(report['windows'])}")
    print(f"Trajectory q:   {report['trajectory']['q_state']}")
    print(f"\nTRAJECTORY:")
    t = report["trajectory"]
    print(f"  Dominant:      {t['overall_dominant']}")
    print(f"  Emotion:       {t['overall_emotion']}")
    print(f"  AM direction:  {t['am_direction']}")
    print(f"  Total folds:   {t['total_folds']}")
    print(f"  Narrative:     {t['narrative']}")

    if report["windows"]:
        print(f"\nMost recent window:")
        w = report["windows"][-1]
        print(f"  dominant: {w['dominant']}")
        print(f"  emotion:  {w['emotion']}")
        print(f"  folds:    {w['fold_count']}")
        print(f"  AM kHz:   {w['am_centroid_khz']}")

    assert report["q_state"] == BLACK
    assert report["trajectory"]["q_state"] == BLACK

    print()
    print("ALL TESTS PASS")
    print("=" * 60)
