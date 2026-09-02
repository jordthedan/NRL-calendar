#!/usr/bin/env python3
"""Generate a subscribed Apple Calendar feed from the official NRL draw data."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

COMPETITION = 111
SYDNEY = ZoneInfo("Australia/Sydney")
OUT = Path(__file__).resolve().parents[1] / "nrl-calendar.ics"
USER_AGENT = "NRL-calendar/1.0 (+https://github.com/jordthedan/NRL-calendar)"


def get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def esc(value: object) -> str:
    return str(value or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def pick(d: dict, *paths, default=None):
    for path in paths:
        cur = d
        ok = True
        for key in path.split("."):
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if ok and cur not in (None, ""):
            return cur
    return default


def parse_dt(value: object) -> datetime | None:
    if not value:
        return None
    s = str(value).strip()
    # NRL commonly supplies an ISO timestamp. A trailing Z is UTC.
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=SYDNEY)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def fixture_key(f: dict, season: int, round_no: int, home: str, away: str) -> str:
    raw = pick(f, "matchId", "id", "fixtureId", "matchCentreUrl", default="")
    if raw:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(raw)).strip("-").lower()
        return f"nrl-{season}-{slug}@jordthedan.github.io"
    pair = re.sub(r"[^a-z0-9]+", "-", f"{home}-{away}".lower()).strip("-")
    return f"nrl-{season}-r{round_no}-{pair}@jordthedan.github.io"


def round_name(f: dict, round_no: int) -> str:
    name = pick(f, "roundTitle", "roundName", "round.name", default="")
    if name:
        return str(name)
    return {28: "Finals Week 1", 29: "Finals Week 2", 30: "Finals Week 3", 31: "Grand Final"}.get(round_no, f"Round {round_no}")


def fetch_round(season: int, round_no: int) -> list[dict]:
    qs = urllib.parse.urlencode({"competition": COMPETITION, "round": round_no, "season": season})
    data = get_json(f"https://www.nrl.com/draw/data?{qs}")
    if isinstance(data, dict):
        for key in ("fixtures", "matches", "data"):
            val = data.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict) and isinstance(val.get("fixtures"), list):
                return val["fixtures"]
    return data if isinstance(data, list) else []


def collect() -> list[dict]:
    now = datetime.now(SYDNEY)
    seasons = range(now.year - 1, now.year + 2)
    events = []
    seen = set()
    for season in seasons:
        for rnd in range(1, 32):
            try:
                fixtures = fetch_round(season, rnd)
            except Exception as exc:
                print(f"WARN {season} round {rnd}: {exc}")
                continue
            for f in fixtures:
                home = str(pick(f, "homeTeam.nickName", "homeTeam.nickname", "homeTeam.name", "home.name", default="TBC"))
                away = str(pick(f, "awayTeam.nickName", "awayTeam.nickname", "awayTeam.name", "away.name", default="TBC"))
                kickoff = parse_dt(pick(f, "clock.kickOffTimeLong", "kickOffTime", "startTime", "startDate"))
                if not kickoff:
                    continue
                uid = fixture_key(f, season, rnd, home, away)
                if uid in seen:
                    continue
                seen.add(uid)
                venue = str(pick(f, "venue.name", "venueName", "venue", default=""))
                match_url = str(pick(f, "matchCentreUrl", default=""))
                if match_url.startswith("/"):
                    match_url = "https://www.nrl.com" + match_url
                events.append({
                    "uid": uid, "season": season, "round": round_name(f, rnd),
                    "home": home, "away": away, "start": kickoff,
                    "end": kickoff + timedelta(hours=2), "venue": venue, "url": match_url,
                })
    return sorted(events, key=lambda x: x["start"])


def build_ics(events: list[dict]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Jordan//NRL Live Calendar//EN",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:NRL",
        "X-WR-TIMEZONE:Australia/Sydney", "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
    ]
    for e in events:
        desc = f"{e['round']} — {e['season']} NRL Telstra Premiership. Auto-updated from the NRL draw."
        lines += [
            "BEGIN:VEVENT", f"UID:{esc(e['uid'])}", f"DTSTAMP:{stamp}",
            f"LAST-MODIFIED:{stamp}", f"DTSTART:{e['start'].strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{e['end'].strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:{esc(e['home'])} vs {esc(e['away'])}",
            f"LOCATION:{esc(e['venue'])}", f"DESCRIPTION:{esc(desc)}",
        ]
        if e["url"]:
            lines.append(f"URL:{esc(e['url'])}")
        lines += [
            "BEGIN:VALARM", "TRIGGER:-PT30M", "ACTION:DISPLAY",
            f"DESCRIPTION:NRL starts in 30 minutes — {esc(e['home'])} vs {esc(e['away'])}",
            "END:VALARM", "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main():
    events = collect()
    if not events:
        raise SystemExit("No NRL fixtures returned; refusing to overwrite the existing calendar.")
    OUT.write_text(build_ics(events), encoding="utf-8", newline="")
    print(f"Wrote {len(events)} fixtures to {OUT}")


if __name__ == "__main__":
    main()
