import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import core from './core.js';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const html = fs.readFileSync(path.join(root, '開始模擬考.html'), 'utf8');
const bank = JSON.parse(html.match(/<script id="bank-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const all = bank.exams.flatMap(exam => exam.questions);
assert.equal(bank.exams.length, 12);
assert.equal(all.length, 960);
for (const question of all) {
  assert.deepEqual(Object.keys(question.options), ['A', 'B', 'C', 'D']);
  assert(question.stem.trim());
  assert(question.rule.fullCredit || question.rule.requireAnswer || question.rule.accepted.some(answer => /^[ABCD]$/.test(answer)));
  for (const image of question.images) assert(fs.existsSync(path.resolve(root, image)), image);
}
for (const exam of bank.exams) {
  const answers = Object.fromEntries(exam.questions.map(question => [question.id, question.rule.accepted.find(answer => answer.length === 1) || 'A']));
  assert.equal(core.grade(exam.questions, answers).score, 100, exam.id);
  for (const url of [exam.source, exam.answerSource, exam.correctionSource].filter(Boolean)) assert(/^https:\/\//.test(url), url);
}
console.log(`Verified ${bank.exams.length} subjects and ${all.length} questions.`);
