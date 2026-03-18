## Description
Corpus stats — size, sequence count, coverage

## Command
cd ~/aria-v4-dev
echo "=== FILTERED CORPUS ==="
wc -w aria-core/training/filtered_corpus.txt 2>/dev/null
echo "=== CALIBRE CORPUS ==="
ls -lh aria-core/training/calibre_corpus.txt 2>/dev/null
