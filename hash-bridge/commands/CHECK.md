## Description
List all training checkpoints with loss values

## Command
cd ~/aria-v4-dev
echo "=== CHECKPOINTS ==="
ls -la aria-core/training/checkpoints/*.pt 2>/dev/null | awk '{print $5, $9}'
echo "=== BEST ==="
python3 -c "
import torch, glob
from pathlib import Path
for c in sorted(glob.glob('aria-core/training/checkpoints/*.pt')):
    try:
        d = torch.load(c, map_location='cpu')
        print(f'{Path(c).name} loss={d.get(chr(98)+chr(101)+chr(115)+chr(116)+chr(95)+chr(108)+chr(111)+chr(115)+chr(115),chr(63))}')
    except: pass
" 2>/dev/null
