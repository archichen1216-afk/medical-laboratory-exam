import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(here);
const read = name => fs.readFileSync(path.join(here, name), 'utf8').replace(/^\uFEFF/, '');
const qbank = JSON.parse(read('questions.json'));
const keys = JSON.parse(read('answers.json'));
const exams = [];
for (const [id, entry] of Object.entries(qbank)) {
  const key = keys[id];
  assert(key, id);
  assert.equal(entry.questions.length, key.count, id);
  const questions = entry.questions.map((question, i) => {
    assert.equal(question.number, i + 1);
    assert(question.stem.trim());
    for (const option of 'ABCD') {
      if (!question.options[option]?.trim()) {
        assert(question.hasImages, `${id} question ${question.number}`);
        question.options[option] = `圖示 ${option}（請查看下方原題與附圖）`;
      }
    }
    assert(question.images.length);
    for (const image of question.images) assert(fs.existsSync(path.resolve(root, image)), image);
    return {...question, id: `${id}:${question.number}`, imageOnlyPages: entry.imageOnlyPages.filter(page => question.pages.includes(page)), answer: key.answers[i], rule: key.effectiveAnswers[i]};
  });
  const [code, category, subject] = id.split('_');
  exams.push({...entry, id, description: entry.fullTitle, source: `https://wwwq.moex.gov.tw/exam/wHandExamQandA_File.ashx?t=Q&code=${code}&c=${category}&s=${subject}&q=1`, answerSource: key.sourceUrl, correctionSource: key.correctionUrl || null, questions});
}
const bank = {version: 1, verifiedAt: '2026-11-05', exams};
const html = read('template.html')
  .replace('/*__STYLE__*/', () => read('style.css') + '\n' + read('feedback.css'))
  .replace('__BANK__', () => JSON.stringify(bank).replace(/</g, '\\u003c'))
  .replace('/*__CORE__*/', () => read('core.js'))
  .replace('/*__APP__*/', () => read('app.js'));
assert(!html.includes('__BANK__'));
fs.writeFileSync(path.join(root, '開始模擬考.html'), html);
fs.writeFileSync(path.join(root, 'index.html'), html);
console.log(JSON.stringify({exams: exams.length, questions: exams.flatMap(exam => exam.questions).length, corrected: exams.flatMap(exam => exam.questions).filter(question => question.rule.note).length}));
