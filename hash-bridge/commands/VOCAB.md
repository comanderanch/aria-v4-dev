## Description
Vocabulary stats — size, plane distribution, coverage

## Command
cd ~/aria-v4-dev
python3 -c "
import json
d = json.load(open('tokenizer/aria_vocab.json'))
print(f'Total words: {len(d)}')
" 2>/dev/null
