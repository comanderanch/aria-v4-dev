## Description
Token trail — last 20 activations, active planes, gradient path

## Command
cd ~/aria-v4-dev
echo "=== TOKEN TRAIL ==="
python3 aria-core/diagnostics/token_trail.py --show-arc --top-tokens 10 2>/dev/null || echo "No trail data yet"
echo "=== BREAKTHROUGHS ==="
python3 aria-core/diagnostics/token_trail.py --show-breakthroughs 2>/dev/null
echo "=== PLANES ==="
python3 aria-core/diagnostics/token_trail.py --show-planes 2>/dev/null
