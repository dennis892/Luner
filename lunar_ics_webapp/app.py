\
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
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
    time: str = "09:00"               # HH:MM
    duration_minutes: int = 30
    alarm_minutes_before: int | None = 1440  # minutes; None = no alarm
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


def lunar_to_solar_date(year: int, lunar_month: int, lunar_day: int, is_leap_month: bool) -> datetime:
    ld = LunarDate(year, lunar_month, lunar_day, is_leap_month)
    d = ld.toSolarDate()
    return datetime(d.year, d.month, d.day, tzinfo=TZ)


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
            base = lunar_to_solar_date(y, ev.lunar_month, ev.lunar_day, ev.is_leap_month)
            start_dt = base.replace(hour=h, minute=m, second=0)
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
                trigger = f"-PT{minutes}M"
                lines.append("BEGIN:VALARM")
                lines.append("ACTION:DISPLAY")
                lines.append(f"DESCRIPTION:{ics_escape(ev.title)}")
                lines.append(f"TRIGGER:{trigger}")
                lines.append("END:VALARM")

            lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


st.set_page_config(page_title="農曆行事曆提醒產生器", page_icon="🗓️", layout="wide")

st.title("🗓️ 農曆行事曆提醒產生器（不存伺服器）")
st.caption(
    "輸入農曆日期與提醒設定 → 產生未來 N 年的 .ics → 下載後匯入 iPhone 行事曆。"
    "本頁面不會把你的事項寫入資料庫；僅在你目前的瀏覽器 session 記憶體中暫存。"
)

if "events" not in st.session_state:
    st.session_state.events = [
        LunarEvent(
            title="媽祖生日",
            lunar_month=3,
            lunar_day=23,
            time="09:00",
            alarm_minutes_before=1440,
            duration_minutes=30,
            notes="準備供品/香燭"
        )
    ]

colA, colB, colC, colD = st.columns([1, 1, 1, 2])
with colA:
    start_year = st.number_input("起始西元年", min_value=1900, max_value=2200, value=datetime.now(TZ).year, step=1)
with colB:
    years = st.number_input("往後產生幾年", min_value=1, max_value=60, value=20, step=1)
with colC:
    calendar_name = st.text_input("匯入顯示名稱", value="農曆提醒")
with colD:
    st.write("")
    st.write("")
    if st.button("➕ 新增一筆事項", use_container_width=True):
        st.session_state.events.append(LunarEvent())

st.divider()

with st.expander("📦 匯入/匯出 JSON（本機檔案，不做伺服器保存）", expanded=False):
    left, right = st.columns(2)
    with left:
        st.subheader("匯出目前設定")
        export_json = json.dumps([asdict(e) for e in st.session_state.events], ensure_ascii=False, indent=2)
        st.download_button(
            "下載 events.json",
            data=export_json.encode("utf-8"),
            file_name="events.json",
            mime="application/json",
            use_container_width=True
        )
    with right:
        st.subheader("匯入 events.json")
        up = st.file_uploader("選擇 JSON 檔", type=["json"])
        if up is not None:
            try:
                raw = json.loads(up.getvalue().decode("utf-8"))
                loaded = [LunarEvent(**item) for item in raw]
                st.session_state.events = loaded if loaded else [LunarEvent()]
                st.success(f"已匯入 {len(st.session_state.events)} 筆事項。")
            except Exception as e:
                st.error(f"匯入失敗：{e}")

st.divider()

st.subheader("✍️ 事項清單（以農曆為主）")
for idx, ev in enumerate(list(st.session_state.events)):
    with st.container(border=True):
        row1 = st.columns([2, 1, 1, 1, 1, 1, 1])
        ev.title = row1[0].text_input("名稱", value=ev.title, key=f"title_{idx}")
        ev.lunar_month = row1[1].number_input("農曆月", min_value=1, max_value=12, value=int(ev.lunar_month), step=1, key=f"lm_{idx}")
        ev.lunar_day = row1[2].number_input("農曆日", min_value=1, max_value=30, value=int(ev.lunar_day), step=1, key=f"ld_{idx}")
        ev.is_leap_month = row1[3].checkbox("閏月", value=bool(ev.is_leap_month), key=f"leap_{idx}")
        ev.time = row1[4].text_input("時間 HH:MM", value=ev.time, key=f"time_{idx}")
        ev.duration_minutes = row1[5].number_input("時長(分)", min_value=1, max_value=1440, value=int(ev.duration_minutes), step=5, key=f"dur_{idx}")

        alarm_choice = row1[6].selectbox(
            "提醒",
            options=["無", "當下", "10 分鐘前", "30 分鐘前", "1 小時前", "3 小時前", "1 天前", "2 天前", "自訂(分鐘)"],
            index=6 if ev.alarm_minutes_before == 1440 else (
                7 if ev.alarm_minutes_before == 2880 else (
                    5 if ev.alarm_minutes_before == 180 else (
                        4 if ev.alarm_minutes_before == 60 else (
                            3 if ev.alarm_minutes_before == 30 else (
                                2 if ev.alarm_minutes_before == 10 else (
                                    1 if ev.alarm_minutes_before == 0 else (
                                        0 if ev.alarm_minutes_before is None else 8
                                    )
                                )
                            )
                        )
                    )
                )
            ),
            key=f"alarm_sel_{idx}"
        )

        row2 = st.columns([6, 1, 2])
        ev.notes = row2[0].text_input("備註（可空白）", value=ev.notes, key=f"notes_{idx}")

        if alarm_choice == "無":
            ev.alarm_minutes_before = None
        elif alarm_choice == "當下":
            ev.alarm_minutes_before = 0
        elif alarm_choice == "10 分鐘前":
            ev.alarm_minutes_before = 10
        elif alarm_choice == "30 分鐘前":
            ev.alarm_minutes_before = 30
        elif alarm_choice == "1 小時前":
            ev.alarm_minutes_before = 60
        elif alarm_choice == "3 小時前":
            ev.alarm_minutes_before = 180
        elif alarm_choice == "1 天前":
            ev.alarm_minutes_before = 1440
        elif alarm_choice == "2 天前":
            ev.alarm_minutes_before = 2880
        else:
            ev.alarm_minutes_before = int(row2[1].number_input(
                "自訂提前(分)", min_value=0, max_value=10080,
                value=int(ev.alarm_minutes_before or 60), step=5, key=f"alarm_custom_{idx}"
            ))

        if row2[2].button("🗑️ 刪除這筆", key=f"del_{idx}", use_container_width=True):
            st.session_state.events.pop(idx)
            st.rerun()

st.session_state.events = [e for e in st.session_state.events] or [LunarEvent()]

st.divider()

st.subheader("⬇️ 產生並下載 .ics")
left, right = st.columns([2, 1])
with left:
    st.info(
        "下載後把 .ics 傳到 iPhone（AirDrop / iCloud Drive / Email），點開即可『加入行事曆』。\n\n"
        "這裡採用『未來每一年都產生一筆事件』的方式，所以最穩、不會跑掉。"
    )

with right:
    try:
        ics_text = build_ics(st.session_state.events, int(start_year), int(years), calendar_name=calendar_name)
        st.download_button(
            "下載 lunar_events.ics",
            data=ics_text.encode("utf-8"),
            file_name="lunar_events.ics",
            mime="text/calendar",
            use_container_width=True
        )
        st.success("已就緒 ✅")
    except Exception as e:
        st.error(f"產生失敗：{e}")
