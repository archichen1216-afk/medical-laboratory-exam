/* Pure scoring functions, shared by the offline application and checks. */
const ExamCore = {
  rule(question){return question.rule || {accepted:[question.answer],fullCredit:false,note:''};},
  correct(question, choice){const r=this.rule(question);return r.fullCredit || (!!choice && (r.requireAnswer || r.accepted.includes(choice)));},
  grade(questions, answers){const rows=questions.map(q=>({id:q.id,number:q.number,choice:answers[q.id]||'',correct:this.correct(q,answers[q.id]),rule:this.rule(q)}));const correct=rows.filter(r=>r.correct).length;return {rows,correct,wrong:rows.filter(r=>!r.correct&&r.choice).length,unanswered:rows.filter(r=>!r.choice).length,total:rows.length,score:rows.length?Math.round(correct/rows.length*10000)/100:0};},
  remaining(session, now=Date.now()){return session.deadline===null?null:Math.max(0,Math.ceil((session.deadline-now)/1000));},
  shuffled(values, random=Math.random){const copy=[...values];for(let i=copy.length-1;i>0;i--){const j=Math.floor(random()*(i+1));[copy[i],copy[j]]=[copy[j],copy[i]];}return copy;}
};
if(typeof module!=='undefined')module.exports=ExamCore;
