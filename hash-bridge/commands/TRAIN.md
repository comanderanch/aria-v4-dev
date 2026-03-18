## Description
Show active training process and last 20 lines of round log

## Command
ps aux | grep "run_round" | grep -v grep
echo "---"
ls -t /tmp/aria-round*.log 2>/dev/null | head -1 | xargs tail -20 2>/dev/null || echo "No training log found"
