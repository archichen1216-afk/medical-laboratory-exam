import json, re, shutil, subprocess, sys, unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]
PDFROOT = ROOT.parent / '考選部醫檢師試題' / '115年'
ASSETS = ROOT / 'assets'
ASSETS.mkdir(parents=True, exist_ok=True)

def clean(text):
    return re.sub(r'[ \t]+', ' ', text).strip()

bank, issues, render_jobs = {}, [], []
for path in sorted(PDFROOT.rglob('*_試題.pdf')):
    match = re.match(r'(\d{6})_(\d{3})_(\d{4})_試題\.pdf$', path.name)
    if not match:
        continue
    code, category, subject = match.groups()
    key = f'{code}_{category}_{subject}'
    reader = PdfReader(path)
    texts = [page.extract_text() or '' for page in reader.pages]
    with pdfplumber.open(path) as layout_pdf:
        graphic_pages = {i + 1 for i, page in enumerate(layout_pdf.pages) if page.images}

    offsets, full = [], ''
    for i, text in enumerate(texts):
        offsets.append((len(full), len(full) + len(text), i + 1))
        full += text + '\n'
    starts = list(re.finditer(r'(?m)^\s*(\d{1,3})\s*[.．、]\s*(?=\S)', full))
    ordered, expected = [], 1
    for item in starts:
        if int(item[1]) == expected:
            ordered.append(item)
            expected += 1
    if len(ordered) != 80:
        issues.append({'id': key, 'questionCount': len(ordered), 'allNumbers': [int(x[1]) for x in starts]})
    questions = []
    for i, item in enumerate(ordered):
        end = ordered[i + 1].start() if i + 1 < len(ordered) else len(full)
        body = full[item.end():end].strip()
        options = list(re.finditer(r'(?m)^\s*([ABCDＡＢＣＤ])\s*[.．、]\s*', body))
        parsed = {}
        if len(options) == 4 and ''.join(unicodedata.normalize('NFKC', x[1]) for x in options) == 'ABCD':
            stem = clean(body[:options[0].start()])
            for j, option in enumerate(options):
                stop = options[j + 1].start() if j + 1 < len(options) else len(body)
                parsed[unicodedata.normalize('NFKC', option[1])] = clean(body[option.end():stop])
        else:
            stem, parsed = clean(body), {letter: '' for letter in 'ABCD'}
            # Some vector-heavy ECG pages extract their option text out of visual order.
            # The original-page image remains embedded in the practice app for these items.
            issues.append({'id': key, 'question': int(item[1]), 'optionMarkers': [x[1] for x in options], 'body': body[:500]})
        pages = [page for start, stop, page in offsets if item.start() < stop and end > start]
        questions.append({'number': int(item[1]), 'stem': stem, 'options': parsed, 'pages': pages,
                          'images': [f'assets/{key}/page-{page:02d}.jpg' for page in pages],
                          'hasImages': any(page in graphic_pages for page in pages) or len(options) != 4})

    _, subject_name = path.parent.name.split('_', 1)
    minutes = re.search(r'考試時間[：:]\s*(\d+)\s*小時', full)
    bank[key] = {'title': subject_name, 'fullTitle': subject_name, 'exam': path.parent.parent.name,
                 'category': '高等考試_醫事檢驗師', 'minutes': int(minutes[1]) * 60 if minutes else 120,
                 'source': '../考選部醫檢師試題/115年/' + path.relative_to(PDFROOT).as_posix(),
                 'questions': questions, 'pageCount': len(texts),
                 'imageOnlyPages': [i + 1 for i, text in enumerate(texts) if not text.strip()]}
    print(key, 'questions', len(questions), 'pages', len(texts))
    render_jobs.append((key, path, len(texts)))

(ROOT / 'source' / 'question_issues.json').write_text(json.dumps(issues, ensure_ascii=False, indent=2), encoding='utf-8')
(ROOT / 'source' / 'questions.json').write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding='utf-8')

def render(job):
    key, path, count = job
    target = ASSETS / key
    target.mkdir(exist_ok=True)
    if len(list(target.glob('page-*.jpg'))) != count:
        subprocess.run([shutil.which('pdftoppm'), '-r', '130', '-jpeg', '-jpegopt', 'quality=88', str(path), str(target / 'page')], check=True, capture_output=True)
    assert all((target / f'page-{page:02d}.jpg').exists() for page in range(1, count + 1)), key
    return key

with ThreadPoolExecutor(max_workers=3) as pool:
    for key in pool.map(render, render_jobs):
        print('Rendered', key, flush=True)
print('All question pages rendered')
