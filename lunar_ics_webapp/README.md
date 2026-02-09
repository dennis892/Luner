# 農曆行事曆提醒產生器（Web App / 不存伺服器）

這是一個 Streamlit 網頁 App：
- 以「農曆日期」新增事項（表單輸入）
- 產生未來 N 年對應的國曆事件
- 下載 `.ics` 後匯入 iPhone 行事曆（含提醒）

> 不寫入資料庫、不做伺服器永久保存。  
> 只在你目前開啟的瀏覽器 session 記憶體中暫存。

---

## 本機執行

1) 安裝
```bash
pip install -r requirements.txt
```

2) 啟動
```bash
streamlit run app.py
```

---

## 分享給別人（推薦：Streamlit Community Cloud）

1) 把這個資料夾推到 GitHub（公開/私有都可）
2) 到 Streamlit Community Cloud 連結你的 repo
3) 指定：
- Main file: `app.py`

部署完成後就有一個網址可以分享。

---

## iPhone 匯入

1) 在網頁下載 `lunar_events.ics`
2) AirDrop / iCloud Drive / Email 到 iPhone
3) iPhone 點開 `.ics` → 選「加入所有事件」
