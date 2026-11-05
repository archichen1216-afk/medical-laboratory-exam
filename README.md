# 醫檢師模擬考程式

115 年考選部醫事檢驗師試題的離線模擬考網站，可直接開啟 `index.html` 使用。

- 12 科、兩次考試題庫
- 計時考試與不限時練習、即時回饋、提早交卷與成績統計
- 錯題練習、原題影像、作答進度保存與紀錄匯出
- 題目、標準答案與更正答案均對應考選部官方來源

重新產生題庫：

```text
python source/build_questions.py
python source/extract_answers.py
node source/build.mjs
node source/verify.mjs
```
