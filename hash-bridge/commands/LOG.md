## Description
Full tail of most recent training log — 50 lines

## Command
ls -t /tmp/aria-round*.log 2>/dev/null | head -1 | xargs tail -50 2>/dev/null || echo "No training log found"
