from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from typing import List

import streamlit as st
from lunardate import LunarDate

TZ = ZoneInfo("Asia/Taipei")


@dataclass
class LunarEvent:
    title: str = "事件"
    lunar_month: int = 1
    lunar_day: int = 1
    is_leap_month: bool = False
    time: str = "09:00"
    duration_minutes: int = 30
    alarm_minutes_before: int | None = 1440
    notes: str = ""


def parse_time_hm(hm: str) -> tuple[int, int]:
    parts = hm.strip().split(":")
    if len(parts) != 2:
        raise ValueError("時間格式需為 HH:MM，例如 09:00")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError("時間需在 00:00 ~ 23:59")
    return h, m


def ics_escape(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def dtstamp_utc() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def format_dt_local(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")


def solar_to_lunar(d: date) -> LunarDate:
    return LunarDate.fromSolarDate(d.year, d.month, d.day)


def lunar_to_solar_date(greg_year: int, lunar_month: int, lunar_day: int, is_leap_month: bool) -> date:
    return LunarDate(greg_year, lunar_month, lunar_day, is_leap_month).toSolarDate()


def build_ics(events: List[LunarEvent], start_year: int, years: int, calendar_name: str) -> str:
    lines: list[str] = []
    lines.append("BEGIN:VCALENDAR")
    lines.append("VERSION:2.0")
    lines.append("PRODID:-//Lunar ICS Generator//Dennis//ZH-TW")
    lines.append("CALSCALE:GREGORIAN")
    lines.append("METHOD:PUBLISH")
    lines.append(f"X-WR-CALNAME:{ics_escape(calendar_name)}")
    lines.append("X-WR-TIMEZONE:Asia/Taipei")

    for ev in events:
        h, m = parse_time_hm(ev.time)

        for y in range(start_year, start_year + years):
            solar = lunar_to_solar_date(y, ev.lunar_month, ev.lunar_day, ev.is_leap_month)
            start_dt = datetime(solar.year, solar.month, solar.day, h, m, 0, tzinfo=TZ)
            end_dt = start_dt + timedelta(minutes=ev.duration_minutes)

            uid = f"{uuid.uuid4()}@lunar-ics"
            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{uid}")
            lines.append(f"DTSTAMP:{dtstamp_utc()}")
            lines.append(f"SUMMARY:{ics_escape(ev.title)}")

            if ev.notes:
                lines.append(f"DESCRIPTION:{ics_escape(ev.notes)}")

            lines.append(f"DTSTART;TZID=Asia/Taipei:{format_dt_local(start_dt)}")
            lines.append(f"DTEND;TZID=Asia/Taipei:{format_dt_local(end_dt)}")

            if ev.alarm_minutes_before is not None:
                minutes = int(ev.alarm_minutes_before)
                lines.append("BEGIN:VALARM")
                lines.append("ACTION:DISPLAY")
                lines.append(f"DESCRIPTION:{ics_escape(ev.title)}")
                lines.append(f"TRIGGER:-PT{minutes}M")
                lines.append("END:VALARM")

            lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def apply_css(style_mode: str) -> None:
    if style_mode == "拜拜吉利":
        accent = "#D4AF37"
        accent2 = "#C62828"
        bg = "#0B0F19"
        text = "#F9FAFB"
        muted = "#CBD5E1"
    else:
        accent = "#2563EB"
        accent2 = "#0EA5E9"
        bg = "#0B1220"
        text = "#E5E7EB"
        muted = "#94A3B8"

    st.markdown(
        f"""
<style>
.stApp {{
  background: radial-gradient(1200px 800px at 20% 10%, rgba(37,99,235,0.18), transparent 55%),
              radial-gradient(900px 700px at 85% 15%, rgba(14,165,233,0.12), transparent 60%),
              {bg};
  color: {text};
}}
.block-container {{ padding-top: 2.2rem; }}
div[data-testid="stExpander"] > details {{
  border: 1px solid rgba(148,163,184,0.20);
  border-radius: 16px;
  background: rgba(255,255,255,0.03);
}}
.stButton>button {{
  border-radius: 14px;
  border: 1px solid rgba(148,163,184,0.24);
  background: rgba(255,255,255,0.04);
  color: {text};
}}
div.stDownloadButton>button {{
  border-radius: 14px;
  border: 1px solid rgba(148,163,184,0.24);
  background: linear-gradient(135deg, {accent}, {accent2});
  color: white;
}}
[data-testid="stCaptionContainer"] {{ color: {muted} !important; }}
</style>
""",
        unsafe_allow_html=True,
    )


def ensure_defaults() -> None:
    if "events" not in st.session_state:
        st.session_state.events = [
            asdict(LunarEvent(
                title="媽祖生日",
                lunar_month=3,
                lunar_day=23,
                time="09:00",
                alarm_minutes_before=1440,
                duration_minutes=30,
                notes="準備供品/香燭"
            ))
        ]


def alarm_label_to_minutes(label: str, current: int | None) -> int | None:
    mapping = {
        "無": None, "當下": 0, "10 分鐘前": 10, "30 分鐘前": 30,
        "1 小時前": 60, "3 小時前": 180, "1 天前": 1440, "2 天前": 2880
    }
    return mapping.get(label, current if current is not None else 60)


st.set_page_config(page_title="農曆提醒產生器", page_icon="🗓️", layout="wide")
style_mode = st.sidebar.selectbox("風格", ["簡單乾淨", "拜拜吉利"], index=0)
apply_css(style_mode)

st.title("🗓️ 農曆提醒產生器")
st.caption("以農曆為主建立提醒，輸出 iPhone 可匯入的 .ics。資料不會寫入資料庫，只在你這次瀏覽器暫存。")

ensure_defaults()

st.subheader("產生設定")
st.caption("這裡決定要幫你產生『哪些國曆年份』的事件（例如：2026 起，往後 20 年）。")
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    start_year = st.number_input("起始年（國曆）", min_value=1900, max_value=2200, value=datetime.now(TZ).year, step=1)
with c2:
    years = st.number_input("往後產生（年）", min_value=1, max_value=60, value=20, step=1)
with c3:
    calendar_name = st.text_input("匯入顯示名稱", value="農曆提醒")

b1, b2 = st.columns([1, 3])
with b1:
    if st.button("➕ 增加事項", use_container_width=True):
        st.session_state.events.append(asdict(LunarEvent()))
with b2:
    st.caption("提示：iPhone 匯入時請選你建立的『農曆提醒』行事曆。")

st.divider()
st.subheader("事項清單")

for idx, ev in enumerate(list(st.session_state.events)):
    with st.expander(f"{idx+1}. {ev.get('title') or '未命名事項'}", expanded=True):
        mode_key = f"mode_{idx}"
        if mode_key not in st.session_state:
            st.session_state[mode_key] = "農曆"
        mode = st.radio("日期輸入方式", ["農曆", "國曆"], horizontal=True, key=mode_key)

        top = st.columns([2, 1, 1, 1])
        ev["title"] = top[0].text_input("名稱", value=ev.get("title", ""), key=f"title_{idx}")

        if mode == "農曆":
            mid = st.columns([1, 1, 1, 2])
            ev["lunar_month"] = mid[0].number_input("農曆月", 1, 12, int(ev.get("lunar_month", 1)), 1, key=f"lm_{idx}")
            ev["lunar_day"] = mid[1].number_input("農曆日", 1, 30, int(ev.get("lunar_day", 1)), 1, key=f"ld_{idx}")
            ev["is_leap_month"] = mid[2].checkbox("閏月", value=bool(ev.get("is_leap_month", False)), key=f"leap_{idx}")
            try:
                preview = lunar_to_solar_date(int(start_year), int(ev["lunar_month"]), int(ev["lunar_day"]), bool(ev["is_leap_month"]))
                mid[3].markdown(f"**{start_year} 年對應國曆：** {preview.isoformat()}")
            except Exception:
                pass
        else:
            sol_key = f"solar_{idx}"
            if sol_key not in st.session_state:
                st.session_state[sol_key] = date.today()
            d = st.date_input("國曆日期", value=st.session_state[sol_key], key=sol_key)
            try:
                ld = solar_to_lunar(d)
                is_leap = bool(getattr(ld, "isLeapMonth", False))
                ev["lunar_month"] = int(ld.month)
                ev["lunar_day"] = int(ld.day)
                ev["is_leap_month"] = is_leap
                st.markdown(f"**自動轉成農曆：** {ld.year}年 {ld.month}月{ld.day}日 {'（閏月）' if is_leap else ''}")
            except Exception as e:
                st.error(f"轉換失敗：{e}")

        row = st.columns([1, 1, 1, 2])
        ev["time"] = row[0].text_input("時間 HH:MM", value=ev.get("time", "09:00"), key=f"time_{idx}")
        ev["duration_minutes"] = row[1].number_input("時長(分)", 1, 1440, int(ev.get("duration_minutes", 30)), 5, key=f"dur_{idx}")

        options = ["無", "當下", "10 分鐘前", "30 分鐘前", "1 小時前", "3 小時前", "1 天前", "2 天前", "自訂(分鐘)"]
        current_alarm = ev.get("alarm_minutes_before", 1440)
        idx_default = 6 if current_alarm == 1440 else (7 if current_alarm == 2880 else (5 if current_alarm == 180 else (4 if current_alarm == 60 else (3 if current_alarm == 30 else (2 if current_alarm == 10 else (1 if current_alarm == 0 else (0 if current_alarm is None else 8)))))))
        choice = row[2].selectbox("提醒", options, index=idx_default, key=f"alarm_sel_{idx}")
        if choice == "自訂(分鐘)":
            ev["alarm_minutes_before"] = int(st.number_input("自訂提前(分)", 0, 10080, int(current_alarm or 60), 5, key=f"alarm_custom_{idx}"))
        else:
            ev["alarm_minutes_before"] = alarm_label_to_minutes(choice, current_alarm)

        ev["notes"] = row[3].text_input("備註（可空白）", value=ev.get("notes", ""), key=f"notes_{idx}")

        d1, _ = st.columns([1, 5])
        if d1.button("刪除", key=f"del_{idx}", use_container_width=True):
            st.session_state.events.pop(idx)
            st.rerun()

st.session_state.events = st.session_state.events or [asdict(LunarEvent())]

with st.expander("匯入 / 匯出（events.json）", expanded=False):
    left, right = st.columns(2)
    with left:
        export_json = json.dumps(st.session_state.events, ensure_ascii=False, indent=2)
        st.download_button("下載 events.json", export_json.encode("utf-8"), "events.json", "application/json", use_container_width=True)
    with right:
        up = st.file_uploader("匯入 events.json", type=["json"])
        if up is not None:
            try:
                raw = json.loads(up.getvalue().decode("utf-8"))
                if not isinstance(raw, list):
                    raise ValueError("JSON 需為陣列（list）")
                st.session_state.events = raw if raw else [asdict(LunarEvent())]
                st.success(f"已匯入 {len(st.session_state.events)} 筆事項。")
                st.rerun()
            except Exception as e:
                st.error(f"匯入失敗：{e}")

st.divider()
st.subheader("下載 .ics")
st.caption("下載後把檔案傳到 iPhone（AirDrop / iCloud Drive / Email），點開即可加入行事曆。")

try:
    events_dc = [LunarEvent(**e) for e in st.session_state.events]
    ics_text = build_ics(events_dc, int(start_year), int(years), calendar_name=calendar_name)
    st.download_button("下載 lunar_events.ics", ics_text.encode("utf-8"), "lunar_events.ics", "text/calendar", use_container_width=True)
except Exception as e:
    st.error(f"產生失敗：{e}")
