## Description
Translation training status — pairs loaded, last run, best loss

## Command
cd ~/aria-v4-dev
echo "=== TRANSLATION PAIRS ==="
grep -c "^[^#].*<SEP>" aria-core/training/translation_pairs.txt 2>/dev/null | xargs -I{} echo "Pairs: {}"
echo "=== LAST RUN ==="
tail -10 /tmp/aria-translation-train.log 2>/dev/null || echo "No translation training run yet"
echo "=== CHECKPOINT ==="
ls -lh checkpoints/translation_best.pt 2>/dev/null || echo "No translation checkpoint yet"
echo "=== DONE ==="
