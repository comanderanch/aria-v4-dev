import json
from datetime import datetime

curiosity_log = []

def curiosity_trigger(condition_data, fold_hash):
    timestamp = datetime.now().isoformat()
    base_query = "why did I think this"

    evaluation = {
        "reducible_to_token_map": False,
        "reducible_to_emotion": False,
        "reducible_to_memory": False,
        "reducible_to_recent": False,
        "reducible_to_field": False
    }

    meta = {
        "repeatability_expected": True,
        "origin_reconstructable": False,
        "state": "unresolved"
    }

    record = {
        "timestamp": timestamp,
        "fold_hash": fold_hash,
        "query": base_query,
        "condition_data": condition_data,
        "evaluation": evaluation,
        "meta": meta
    }

    curiosity_log.append(record)

    log_entry = f"""
---
CURIOSITY EVENT
timestamp: {timestamp}
fold_hash: {fold_hash}
query: {base_query}
state: unresolved
origin_reconstructable: False
---
"""
    with open("docs/EMERGENCE_LOG.md", "a") as f:
        f.write(log_entry)

    return record

def curiosity_summary():
    total = len(curiosity_log)
    return {
        "total_curiosity_events": total,
        "unresolved": total
    }
