## Description
Queens Fold — palace chambers, hash count, last seal

## Command
cd ~/aria-v4-dev
echo "=== PALACE CHAMBERS ==="
find aria-core/queens-fold/palace -name "*.json" 2>/dev/null | wc -l
echo "=== LAST SEAL ==="
tail -20 aria-core/queens-fold/fold_log.jsonl 2>/dev/null || echo "No fold log found"
