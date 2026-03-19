# second_verifier.py

"""
Second Verifier (Read-Only)
Purpose:

* Aggregate verification metrics
* Output STRICT label:value format
* ZERO influence on system state
"""


def run_second_verifier(state):
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


def run_post_training_verifier(attractor_data):
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


# --- SAFE ENTRY POINT ---

if __name__ == "__main__":
    print("second_verifier: requires injected state")
