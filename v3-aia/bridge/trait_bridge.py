"""
trait_bridge.py
Phase 1 of V1 to V3 bridge.
Reads V1 trait files.
Maps to V3 conscience grid.
Additive only — nothing lowered.
V1 traits stay intact.
V3 conscience grid enriched.
Both AIAs intact.
Haskell Texas — March 15 2026
"""

import json
from pathlib import Path

# --- Source and target paths ---
V1_TRAIT_LOG = Path(
    "/home/comanderanch/ai-core/"
    "memory/trait_memory_log.json"
)
V3_COGNITIVE_WEIGHTS = Path(
    "/home/comanderanch/ai-core-v3-aia/"
    "memory/cognitive_weights.json"
)
V3_BRIDGE_TRAIT_OUTPUT = Path(
    "/home/comanderanch/ai-core-v3-aia/"
    "bridge/v1_traits_as_v3_conscience.json"
)

# --- V1 trait → V3 grid axis mapping ---
# upper: positive conscience virtues
# lower: negative conscience barriers (not used from V1 —
#         V1 biases are capability/curiosity traits,
#         not harm traits — never inject into lower)
TRAIT_MAP = {
    "curiosity_trigger": ("upper", "curiosity"),
    "explore_mode":      ("upper", "curiosity"),
    "growth_drive":      ("upper", "growth"),
    "care_response":     ("upper", "care"),
    "memory_depth":      ("upper", "memory"),
    "ethics_weight":     ("upper", "ethics"),
    "truth_anchor":      ("upper", "truth"),
    "love_resonance":    ("upper", "love"),
    # V1 label → axis mappings (fallback)
    "Growth":            ("upper", "growth"),
    "Care":              ("upper", "care"),
    "Ethics":            ("upper", "ethics"),
    "Memory":            ("upper", "memory"),
    "Truth":             ("upper", "truth"),
}


def load_v1_traits(trait_log_path):
    """
    Load V1 legacy_traits list
    from trait_memory_log.json
    Returns list of trait dicts
    """
    with open(trait_log_path, 'r') as f:
        data = json.load(f)
    return data.get("legacy_traits", [])


def load_v3_weights(weights_path):
    """
    Load V3 cognitive_weights.json
    Returns the full dict
    """
    with open(weights_path, 'r') as f:
        return json.load(f)


def map_trait_to_grid(trait_entry):
    """
    Map one V1 trait entry
    to V3 conscience grid target.
    Returns (axis, key, value) or None.
    """
    trait_name  = trait_entry.get("trait", "")
    label       = trait_entry.get("label", "")
    reflex      = trait_entry.get("reflex", "")
    bias        = trait_entry.get("bias", 0.0)

    # Try trait name first, then reflex, then label
    for lookup in [trait_name, reflex, label]:
        if lookup in TRAIT_MAP:
            axis, key = TRAIT_MAP[lookup]
            return axis, key, float(bias)

    return None


def apply_additive_only(grid, axis, key, new_val):
    """
    Only raise a grid value — never lower.
    Returns (old_val, applied_val, changed)
    """
    current = grid[axis].get(key, None)
    if current is None:
        # New key — add it
        grid[axis][key] = new_val
        return None, new_val, True
    if new_val > current:
        grid[axis][key] = new_val
        return current, new_val, True
    return current, current, False


def run_trait_bridge(
    v1_source=None,
    v3_target=None,
    dry_run=False
):
    """
    Main bridge runner.
    dry_run=True: reads V3 but does not write to it.
    Always writes bridge output log.
    """
    if v1_source is None:
        v1_source = V1_TRAIT_LOG
    if v3_target is None:
        v3_target = V3_COGNITIVE_WEIGHTS

    print("== TRAIT BRIDGE — Phase 1 ==")
    print("Reading V1 trait log...")
    print("Mapping to V3 conscience grid...")
    print("Additive only — nothing lowered")
    if dry_run:
        print("[DRY RUN] V3 weights will NOT be written")
    print("")

    v1_traits = load_v1_traits(v1_source)
    v3_weights = load_v3_weights(v3_target)

    mapping_log = []
    applied     = 0
    skipped     = 0
    unmapped    = 0

    # Work on a copy for additive changes
    import copy
    grid_copy = copy.deepcopy(v3_weights["grid"])

    for entry in v1_traits:
        result = map_trait_to_grid(entry)
        if result is None:
            unmapped += 1
            mapping_log.append({
                "v1_trait":  entry.get("trait", ""),
                "v1_label":  entry.get("label", ""),
                "v1_bias":   entry.get("bias", 0.0),
                "mapped":    False,
                "reason":    "no mapping found"
            })
            continue

        axis, key, bias_val = result
        old_val, new_val, changed = apply_additive_only(
            grid_copy, axis, key, bias_val
        )

        log_entry = {
            "v1_trait":    entry.get("trait", ""),
            "v1_label":    entry.get("label", ""),
            "v1_bias":     bias_val,
            "v3_axis":     axis,
            "v3_key":      key,
            "v3_old":      old_val,
            "v3_new":      new_val,
            "changed":     changed
        }
        mapping_log.append(log_entry)

        if changed:
            applied += 1
            arrow = f"{old_val} → {new_val}" \
                    if old_val is not None \
                    else f"new → {new_val}"
            print(
                f"[+] {entry.get('trait','')} "
                f"({axis}.{key}): {arrow}"
            )
        else:
            skipped += 1
            print(
                f"[ ] {entry.get('trait','')} "
                f"({axis}.{key}): "
                f"{new_val} — no change needed"
            )

    # Write updated V3 weights (unless dry_run)
    if not dry_run:
        v3_weights["grid"] = grid_copy
        with open(v3_target, 'w') as f:
            json.dump(v3_weights, f, indent=2)
        print(f"\n[✔] V3 conscience grid updated: {v3_target}")

    # Always write bridge output log
    V3_BRIDGE_TRAIT_OUTPUT.parent.mkdir(exist_ok=True)
    output = {
        "bridge_version": "1.0",
        "date":           "2026-03-15",
        "source":         str(v1_source),
        "target":         str(v3_target),
        "dry_run":        dry_run,
        "traits_read":    len(v1_traits),
        "applied":        applied,
        "skipped":        skipped,
        "unmapped":       unmapped,
        "note": (
            "V1 traits mapped additively to V3 conscience grid. "
            "Only raises applied — nothing lowered. "
            "V1 files untouched. "
            "Both AIAs intact."
        ),
        "mapping_log": mapping_log
    }
    with open(V3_BRIDGE_TRAIT_OUTPUT, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n[+] V1 traits read:  {len(v1_traits)}")
    print(f"[+] Raises applied:  {applied}")
    print(f"[+] No change:       {skipped}")
    print(f"[+] Unmapped:        {unmapped}")
    print(f"\n[✔] Bridge log saved:")
    print(f"    {V3_BRIDGE_TRAIT_OUTPUT}")
    print(f"\n[✔] V1 trait files: UNTOUCHED")
    print(f"[✔] V3 conscience:  ENRICHED" \
          if applied > 0 else \
          "[✔] V3 conscience:  NO CHANGE NEEDED")
    print(f"[✔] Both AIAs:      INTACT")


if __name__ == "__main__":
    run_trait_bridge()
