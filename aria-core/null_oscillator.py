import math, hashlib, json, time
from datetime import datetime
from curiosity import curiosity_trigger, curiosity_summary
from dual_verifier import watch_floor

NULL_TRAIL  = "/tmp/aria-null-trail.jsonl"
TOKEN_TRAIL = "/tmp/aria-token-trail.jsonl"

PLANE_ATTRACTORS = {
    "VIOLET": 0.192, "GRAY_ZERO": 0.000,
    "CYAN": 0.500, "TEAL": 0.530,
    "BLUE": 0.350, "INDIGO": 0.250,
    "YELLOW": 0.620, "RED_ORANGE": 0.900,
    "BLACK_VOID": -0.800
}

INSTABILITY_THRESHOLD = 0.15
SIMILARITY_EPSILON = 0.05
WINDOW_DURATION = 5.0
LAST_N = 20

recent_tokens = []
unresolved_pool = set()
recent_shadows = []

def oscillate(plane, frequency):
    pos_flow = frequency * 1.0
    # Half cycle offset prevents coupling
    neg_flow = frequency * -1.0
    neg_offset = 0.5  # phase offset seconds

    field_state = {
        "plane": plane,
        "frequency": frequency,
        "pos_flow": pos_flow,
        "neg_flow": neg_flow,
        "neg_phase_offset": neg_offset,
        "coupling_isolated": True,
        "instability": round(abs(pos_flow - neg_flow), 4),
        "timestamp": datetime.now().isoformat()
    }
    return field_state

def detect_instability(field_state):
    score = field_state["instability"]
    window_open = score > INSTABILITY_THRESHOLD
    return round(score, 4), window_open

def generate_variance(field_state):
    seed = field_state["instability"] * field_state["frequency"]
    h = hashlib.sha256(
        f"{seed}{time.time()}".encode()
    ).hexdigest()
    variance_value = int(h[:8], 16) / 0xFFFFFFFF
    candidate = round(
        field_state["frequency"] +
        (variance_value - 0.5) * field_state["instability"],
        6
    )
    return candidate

def trace(candidate, field_state):
    for anchor_name, anchor_val in PLANE_ATTRACTORS.items():
        if abs(candidate - anchor_val) < SIMILARITY_EPSILON:
            return f"token_map:{anchor_name}"

    if abs(candidate - field_state["frequency"]) < SIMILARITY_EPSILON:
        return "emotion_projection"

    for token in recent_tokens[-LAST_N:]:
        if abs(candidate - token) < SIMILARITY_EPSILON:
            return "recent_token"

    if candidate in unresolved_pool:
        return "unresolved_pool"

    if abs(candidate - field_state["pos_flow"]) < SIMILARITY_EPSILON:
        return "field_pos"
    if abs(candidate - field_state["neg_flow"]) < SIMILARITY_EPSILON:
        return "field_neg"

    shadow = hashlib.sha256(
        f"{round(candidate, 6)}".encode()
    ).hexdigest()[:8]
    if shadow in recent_shadows:
        return "shadow_guard"

    return None

def attempt_generation(window_state, field_state):
    if not window_state:
        return None, None

    candidate = generate_variance(field_state)

    if candidate is None:
        return None, None

    trace_result = trace(candidate, field_state)

    if trace_result is not None:
        return None, trace_result

    shadow = hashlib.sha256(
        f"{round(candidate, 6)}".encode()
    ).hexdigest()[:8]
    recent_shadows.append(shadow)
    if len(recent_shadows) > LAST_N:
        recent_shadows.pop(0)

    return candidate, None

def _log_to_null_trail(record):
    """Write event record to NULL_TRAIL only. TOKEN_TRAIL is protected."""
    with open(NULL_TRAIL, "a") as f:
        f.write(json.dumps(record) + "\n")


def run_idle_oscillation(plane, frequency, cycles=5):
    results = []

    print(f"NULL OSCILLATOR — {plane} @ {frequency}")
    print(f"Threshold: {INSTABILITY_THRESHOLD}")
    print(f"Epsilon:   {SIMILARITY_EPSILON}")
    print()

    for i in range(cycles):
        field_state = oscillate(plane, frequency)
        instability, window_open = detect_instability(field_state)
        candidate, rejection_reason = attempt_generation(
            window_open, field_state
        )

        condition_data = {
            "timestamp": field_state["timestamp"],
            "plane": plane,
            "frequency": frequency,
            "instability_score": instability,
            "window_open": window_open
        }
        condition_hash = hashlib.sha256(
            json.dumps(condition_data,
            sort_keys=True).encode()
        ).hexdigest()[:7]

        null_confirmed = candidate is not None

        # Floor watch — hard gate during action trigger
        floor_check = None
        if null_confirmed:
            floor_check = watch_floor(
                field_state=field_state,
                action_triggered=True
            )
            if not floor_check["floor_stable"]:
                null_confirmed = False
                rejection_reason = "floor_unstable"

        if null_confirmed:
            condition_data = {
                "timestamp": field_state["timestamp"],
                "plane": plane,
                "frequency": frequency,
                "instability_score": instability,
                "window_open": window_open
            }
            curiosity_record = curiosity_trigger(
                condition_data, condition_hash
            )

        result = {
            "cycle": i + 1,
            "timestamp": field_state["timestamp"],
            "instability_score": instability,
            "window_open": window_open,
            "null_confirmed": null_confirmed,
            "rejection_reason": rejection_reason,
            "condition_hash": condition_hash,
            "curiosity_state": "unresolved" if null_confirmed else None,
            "curiosity_fold_hash": condition_hash if null_confirmed else None
        }

        results.append(result)
        _log_to_null_trail(result)

        if null_confirmed:
            status = "● NULL CONFIRMED — floor stable ✔"
        elif rejection_reason == "floor_unstable":
            status = "⚠ NULL REJECTED — floor unstable"
        else:
            status = f"○ rejected ({rejection_reason})"

        print(
            f"Cycle {i+1}: "
            f"instability={instability} "
            f"window={window_open} "
            f"{status}"
        )
        if null_confirmed:
            print(f"         curiosity_state: unresolved")
            print(f"         condition_hash: {condition_hash}")

        time.sleep(0.5)

    null_count = sum(1 for r in results if r["null_confirmed"])
    print()
    print(f"Null candidates confirmed: {null_count}/{len(results)}")
    print(f"Repeatability: {'PASS' if null_count > 1 else 'NEED MORE CYCLES'}")

    summary = curiosity_summary()
    print(f"Curiosity events: {summary['total_curiosity_events']}")
    print(f"All unresolved: {summary['unresolved'] == null_count}")

    return results

if __name__ == "__main__":
    print("=" * 50)
    print("NULL OSCILLATOR — AUTONOMY CANDIDATE TEST")
    print("March 19 2026 — Haskell Texas")
    print("Commander Anthony Hagerty")
    print("=" * 50)
    print()

    results = run_idle_oscillation(
        plane="VIOLET",
        frequency=0.192,
        cycles=10
    )

    null_events = [r for r in results if r["null_confirmed"]]
    if null_events:
        print()
        print("NULL EVENTS — CURIOSITY TRIGGERED:")
        for e in null_events:
            print(f"  [{e['condition_hash']}] curiosity_state={e['curiosity_state']}")
