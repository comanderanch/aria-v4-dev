## Description
Full system status — GPU, training, vocab, git

## Command
cd ~/aria-v4-dev
echo "=== GPU ==="
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader
echo "=== TRAINING ==="
tail -3 /tmp/aria-round22.log 2>/dev/null || echo "No active training log"
echo "=== VOCAB ==="
python3 -c "import json; d=json.load(open('tokenizer/aria_vocab.json')); print('Words:', len(d['vocab']))" 2>/dev/null
echo "=== GIT ==="
git log --oneline -3
echo "=== DONE ==="
