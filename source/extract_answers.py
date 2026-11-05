from pathlib import Path
import json, re, sys, unicodedata

import pdfplumber
from pypdf import PdfReader

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent / '考選部醫檢師試題' / '115年'

def get_rows(text):
    normalized = unicodedata.normalize('NFKC', text)
    lines = [line.strip() for line in normalized.splitlines() if re.fullmatch(r'答案(?:\s+[ABCD#])+', line.strip())]
    assert all(len(re.findall(r'[ABCD#]', line)) == 20 for line in lines)
    return [answer for line in lines for answer in re.findall(r'[ABCD#]', line)]

def check_geometry(path, expected):
    with pdfplumber.open(path) as pdf:
        actual = get_rows('\n'.join(page.extract_text() or '' for page in pdf.pages))
    assert actual == expected, ('PDF parsing disagreement', path)

answers, corrections = {}, {}
for path in sorted(ROOT.rglob('*_答案.pdf')):
    match = re.match(r'(\d{6})_(\d{3})_(\d{4})_答案\.pdf$', path.name)
    if not match:
        continue
    code, category, subject = match.groups()
    exam_id = f'{code}_{category}_{subject}'
    text = '\n'.join(page.extract_text() or '' for page in PdfReader(path).pages)
    normalized = unicodedata.normalize('NFKC', text)
    count = int(re.search(r'題\s*數:\s*(\d+)題', normalized).group(1))
    official = get_rows(text)
    assert len(official) == count, (exam_id, count, len(official))
    check_geometry(path, official)
    answer_url = f'https://wwwq.moex.gov.tw/exam/wHandExamQandA_File.ashx?t=S&code={code}&c={category}&s={subject}&q=1'
    record = {'answers': official, 'count': count, 'source': path.relative_to(ROOT).as_posix(), 'sourceUrl': answer_url,
              'effectiveAnswers': [{'accepted': [answer], 'fullCredit': False, 'requireAnswer': False, 'note': ''} for answer in official]}
    correction = path.with_name(path.name.replace('_答案.pdf', '_更正答案.pdf'))
    updates = []
    if correction.exists():
        correction_text = '\n'.join(page.extract_text() or '' for page in PdfReader(correction).pages)
        corrected = get_rows(correction_text)
        assert len(corrected) == count
        check_geometry(correction, corrected)
        note_text = re.sub(r'\s+', '', unicodedata.normalize('NFKC', correction_text))
        note_text = note_text[note_text.index('第'):]
        notes = re.findall(r'第(\d+)題(.*?)(?=,?第\d+題|$)', note_text)
        expected_changed = {i + 1 for i, answer in enumerate(corrected) if answer == '#'}
        assert set(int(number) for number, _ in notes) == expected_changed, (exam_id, notes, expected_changed)
        for number, rule in notes:
            n, rule = int(number), rule.rstrip(',，。')
            update = {'question': n, 'original': official[n - 1], 'accepted': [], 'fullCredit': False, 'requireAnswer': False, 'note': f'第{n}題{rule}'}
            if rule == '一律給分':
                update['fullCredit'] = True
            elif rule == '除未作答者不給分外,其餘均給分':
                update['requireAnswer'], update['accepted'] = True, ['A', 'B', 'C', 'D']
            else:
                result = re.fullmatch(r'答([ABCD或]+)者均給分', rule)
                assert result, (exam_id, rule)
                update['accepted'] = result.group(1).split('或')
            record['effectiveAnswers'][n - 1] = {key: update[key] for key in ['accepted', 'fullCredit', 'requireAnswer', 'note']}
            updates.append(update)
        assert all(answer == '#' or answer == official[i] for i, answer in enumerate(corrected))
        record['correctionSource'] = correction.relative_to(ROOT).as_posix()
        record['correctionUrl'] = f'https://wwwq.moex.gov.tw/exam/wHandExamQandA_File.ashx?t=M&code={code}&c={category}&s={subject}&q=1'
    answers[exam_id] = record
    corrections[exam_id] = {'source': record.get('correctionSource'), 'url': record.get('correctionUrl'), 'updates': updates}
    print(exam_id, count, 'questions;', len(updates), 'corrections')

(HERE / 'answers.json').write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding='utf-8')
(HERE / 'corrections.json').write_text(json.dumps(corrections, ensure_ascii=False, indent=2), encoding='utf-8')
print('Extracted', len(answers), 'subjects;', sum(item['count'] for item in answers.values()), 'answers')
