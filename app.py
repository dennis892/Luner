from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from typing import List, Optional

import streamlit as st
from lunardate import LunarDate

TZ = ZoneInfo("Asia/Taipei")


@dataclass
class LunarEvent:
    title: str = "事件"
    lunar_month: int = 1
    lunar_day: int = 1
    is_leap_month: bool = False
    time: str = "09:00"               # HH:MM
    duration_minutes: int = 30
    alarm_minutes_before: Optional[int] = 1440  # None = no alarm
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


def lunar_to_solar_date(greg_year: int, lunar_month: int, lunar_day: int, is_leap_month: bool) -> date:
    return LunarDate(greg_year, lunar_month, lunar_day, is_leap_month).toSolarDate()


def build_ics(events: List[LunarEvent], start_year: int, years: int, calendar_name: str = "農曆提醒") -> str:
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

            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{uuid.uuid4()}@lunar-ics")
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


def apply_css() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Yuji+Syuku&display=swap');

:root{
  --bg: #B3131B;
  --card: rgba(255,255,255,0.92);
  --border: rgba(0,0,0,0.10);
  --text: #1F2937;
  --muted: rgba(55,65,81,0.72);
  --gold: #F5D76E;
}

.stApp{
  background:
    radial-gradient(1200px 800px at 18% 8%, rgba(245,215,110,0.22), transparent 55%),
    radial-gradient(900px 700px at 85% 15%, rgba(255,255,255,0.14), transparent 60%),
    var(--bg);
  color: var(--text);
}

.stApp:before{
  content:'';
  position:fixed; inset:0;
  pointer-events:none;
  background-image: radial-gradient(rgba(0,0,0,0.06) 1px, transparent 1px);
  background-size: 6px 6px;
  opacity: 0.22;
  mix-blend-mode: multiply;
}

.block-container{
  max-width: 1100px;
  padding-top: 2.2rem;
  padding-bottom: 3rem;
}

h1, h2, h3{
  font-family: "Yuji Syuku", ui-serif, "Hiragino Mincho ProN", "Noto Serif TC", serif !important;
  letter-spacing: 0.01em;
}

[data-testid="stCaptionContainer"]{
  color: rgba(255,255,255,0.80) !important;
}

div[data-testid="stExpander"] > details{
  border: 1px solid var(--border);
  border-radius: 18px;
  background: var(--card);
  box-shadow: 0 14px 34px rgba(0,0,0,0.18);
}
div[data-testid="stExpander"] summary{
  font-weight: 650;
}

div[data-testid="stExpander"] [data-testid="stCaptionContainer"]{
  color: var(--muted) !important;
}

input, textarea{
  border-radius: 12px !important;
}

.stButton>button{
  border-radius: 14px;
  border: 1px solid var(--border);
  background: rgba(255,255,255,0.86);
  color: var(--text);
  padding: 0.55rem 0.85rem;
}
.stButton>button:hover{
  filter: brightness(1.02);
}

div.stDownloadButton>button{
  border-radius: 14px;
  border: 1px solid rgba(0,0,0,0.12);
  background: linear-gradient(135deg, var(--gold), #FFFFFF);
  color: #1F2937;
  font-weight: 700;
  padding: 0.62rem 0.95rem;
}
</style>
""",
        unsafe_allow_html=True,
    )


def ensure_state() -> None:
    if "events" not in st.session_state:
        st.session_state.events = [
            asdict(LunarEvent(
                title="媽祖生日",
                lunar_month=3,
                lunar_day=23,
                is_leap_month=False,
                time="09:00",
                duration_minutes=30,
                alarm_minutes_before=1440,
                notes="準備供品/香燭"
            ))
        ]


def alarm_default_index(minutes: Optional[int]) -> int:
    opts = ["無", "當下", "10 分鐘前", "30 分鐘前", "1 小時前", "3 小時前", "1 天前", "2 天前", "自訂(分鐘)"]
    mapping = {None: 0, 0: 1, 10: 2, 30: 3, 60: 4, 180: 5, 1440: 6, 2880: 7}
    return mapping.get(minutes, 8)


def alarm_label_to_minutes(label: str, current: Optional[int]) -> Optional[int]:
    mapping = {
        "無": None, "當下": 0, "10 分鐘前": 10, "30 分鐘前": 30,
        "1 小時前": 60, "3 小時前": 180, "1 天前": 1440, "2 天前": 2880
    }
    if label in mapping:
        return mapping[label]
    return current if current is not None else 60


st.set_page_config(page_title="農曆提醒產生器", page_icon="🗓️", layout="wide")
apply_css()
ensure_state()

st.title("⛩️ 農曆提醒產生器")
st.caption("只輸入農曆（月/日/閏月），會顯示起始年對應的國曆日期作為查對，並輸出 iPhone 可匯入的 .ics。")

st.subheader("產生設定")
st.caption("決定要產生哪些『國曆年份』的事件（例如：2026 起，往後 20 年）。")
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    start_year = st.number_input("起始年（國曆）", min_value=1900, max_value=2200, value=datetime.now(TZ).year, step=1)
with c2:
    years = st.number_input("往後產生（年）", min_value=1, max_value=60, value=20, step=1)
with c3:
    st.write("")
    st.write("")
    if st.button("➕ 增加事項", use_container_width=True):
        st.session_state.events.append(asdict(LunarEvent()))

st.divider()
st.subheader("事項清單")

for idx, ev in enumerate(list(st.session_state.events)):
    title = (ev.get("title") or "未命名事項").strip()
    with st.expander(f"{idx+1}. {title}", expanded=True):
        ev["title"] = st.text_input("名稱", value=ev.get("title", ""), key=f"title_{idx}")

        d1, d2, d3, d4 = st.columns([1, 1, 1, 2])
        ev["lunar_month"] = d1.number_input("農曆月", 1, 12, int(ev.get("lunar_month", 1)), 1, key=f"lm_{idx}")
        ev["lunar_day"] = d2.number_input("農曆日", 1, 30, int(ev.get("lunar_day", 1)), 1, key=f"ld_{idx}")
        ev["is_leap_month"] = d3.checkbox("閏月", value=bool(ev.get("is_leap_month", False)), key=f"leap_{idx}")

        try:
            preview = lunar_to_solar_date(int(start_year), int(ev["lunar_month"]), int(ev["lunar_day"]), bool(ev["is_leap_month"]))
            d4.markdown(f"**{start_year} 年對應國曆：** {preview.isoformat()}")
        except Exception:
            d4.markdown("")

        t1, t2, t3, t4 = st.columns([1, 1, 1, 2])
        ev["time"] = t1.text_input("時間 HH:MM", value=ev.get("time", "09:00"), key=f"time_{idx}")
        ev["duration_minutes"] = t2.number_input("時長(分)", 1, 1440, int(ev.get("duration_minutes", 30)), 5, key=f"dur_{idx}")

        alarm_options = ["無", "當下", "10 分鐘前", "30 分鐘前", "1 小時前", "3 小時前", "1 天前", "2 天前", "自訂(分鐘)"]
        current_alarm = ev.get("alarm_minutes_before", 1440)
        sel = t3.selectbox("提醒", options=alarm_options, index=alarm_default_index(current_alarm), key=f"alarm_sel_{idx}")
        if sel == "自訂(分鐘)":
            ev["alarm_minutes_before"] = int(st.number_input(
                "自訂提前(分)", 0, 10080, int(current_alarm or 60), 5, key=f"alarm_custom_{idx}"
            ))
        else:
            ev["alarm_minutes_before"] = alarm_label_to_minutes(sel, current_alarm)

        ev["notes"] = t4.text_input("備註（可空白）", value=ev.get("notes", ""), key=f"notes_{idx}")

        if st.button("刪除這筆事項", key=f"del_{idx}"):
            st.session_state.events.pop(idx)
            st.rerun()

if not st.session_state.events:
    st.session_state.events = [asdict(LunarEvent())]

st.divider()

with st.expander("📦 備份 / 還原（農曆事項）", expanded=False):
    st.caption("備份檔只包含你設定的農曆事項，不會修改手機行事曆。")
    left, right = st.columns(2)
    with left:
        export_json = json.dumps(st.session_state.events, ensure_ascii=False, indent=2)
        st.download_button(
            "下載備份檔",
            data=export_json.encode("utf-8"),
            file_name="events.json",
            mime="application/json",
            use_container_width=True
        )
    with right:
        up = st.file_uploader("還原備份檔", type=["json"])
        if up is not None:
            try:
                raw = json.loads(up.getvalue().decode("utf-8"))
                if not isinstance(raw, list):
                    raise ValueError("備份檔格式錯誤：內容需為陣列（list）")
                st.session_state.events = raw if raw else [asdict(LunarEvent())]
                st.success(f"已還原 {len(st.session_state.events)} 筆事項。")
                st.rerun()
            except Exception as e:
                st.error(f"還原失敗：{e}")

st.divider()
st.subheader("下載 .ics")
st.caption("下載後把檔案傳到 iPhone（AirDrop / iCloud Drive / Email），點開即可加入行事曆。")

try:
    events_dc = [LunarEvent(**e) for e in st.session_state.events]
    ics_text = build_ics(events_dc, int(start_year), int(years))
    st.download_button(
        "下載 lunar_events.ics",
        data=ics_text.encode("utf-8"),
        file_name="lunar_events.ics",
        mime="text/calendar",
        use_container_width=True
    )
except Exception as e:
    st.error(f"產生失敗：{e}")
