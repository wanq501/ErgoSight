"""Build ErgoSight-Bench.zip, the release asset with the interface pages and the question images, from an ErgoHMI export.

Usage:
    python scripts/pack_dataset.py --export <folder of the ErgoHMI export> [--out ErgoSight-Bench.zip]

The script searches the export for
  - the HTML file of every page in data/questions.jsonl, named <page_id>.html or <page_id>/index.html, and
  - the image folder of every question, a folder named <qid> holding s0.jpg and, where the question has them,
    the views loupe.jpg, ruler.jpg and sim.jpg of the Physical View Lens.
It checks that every page and every image listed in the `inputs` of the questions is present, and writes
    pages/<page_id>.html     every page of the export, which must include the pages of all questions
    images/<qid>/<name>.jpg
    MANIFEST.csv            path, size and SHA-256 of every file
into the archive, which unpacks into data/ of this repository. Missing files stop the build unless --allow-missing is given.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def index_export(export: Path):
    pages, qdirs = {}, {}
    for p in export.rglob('*'):
        if p.is_file() and p.suffix.lower() == '.html':
            key = p.parent.name if p.name.lower() == 'index.html' else p.stem
            pages.setdefault(key, p)
        elif p.is_dir() and re.fullmatch(r'q\d{5}', p.name) and (p / 's0.jpg').exists():
            qdirs.setdefault(p.name, p)
    return pages, qdirs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--export', required=True, type=Path)
    ap.add_argument('--out', default='ErgoSight-Bench.zip', type=Path)
    ap.add_argument('--allow-missing', action='store_true')
    a = ap.parse_args()
    questions = [json.loads(line) for line in (ROOT / 'data' / 'questions.jsonl').open(encoding='utf-8')]
    pages, qdirs = index_export(a.export)
    need_pages = sorted({q['page_id'] for q in questions})
    files, missing = [], []
    for pid in need_pages:
        (files.append((f'pages/{pid}.html', pages[pid])) if pid in pages else missing.append(f'page {pid}'))
    for pid in sorted(set(pages) - set(need_pages)):        # the benchmark pages without a question, such as unrepaired originals
        files.append((f'pages/{pid}.html', pages[pid]))
    for q in questions:
        names = sorted({n for v in q['inputs'].values() for n in v})
        for n in names:
            src = qdirs.get(q['qid'], Path('/nonexistent')) / f'{n}.jpg'
            (files.append((f"images/{q['qid']}/{n}.jpg", src)) if src.exists() else missing.append(f"image {q['qid']}/{n}.jpg"))
    print(f'pages found {len(need_pages) - sum(m.startswith("page") for m in missing)} of {len(need_pages)}, '
          f'images found {sum(1 for f in files if f[0].startswith("images/"))} of {sum(1 for f in files if f[0].startswith("images/")) + sum(m.startswith("image") for m in missing)}')
    if missing:
        print(f'{len(missing)} files missing, for example: ' + ', '.join(missing[:5]))
        if not a.allow_missing:
            sys.exit('stopped: export incomplete (use --allow-missing only for a test build)')
    manifest = io.StringIO(); w = csv.writer(manifest); w.writerow(['path', 'bytes', 'sha256'])
    with zipfile.ZipFile(a.out, 'w', compression=zipfile.ZIP_STORED) as z:
        for arc, src in files:
            data = src.read_bytes(); z.writestr(arc, data); w.writerow([arc, len(data), hashlib.sha256(data).hexdigest()])
        z.writestr('MANIFEST.csv', manifest.getvalue())
    print(f'wrote {a.out} with {len(files)} files')


if __name__ == '__main__':
    main()
