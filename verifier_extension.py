"""
Verifier Extension (Non-invasive)

Purpose:

Parse existing token_trail output

Extract required verification numbers

Output strict label format

DOES NOT modify existing scripts
"""

import re


def parse_attractor_report(text):
    data = {}

    # --- CORE ---
    exact_match = re.search(r'● EXACT:\s+(\d+)', text)
    if exact_match:
        data["exact_token_count"] = int(exact_match.group(1))

    # --- VIOLET SECTION ---
    violet_mean = re.search(r'mean_X:\s+([0-9.]+)', text)
    violet_std = re.search(r'std_dev:\s+([0-9.]+)', text)

    if violet_mean:
        data["violet_mean_X"] = float(violet_mean.group(1))
    if violet_std:
        data["violet_std_dev"] = float(violet_std.group(1))

    # --- DRIFT (DISTANT TOKENS COUNT) ---
    distant_match = re.search(r'◌ DISTANT:\s+(\d+)', text)
    if distant_match:
        data["drift_tokens"] = int(distant_match.group(1))

    # --- MAX DELTA ---
    deltas = re.findall(r'Δ([0-9.]+)', text)
    if deltas:
        data["max_delta"] = max(float(d) for d in deltas)

    return data


def run_extension(file_path):
    with open(file_path, "r") as f:
        text = f.read()

    data = parse_attractor_report(text)

    # --- STRICT OUTPUT ---
    print("violet_mean_X:", data.get("violet_mean_X"))
    print("violet_std_dev:", data.get("violet_std_dev"))
    print("exact_token_count:", data.get("exact_token_count"))
    print("drift_tokens:", data.get("drift_tokens"))
    print("max_delta:", data.get("max_delta"))


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python3 verifier_extension.py <attractor_output.txt>")
    else:
        run_extension(sys.argv[1])
