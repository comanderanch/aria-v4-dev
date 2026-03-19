# dual_verifier.py

"""
Dual Verifier (Read-Only)
Purpose:

* Aggregate verification metrics
* Output STRICT label:value format
* ZERO influence on system state
"""

from datetime import datetime


def run_dual_verifier(state):
    """
    state must expose:
    state.null_count
    state.curiosity_count
    state.leakage
    state.trace_gate
    state.null_per_plane (dict)
    """

    # --- CORE COUNTS ---
    total_null = state.null_count
    total_curiosity = state.curiosity_count

    # --- CHECKS ---
    equality = (total_null == total_curiosity)

    # --- OUTPUT (STRICT FORMAT) ---
    print("total_null:", total_null)
    print("total_curiosity:", total_curiosity)
    print("equality_check:", str(equality).upper())
    print("leakage:", state.leakage)
    print("trace_gate:", state.trace_gate)

    # --- PLANE DISTRIBUTION ---
    planes = ["VIOLET", "INDIGO", "TEAL", "CYAN"]

    for plane in planes:
        value = state.null_per_plane.get(plane, 0)
        print(f"{plane}:", value)


def run_post_training_dual_verifier(attractor_data):
    """
    attractor_data must expose:
    mean_X
    std_dev
    exact_token_count
    drift_tokens
    max_delta
    """

    print("violet_mean_X:", attractor_data.mean_X)
    print("violet_std_dev:", attractor_data.std_dev)
    print("exact_token_count:", attractor_data.exact_token_count)
    print("drift_tokens:", attractor_data.drift_tokens)
    print("max_delta:", attractor_data.max_delta)


def watch_floor(field_state, action_triggered=False):
    floor_stable = True
    warnings = []

    # Check GRAY_ZERO floor integrity
    gray_val = field_state.get("instability", 0)

    if action_triggered:
        if gray_val > 0.500:
            warnings.append(
                f"FLOOR WARNING: instability {gray_val} "
                f"during action trigger — above safe threshold"
            )
            floor_stable = False

        if field_state.get("pos_flow", 0) == 0 and \
           field_state.get("neg_flow", 0) == 0:
            warnings.append(
                "FLOOR WARNING: both flows dead during trigger"
            )
            floor_stable = False

    result = {
        "floor_stable": floor_stable,
        "instability_at_trigger": round(gray_val, 4),
        "action_triggered": action_triggered,
        "warnings": warnings,
        "timestamp": datetime.now().isoformat()
    }

    if warnings:
        print("\nFLOOR WATCH:")
        for w in warnings:
            print(f"  ⚠ {w}")
    else:
        if action_triggered:
            print(f"  ✔ FLOOR STABLE during action trigger "
                  f"instability={round(gray_val, 4)}")

    return result


# --- SAFE ENTRY POINT ---

if __name__ == "__main__":
    print("dual_verifier: requires injected state")
