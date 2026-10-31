# -*- coding: utf-8 -*-
"""공개 데이터 → 10주제 × 5문항.

**모든 숫자는 raw/ 의 원본에서 계산합니다.** 지어낸 값이 하나도 없어야 합니다.
결과는 앱이 읽는 topics/*.json 과, 사람이 읽는 tools/정답지.md 로 나갑니다.

정답지와 이 스크립트는 .vercelignore 에 들어 있어 **배포되지 않습니다.**
공개 URL 에 정답지가 올라가면 게임이 성립하지 않습니다.

실행 (저장소 최상위에서):
    python tools/build_topics.py
"""
from __future__ import annotations

import csv
import io
import json
import sys
import unicodedata
import datetime as dt
from collections import Counter
from pathlib import Path
from statistics import mean

# 윈도우 콘솔(cp949)은 이모지 · 기호를 못 찍고 멈춘다. 출력만 UTF-8 로 맞춘다
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

HERE = Path(__file__).resolve().parent          # tools/
APP = HERE.parent                                # 저장소 최상위 = 배포되는 곳
RAW = APP / "data" / "raw"
OUT = APP / "topics"

TOPICS: list[dict] = []


def load_json(name):
    return json.load(io.open(RAW / name, encoding="utf-8"))


def load_csv(name):
    return list(csv.DictReader(io.open(RAW / name, encoding="utf-8")))


# World Bank·OWID 응답에는 '유럽연합' '고소득국' 같은 **집계치**가 섞여 있다.
# 그대로 순위를 매기면 나라와 대륙을 한 줄에 놓고 세는 셈이 된다.
REAL = {x["id"] for x in load_json("wb_countries.json")[1]
        if x["region"]["id"] != "NA"}


def wb_countries(rows, year):
    """그 해의 실제 국가 값만 남긴다 (집계치 제외)."""
    return {r["country"]["value"]: r["value"] for r in rows
            if int(r["date"]) == year and r["countryiso3code"] in REAL}


def owid_countries(rows, year, col):
    """OWID 도 마찬가지. code 가 비었거나 OWID_ 로 시작하면 집계치다."""
    return {r["entity"]: float(r[col]) for r in rows
            if int(r["year"]) == year and r["code"]
            and not r["code"].startswith("OWID")}


def topic(tid, emoji, title, blurb, source, source_url, questions, caveat=""):
    """caveat = 이 데이터를 믿을 때의 한계. 앱 화면에도 그대로 나간다.

    출처가 다르면 같은 '서울 기온'도 값이 다르다. 그 사실을 감추지 않는다.
    """
    TOPICS.append({"id": tid, "emoji": emoji, "title": title, "blurb": blurb,
                   "source": source, "source_url": source_url,
                   "caveat": caveat, "questions": questions})


def slider(qid, text, answer, unit, lo, hi, step, basis, why):
    return {"id": qid, "type": "slider", "text": text, "unit": unit,
            "min": lo, "max": hi, "step": step,
            "answer": round(float(answer), 1), "basis": basis, "why": why}


def choice(qid, text, options, answer, basis, why):
    assert answer in options, f"{qid}: 정답이 선택지에 없습니다"
    return {"id": qid, "type": "choice", "text": text, "options": options,
            "answer": answer, "basis": basis, "why": why}


# ════════════════════════════════════════════════════════════════
# 파일 쓰기 — 맨 아래가 아니라 여기 둔다. 축구만 다시 계산할 때(--soccer)는
# 축구 주제를 만든 직후 이 함수를 부르고 끝내서, 아래 10주제는 계산하지 않는다
# ════════════════════════════════════════════════════════════════
def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fresh = {}
    for t in TOPICS:
        assert len(t["questions"]) == 5, f"{t['id']}: 문항이 5개가 아닙니다"
        pack = {k: t[k] for k in ("id", "emoji", "title", "blurb",
                                  "source", "source_url", "caveat")}
        pack["questions"] = t["questions"]
        io.open(OUT / f"{t['id']}.json", "w", encoding="utf-8").write(
            json.dumps(pack, ensure_ascii=False, indent=2))
        fresh[t["id"]] = {k: t[k] for k in ("id", "emoji", "title", "blurb",
                                            "source")}

    # 제목·부제는 화면을 바꾸며 고친 값을 지킨다 (2장에서 내 제목으로 바꾼다).
    # 다시 계산해도 내 제목이 «감 테스트»로 돌아가지 않게, 있던 값을 읽어 쓴다
    old = {}
    if (APP / "topics.json").exists():
        try:
            old = json.load(io.open(APP / "topics.json", encoding="utf-8"))
        except ValueError:
            old = {}
    # 목록 순서도 지킨다. 같은 id 는 새 값으로 바꾸고, 처음 보는 주제는 뒤에 붙인다.
    # 일부 주제만 다시 계산해도(--soccer) 나머지 주제가 목록에서 빠지지 않는다
    index = [fresh.pop(x["id"], x) for x in old.get("topics", [])] \
        + list(fresh.values())
    io.open(APP / "topics.json", "w", encoding="utf-8").write(json.dumps({
        "title": old.get("title", "감 테스트"),
        "subtitle": old.get("subtitle", "숫자에 대한 당신의 감은 몇 점입니까"),
        # 등급·문구는 여기서 고칩니다. 코드를 건드릴 일이 아닙니다
        "grades": [
            {"min": 90, "name": "촉이 데이터급", "emoji": "🎯"},
            {"min": 70, "name": "감이 좋은 편", "emoji": "📊"},
            {"min": 50, "name": "보통의 감각", "emoji": "🙂"},
            {"min": 30, "name": "느낌대로 삽니다", "emoji": "🎲"},
            {"min": 0, "name": "감은 접어두시죠", "emoji": "🙈"},
        ],
        "reactions_choice": {"hit": "맞히셨습니다", "miss": "다들 그렇게 찍습니다"},
        "reactions": [
            {"max": 5, "text": "촉이 좋으시네요"},
            {"max": 20, "text": "비슷하게 보셨습니다"},
            {"max": 60, "text": "음…"},
            {"max": 999, "text": "꽤 멀리 가셨습니다"},
        ],
        "topics": index,
    }, ensure_ascii=False, indent=2))

    # 사람이 읽는 정답지. 이번에 계산하지 않은 주제도 빠지지 않게
    # 목록의 모든 주제를 topics/ 의 파일에서 읽어 쓴다
    packs = [json.load(io.open(OUT / f"{x['id']}.json", encoding="utf-8"))
             for x in index]
    md = [f"# 문항 정답지 — {len(packs)}주제 "
          f"{sum(len(t['questions']) for t in packs)}문항", "",
          "> 모든 값은 `data/raw/` 의 원본에서 `tools/build_topics.py` 가 계산합니다.", ""]
    for t in packs:
        md += [f"## {t['emoji']} {t['title']}", "",
               f"- 출처: {t['source']} · {t['source_url']}"]
        if t["caveat"]:
            md += [f"- **한계** {t['caveat']}"]
        md += [""]
        for q in t["questions"]:
            a = f"{q['answer']}{q.get('unit', '')}" if q["type"] == "slider" \
                else q["answer"]
            md += [f"**{q['text']}**", "",
                   f"- 정답 **{a}**", f"- 근거 {q['basis']}",
                   f"- 왜 틀리나 {q['why']}", ""]
    io.open(HERE / "정답지.md", "w", encoding="utf-8").write("\n".join(md))

    print(f"주제 {len(TOPICS)}개 · 문항 {sum(len(t['questions']) for t in TOPICS)}개")
    for t in TOPICS:
        print(f"\n{t['emoji']} {t['title']}  ({t['source']})")
        for q in t["questions"]:
            a = f"{q['answer']}{q.get('unit', '')}" if q["type"] == "slider" \
                else q["answer"]
            print(f"    [{q['type'][:6]:<6}] {q['text'][:44]:<44} → {a}")


# ════════════════════════════════════════════════════════════════
# 축구 — "축구, 얼마나 좋아하니?" 6주제 × 5문항
# 원본: engsoccerdata(잉글랜드·스페인 리그 경기 결과 · 승점 감점)
#       openfootball worldcup.json(월드컵 전 경기 · 득점자)
#       UEFA 경기 API(유러피언컵·챔스 전 경기 · 득점자)
# 받기: python tools/fetch_all.py soccer_
# 축구만 다시 계산 (다른 주제는 읽지도 쓰지도 않는다):
#     python tools/build_topics.py --soccer
# ════════════════════════════════════════════════════════════════
def ranged(qid, text, answer, unit, lo, hi, step, basis, why):
    """slider 와 같다. 범위는 손으로 정하므로, 계산한 정답이 범위 밖이면 멈춘다."""
    assert lo <= answer <= hi, f"{qid}: 정답 {answer} 이(가) 범위 {lo}~{hi} 밖입니다"
    return slider(qid, text, answer, unit, lo, hi, step, basis, why)


def season_name(start):
    """시작 연도 → '1998-99'."""
    return f"{start}-{(start + 1) % 100:02d}"


def table(games, win_pts, deduct=None):
    """경기 결과 → 팀별 승·무·패·득점·실점·승점."""
    t = {}
    for r in games:
        hg, vg = int(r["hgoal"]), int(r["vgoal"])
        for team, f, a in ((r["home"], hg, vg), (r["visitor"], vg, hg)):
            s = t.setdefault(team, {"w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0})
            s["gf"] += f
            s["ga"] += a
            if f > a:
                s["w"] += 1
                s["pts"] += win_pts
            elif f == a:
                s["d"] += 1
                s["pts"] += 1
            else:
                s["l"] += 1
    for team, n in (deduct or {}).items():
        if team in t:
            t[team]["pts"] -= n
    return t


# ── 리그 원본 ────────────────────────────────────────────────────
# 원본에는 경기 결과만 있고 순위표가 없다. 순위는 그 시즌 규칙대로 다시 계산한다.
#   승점  잉글랜드는 1981-82, 스페인은 1995-96 시즌부터 승리 3점 (그 전은 2점)
#   동률  잉글랜드: 1975-76 까지 골 평균(득점÷실점), 그 뒤로 골 득실 → 다득점
#         스페인: 맞대결 성적(승점 → 골 득실) → 전체 골 득실 → 다득점
# 스페인 규칙은 승점 동률이던 1위 시즌들을 Wikidata 의 시즌 우승팀과 맞춰 보고 정했다.
ENG, ESP, DED = {}, {}, {}
for r in load_csv("soccer_england.csv"):
    if r["tier"] == "1":
        ENG.setdefault(int(r["Season"]), []).append(r)
# 1986-87 라리가는 정규 리그 뒤 2차 리그(phase2)가 이어졌고 승점도 이어졌다. 둘 다 넣는다
for r in load_csv("soccer_spain.csv"):
    ESP.setdefault(int(r["Season"]), []).append(r)
# 감점 목록은 1부 리그 기준 2009-10 시즌에서 끝난다. 그 뒤의 감점은 반영되지 않는다
for r in load_csv("soccer_deductions.csv"):
    if r["tier"] == "1" and r["country"] == "England":
        DED.setdefault(int(r["Season"]), {})[r["team"]] = int(r["deduction"])
DED_LAST = max(DED)

# engsoccerdata 에 없는 시즌은 football.json 에서 채운다.
# 잉글랜드 2022-23 은 통째로 빠져 있고, 2025-26 은 두 리그 모두 아직 반영 전이다.
# football.json 의 팀 이름은 대개 뒤의 " FC" 만 다르다. 그렇지 않은 팀만 여기 적는다
FJ_NAMES = {
    "Sunderland AFC": "Sunderland",
    "Athletic Club": "Athletic Bilbao",
    "Club Atlético de Madrid": "Atletico Madrid",
    "Deportivo Alavés": "CD Alaves",
    "RC Celta de Vigo": "Celta Vigo",
    "RCD Espanyol de Barcelona": "Espanyol Barcelona",
    "Rayo Vallecano de Madrid": "Rayo Vallecano",
    "Real Betis Balompié": "Real Betis",
    "Real Madrid CF": "Real Madrid",
    "Real Sociedad de Fútbol": "Real Sociedad",
}


def fj_season(file, season, league):
    """football.json 한 시즌 → engsoccerdata 와 같은 모양의 줄. 이름이 안 맞거나 결과가 빠지면 멈춘다."""
    known = {r["home"] for rows in league.values() for r in rows}
    out = []
    for m in load_json(file)["matches"]:
        s = m["score"]
        ft = s if isinstance(s, list) else s["ft"]
        teams = []
        for n in (m["team1"], m["team2"]):
            n = FJ_NAMES.get(n, n)
            n = n if n in known else n.removesuffix(" FC")
            assert n in known, f"{file}: '{n}' 를 원본 표기와 맞추지 못했습니다"
            teams.append(n)
        out.append({"Season": str(season), "Date": m["date"], "home": teams[0],
                    "visitor": teams[1], "hgoal": ft[0], "vgoal": ft[1],
                    "FT": f"{ft[0]}-{ft[1]}", "tier": "1", "round": "league"})
    n_teams = len({r["home"] for r in out})
    assert len(out) == n_teams * (n_teams - 1), f"{file}: 경기가 모자랍니다"
    return out


for season, file, league in ((2022, "soccer_en1_2022.json", ENG),
                             (2025, "soccer_en1_2025.json", ENG),
                             (2025, "soccer_es1_2025.json", ESP)):
    if season not in league:
        league[season] = fj_season(file, season, league)
ENG_LAST, ESP_FIRST, ESP_LAST = max(ENG), min(ESP), max(ESP)
# 전쟁으로 리그가 멈춘 시즌 말고는 빠진 시즌이 없어야 한다
assert all(s in ENG for s in range(1946, ENG_LAST + 1)), "잉글랜드 원본에 빠진 시즌이 있습니다"
assert all(s in ESP for s in range(1939, ESP_LAST + 1)), "스페인 원본에 빠진 시즌이 있습니다"


def eng_table(season):
    return table(ENG[season], 3 if season >= 1981 else 2, DED.get(season))


def eng_champion(season):
    t = eng_table(season)

    def rank(team):
        s = t[team]
        if season <= 1975:
            tie = s["gf"] / s["ga"] if s["ga"] else float("inf")
        else:
            tie = s["gf"] - s["ga"]
        return (s["pts"], tie, s["gf"])
    return max(t, key=rank)


def esp_table(season):
    return table(ESP[season], 3 if season >= 1995 else 2)


def esp_champion(season):
    t = esp_table(season)
    top = max(s["pts"] for s in t.values())
    tied = [k for k, s in t.items() if s["pts"] == top]
    h2h = table([r for r in ESP[season]
                 if r["home"] in tied and r["visitor"] in tied],
                3 if season >= 1995 else 2)

    def rank(team):
        m, s = h2h.get(team, {"pts": 0, "gf": 0, "ga": 0}), t[team]
        return (m["pts"], m["gf"] - m["ga"], s["gf"] - s["ga"], s["gf"])
    return max(tied, key=rank)


def record(rows, team):
    """한 팀의 리그 성적 문자열."""
    s = rows[team]
    return f"{s['w'] + s['d'] + s['l']}경기 {s['w']}승 {s['d']}무 {s['l']}패"


# ── 월드컵 원본 ──────────────────────────────────────────────────
WC = {int(p.stem[-4:]): load_json(p.name)["matches"]
      for p in sorted(RAW.glob("soccer_wc_*.json"))}
WC_FIRST, WC_LAST = min(WC), max(WC)
KOR = "South Korea"


def wc_score(m):
    """정규 시간 + 연장까지의 스코어. 승부차기는 넣지 않는다.

    원본의 score 는 [1, 0] 같은 목록이거나 {ft, et, p} 사전이다. 연장을 했으면 et 가 최종이다.
    """
    s = m["score"]
    return s if isinstance(s, list) else (s.get("et") or s["ft"])


def wc_winner(m):
    """승부차기까지 따진 승자. 비겼으면 None."""
    a, b = wc_score(m)
    s = m["score"]
    if a == b and isinstance(s, dict) and s.get("p"):
        a, b = s["p"]
    return m["team1"] if a > b else m["team2"] if b > a else None


def wc_champion(year):
    finals = [m for m in WC[year] if m["round"] == "Final"]
    if finals:
        assert len(finals) == 1, f"{year}: 결승이 {len(finals)}경기입니다"
        return wc_winner(finals[0])
    # 1950 년은 결승전 없이 네 팀 결선 리그로 우승팀을 정했다
    last = [{"home": m["team1"], "visitor": m["team2"],
             "hgoal": wc_score(m)[0], "vgoal": wc_score(m)[1]}
            for m in WC[year] if m["round"] == "Final Round"]
    assert last, f"{year}: 결승도 결선 리그도 없습니다"
    t = table(last, 2)
    return max(t, key=lambda k: t[k]["pts"])


def wc_goals(years):
    """선수별 골. 자책골은 뺀다. 승부차기는 원본에서 따로 적혀 있어 들어오지 않는다.

    원본에는 같은 선수가 'Olivier Giroud' · 'Olivier GIROUD' 처럼 대소문자만 다르게
    적힌 경우가 있다. 대소문자·악센트를 무시하고 합치고, 가장 많이 쓴 표기로 보여 준다.
    """
    c, spell = Counter(), {}
    for y in years:
        for m in WC[y]:
            for g in m.get("goals1", []) + m.get("goals2", []):
                if not g.get("owngoal"):
                    k = unicodedata.normalize("NFKD", g["name"]).encode(
                        "ascii", "ignore").decode().casefold()
                    c[k] += 1
                    spell.setdefault(k, Counter())[g["name"]] += 1
    return Counter({spell[k].most_common(1)[0][0]: n for k, n in c.items()})


# ── 챔스 원본 ────────────────────────────────────────────────────
# 파일 이름의 연도 = 시즌이 끝나는 해 (fetch_all.py 에서 그렇게 맞췄다)
UCL = {int(p.stem[-4:]): load_json(p.name)
       for p in sorted(RAW.glob("soccer_ucl_*.json"))}
UCL_FIRST, UCL_LAST = min(UCL), max(UCL)


def ucl_season(end):
    return season_name(end - 1)


def main_draw(end, m):
    """본선 경기인가. 예선(QUALIFYING)은 뺀다.
    단, 1991-92 시즌까지의 유러피언컵은 예비 라운드까지 전 라운드를 센다."""
    # 열리지 않은 경기 하나(2021-22 예선 플레이오프)에는 competitionPhase 가 없다.
    # 라운드에 같은 구분이 있어 그것을 대신 쓴다
    phase = m.get("competitionPhase", m["round"].get("phase"))
    return end <= 1992 or phase == "TOURNAMENT"


UCL_GOALS = []          # (끝 연도, 선수 id, 이름, 국적) — 본선 골 하나에 한 줄
UCL_NO_SCORER = []      # 득점자가 비어 있는 본선 골 — 골 하나에 그 시즌 끝 연도 하나
# 끝까지 치른 경기(FINISHED)의 골만 센다. 취소·중단·미개최 경기에도 득점자가 적힌 것이 있다
UCL_SKIPPED = Counter(m.get("status") for ms in UCL.values() for m in ms
                      if m.get("status") != "FINISHED")
for end, ms in UCL.items():
    for m in ms:
        if not main_draw(end, m) or m.get("status") != "FINISHED":
            continue
        for g in (m.get("playerEvents") or {}).get("scorers", []):
            if g["goalType"] == "OWN":
                continue
            p = g.get("player")
            if not p:
                UCL_NO_SCORER.append(end)
                continue
            UCL_GOALS.append((end, p["id"], p["internationalName"], p.get("countryCode")))


def ucl_player(name):
    """이름 → 선수 id. 같은 이름이 둘이면 멈춘다."""
    ids = {pid for _, pid, n, _ in UCL_GOALS if n == name}
    assert len(ids) == 1, f"{name}: 선수 id 가 {len(ids)}개입니다"
    return ids.pop()


def ucl_final(end):
    fs = sorted((m for m in UCL[end] if m["round"]["metaData"]["type"] == "FINAL"),
                key=lambda m: m["kickOffTime"]["date"])
    assert fs, f"{ucl_season(end)}: 결승이 없습니다"
    return fs[-1]       # 1973-74 은 비겨서 재경기를 했다. 마지막 경기가 우승을 정했다


def ucl_teams(m):
    return m["homeTeam"]["internationalName"], m["awayTeam"]["internationalName"]


def ucl_winner(m):
    s = m["score"]
    h, a = s["total"]["home"], s["total"]["away"]
    if h == a and s.get("penalty"):
        h, a = s["penalty"]["home"], s["penalty"]["away"]
    return ucl_teams(m)[0] if h > a else ucl_teams(m)[1]


FINALS = {end: ucl_final(end) for end in UCL}
UCL_SPAN = f"{ucl_season(UCL_FIRST)}~{ucl_season(UCL_LAST)}"


def ucl_goals_of(pid):
    return sum(1 for _, p, _, _ in UCL_GOALS if p == pid)


# ── 축구 1. 맨유 ─────────────────────────────────────────────────
MU = "Manchester United"
fergie = [s for s in range(1986, 2013) if eng_champion(s) == MU]
t_9899 = eng_table(1998)
mu_finals = [end for end, m in FINALS.items() if "Man Utd" in ucl_teams(m)]
mu_won = [end for end in mu_finals if ucl_winner(FINALS[end]) == "Man Utd"]
rooney = ucl_goals_of(ucl_player("Wayne Rooney"))
park = ucl_goals_of(ucl_player("Park Ji-Sung"))

topic(
    "soccer-manutd", "👹", "맨유",
    "퍼거슨의 시대부터 박지성까지",
    "engsoccerdata · UEFA 경기 기록", "https://github.com/jalapic/engsoccerdata",
    [
        ranged("mu1", "퍼거슨 감독이 맨유를 이끈 1986-87~2012-13 시즌, 맨유의 1부 리그 "
                      "우승은 몇 번이었을까요?",
               len(fergie), "회", 0, 27, 1,
               f"1986-87~2012-13 시즌 잉글랜드 1부 리그 경기 결과로 시즌마다 순위를 "
               f"다시 계산해(그 시즌 승점·동률 규칙, 감점 목록 반영) 맨유가 1위인 시즌을 "
               f"세면 {len(fergie)}회입니다",
               f"'퍼거슨 = 우승'으로 기억하지만, 부임 후 첫 리그 우승은 "
               f"{season_name(fergie[0])} 시즌에야 나왔습니다."),
        ranged("mu2", "트레블을 달성한 1998-99 시즌, 맨유는 리그에서 몇 번 졌을까요?",
               t_9899[MU]["l"], "패", 0, 15, 1,
               f"1998-99 시즌 잉글랜드 1부 리그에서 맨유가 치른 경기 결과를 세면 "
               f"{record(t_9899, MU)}입니다",
               "트레블이라는 결과가 시즌 전체를 완벽했던 것처럼 기억하게 만듭니다."),
        ranged("mu3", f"{UCL_SPAN} 시즌 유러피언컵·챔피언스리그에서 맨유가 결승에 "
                      "오른 횟수는?",
               len(mu_finals), "회", 0, 10, 1,
               f"{UCL_SPAN} 시즌 UEFA 결승 경기 기록에서 맨유가 나온 결승을 세면 "
               f"{len(mu_finals)}회({', '.join(ucl_season(e) for e in mu_finals)})입니다",
               f"우승한 결승({', '.join(ucl_season(e) for e in mu_won)})은 오래 남지만, "
               "진 결승은 금방 잊힙니다."),
        ranged("mu4", f"{UCL_SPAN} 시즌, 웨인 루니가 챔피언스리그 본선에서 넣은 골은 "
                      "모두 몇 골일까요?",
               rooney, "골", 0, 60, 1,
               f"{UCL_SPAN} 시즌 UEFA 경기 기록에서 예선을 뺀 본선 경기의 루니 득점"
               f"(자책골 제외)을 세면 {rooney}골입니다",
               "챔스는 한 시즌 경기 수가 리그보다 훨씬 적습니다. 리그 골 감각으로 "
               "짐작하면 크게 빗나갑니다."),
        ranged("mu5", f"{UCL_SPAN} 시즌, 박지성이 챔피언스리그 본선에서 넣은 골은 "
                      "모두 몇 골일까요? (맨유 이전 소속팀 포함)",
               park, "골", 0, 20, 1,
               f"{UCL_SPAN} 시즌 UEFA 경기 기록에서 예선을 뺀 본선 경기의 박지성 득점"
               f"(자책골 제외)을 소속팀 구분 없이 세면 {park}골입니다",
               "수비 가담으로 기억되는 선수라 골 수는 감으로 잡기 어렵습니다."),
    ],
    caveat="리그 순위는 원본의 경기 결과로 다시 계산한 값입니다. 챔스 골은 UEFA "
           "기록에서 예선을 뺀 본선 경기만 셉니다.")

# ── 축구 2. 프리미어리그 ─────────────────────────────────────────
EPL = [s for s in range(1992, ENG_LAST + 1)]
EPL_SPAN = f"{season_name(EPL[0])}~{season_name(EPL[-1])}"
epl_champs = {s: eng_champion(s) for s in EPL}
epl_pts = max(((t["pts"], team, s) for s in EPL
               for team, t in eng_table(s).items()))
epl_goals = max(int(r["hgoal"]) + int(r["vgoal"]) for s in EPL for r in ENG[s])
epl_goal_games = [r for s in EPL for r in ENG[s]
                  if int(r["hgoal"]) + int(r["vgoal"]) == epl_goals]
t_0304, t_1516 = eng_table(2003), eng_table(2015)

topic(
    "soccer-epl", "🦁", "프리미어리그",
    f"{EPL_SPAN}, {len(EPL)}시즌의 기록",
    "engsoccerdata · football.json", "https://github.com/jalapic/engsoccerdata",
    [
        ranged("epl1", f"{EPL_SPAN} 시즌 프리미어리그에서 한 번이라도 우승한 클럽은 "
                       "몇 곳일까요?",
               len(set(epl_champs.values())), "곳", 1, 15, 1,
               f"{EPL_SPAN} 시즌 순위를 경기 결과로 다시 계산해 1위 클럽을 중복 없이 "
               f"세면 {len(set(epl_champs.values()))}곳"
               f"({', '.join(sorted(set(epl_champs.values())))})입니다",
               "늘 상위권인 클럽과 실제로 우승한 클럽은 다릅니다."),
        ranged("epl2", f"{EPL_SPAN} 프리미어리그 한 시즌 최다 승점은?",
               epl_pts[0], "점", 70, 110, 1,
               f"{EPL_SPAN} 시즌마다 팀별 승점(승리 3점, {season_name(DED_LAST)}까지의 "
               f"감점 반영)을 계산해 "
               f"가장 높은 값은 {epl_pts[1]}의 {season_name(epl_pts[2])} 시즌 "
               f"{epl_pts[0]}점입니다",
               "38경기 시즌의 만점은 114점입니다. 상한을 알고 나면 감이 달라집니다."),
        ranged("epl3", "무패 우승을 한 2003-04 시즌, 아스널은 리그에서 몇 번 "
                       "비겼을까요?",
               t_0304["Arsenal"]["d"], "무", 0, 20, 1,
               f"2003-04 시즌 프리미어리그에서 아스널이 치른 경기 결과를 세면 "
               f"{record(t_0304, 'Arsenal')}입니다",
               "'무패'가 '거의 다 이겼다'로 들립니다. 지지 않은 것과 이긴 것은 "
               "다릅니다."),
        ranged("epl4", f"{EPL_SPAN} 프리미어리그 한 경기에서 나온 최다 골"
                       "(양 팀 합계)은?",
               epl_goals, "골", 5, 15, 1,
               f"{EPL_SPAN} 시즌 모든 경기의 양 팀 골 합계 중 최댓값은 {epl_goals}골이고, "
               f"그런 경기는 {len(epl_goal_games)}경기"
               f"({'; '.join(r['home'] + ' ' + r['FT'] + ' ' + r['visitor'] + ' ' + r['Date'][:4] for r in epl_goal_games)})입니다",
               "기억에 남는 대승 스코어가 기준점이 되어 상한을 낮게 잡기 쉽습니다."),
        ranged("epl5", "기적의 우승을 한 2015-16 시즌, 레스터 시티는 리그에서 몇 번 "
                       "졌을까요?",
               t_1516["Leicester City"]["l"], "패", 0, 15, 1,
               f"2015-16 시즌 프리미어리그에서 레스터 시티가 치른 경기 결과를 세면 "
               f"{record(t_1516, 'Leicester City')}입니다",
               "'기적'이라는 말 때문에 아슬아슬하게 우승했을 거라고 짐작하기 쉽습니다."),
    ],
    caveat="순위와 승점은 원본의 경기 결과로 다시 계산한 값입니다. 승점 감점은 "
           f"engsoccerdata 감점 목록이 끝나는 {season_name(DED_LAST)} 시즌까지만 "
           "반영했습니다(이후 감점은 우승팀·최다 승점과 무관). engsoccerdata 에 없는 "
           "2022-23 · 2025-26 시즌은 openfootball football.json 으로 채웠습니다. "
           "1992-93~1994-95 시즌은 팀당 42경기였습니다.")

# ── 축구 3. 라리가 ───────────────────────────────────────────────
RM, FCB = "Real Madrid", "FC Barcelona"
LIGA_SPAN = f"{season_name(ESP_FIRST)}~{season_name(ESP_LAST)}"
rm_titles = [s for s in ESP if esp_champion(s) == RM]
liga_rows = [(t["pts"], t["gf"], team, s) for s in ESP
             for team, t in esp_table(s).items()]
liga_pts = max(r[0] for r in liga_rows)
liga_pts_by = [r for r in liga_rows if r[0] == liga_pts]
liga_gf = max(r[1] for r in liga_rows)
liga_gf_by = [r for r in liga_rows if r[1] == liga_gf]
# 1986-87 2차 리그(phase2)의 맞대결도 넣는다 — 승점이 이어진 같은 시즌 리그로 본다
clasico = [r for s in ESP for r in ESP[s] if {r["home"], r["visitor"]} == {RM, FCB}]
clasico_p2 = sum(1 for r in clasico if r.get("round") == "phase2")
cl_rm = sum(1 for r in clasico
            if (int(r["hgoal"]) - int(r["vgoal"])) * (1 if r["home"] == RM else -1) > 0)
cl_d = sum(1 for r in clasico if r["hgoal"] == r["vgoal"])
liga_margin = max(abs(int(r["hgoal"]) - int(r["vgoal"])) for s in ESP for r in ESP[s])
liga_margin_games = [r for s in ESP for r in ESP[s]
                     if abs(int(r["hgoal"]) - int(r["vgoal"])) == liga_margin]

topic(
    "soccer-laliga", "🇪🇸", "라리가",
    f"{LIGA_SPAN}, 스페인 1부 리그의 모든 경기",
    "engsoccerdata · football.json", "https://github.com/jalapic/engsoccerdata",
    [
        ranged("liga1", f"{LIGA_SPAN} 시즌 레알 마드리드의 라리가 우승은 몇 번일까요?",
               len(rm_titles), "회", 10, 45, 1,
               f"{LIGA_SPAN} 시즌 라리가 경기 결과로 시즌마다 순위를 다시 계산해"
               f"(승점 동률은 맞대결 성적 → 골 득실) 레알 마드리드가 1위인 시즌을 세면 "
               f"{len(rm_titles)}회입니다",
               "챔피언스리그 우승 횟수와 섞여서 기억이 흐려지기 쉽습니다."),
        ranged("liga2", f"{LIGA_SPAN} 라리가 한 시즌 최다 승점은? "
                        "(그 시즌 승점 규칙 그대로)",
               liga_pts, "점", 70, 110, 1,
               f"{LIGA_SPAN} 시즌마다 그 시즌 규칙(1994-95까지 승리 2점, 이후 3점)으로 "
               f"팀별 승점을 계산해 가장 높은 값은 {liga_pts}점"
               f"({', '.join(f'{r[2]} {season_name(r[3])}' for r in liga_pts_by)})입니다",
               "EPL 기록과 비교하며 짐작하게 되는데, 리그마다 독주의 정도가 다릅니다."),
        ranged("liga3", f"{LIGA_SPAN} 라리가 한 시즌 팀 최다 득점은?",
               liga_gf, "골", 80, 130, 1,
               f"{LIGA_SPAN} 시즌마다 팀별 리그 득점을 더해 가장 많은 값은 {liga_gf}골"
               f"({', '.join(f'{r[2]} {season_name(r[3])}' for r in liga_gf_by)})입니다",
               "한 경기 평균 3골이면 38경기에 114골입니다. 경기당으로 나눠 보면 감이 "
               "달라집니다."),
        ranged("liga4", f"{LIGA_SPAN} 시즌, 레알 마드리드와 바르셀로나의 라리가 맞대결"
                        "(엘 클라시코)은 몇 번 있었을까요? (1986-87 2차 리그 포함, "
                        "컵 대회 제외)",
               len(clasico), "경기", 100, 250, 1,
               f"{LIGA_SPAN} 시즌 라리가 경기(1986-87 2차 리그 {clasico_p2}경기 포함) 중 "
               f"두 팀이 만난 경기를 세면 {len(clasico)}경기(레알 {cl_rm}승 · {cl_d}무 · "
               f"바르사 {len(clasico) - cl_rm - cl_d}승)입니다",
               "한 시즌 두 번씩이라는 건 알아도, 그게 몇 시즌 쌓였는지는 잘 세지 "
               "않습니다."),
        ranged("liga5", f"{LIGA_SPAN} 라리가 한 경기 최다 점수 차는 몇 골일까요?",
               liga_margin, "골", 3, 15, 1,
               f"{LIGA_SPAN} 시즌 라리가 모든 경기의 점수 차 중 가장 큰 값은 "
               f"{liga_margin}골"
               f"({'; '.join(r['home'] + ' ' + r['FT'] + ' ' + r['visitor'] + ' ' + season_name(int(r['Season'])) for r in liga_margin_games)})입니다",
               "요즘 경기만 떠올리면 상한을 낮게 잡게 됩니다. 기록은 리그 초창기에도 "
               "있습니다."),
    ],
    caveat="순위는 원본의 경기 결과로 다시 계산한 값이고, 승점이 같으면 맞대결 "
           "성적 → 골 득실로 가렸습니다. 1994-95 시즌까지는 승리가 2점이라 승점 "
           "기록은 그 시즌 규칙 그대로입니다. 1986-87 시즌은 정규 리그 뒤 2차 리그까지 "
           "한 시즌으로 셉니다. engsoccerdata 에 없는 2025-26 시즌은 openfootball "
           "football.json 으로 채웠습니다. 원본의 1979-80 시즌에는 말라가 대 살라망카 "
           "경기가 빠져 있고, 말라가 대 알메리아 경기는 몰수 판정 스코어(1-0)로 "
           "들어 있습니다.")

# ── 축구 4. 월드컵 ───────────────────────────────────────────────
WC_SPAN = f"{WC_FIRST}~{WC_LAST}년"
champs = {y: wc_champion(y) for y in WC}
bra = [y for y, c in champs.items() if c == "Brazil"]
career = wc_goals(WC)
top_career = max(career.values())
by_cup = [(n, name, y) for y in WC for name, n in wc_goals([y]).items()]
top_cup = max(n for n, _, _ in by_cup)
wc_tot = max(sum(wc_score(m)) for y in WC for m in WC[y])
wc_tot_games = [(y, m) for y in WC for m in WC[y] if sum(wc_score(m)) == wc_tot]

topic(
    "soccer-worldcup", "🏆", "월드컵",
    f"{WC_SPAN}, {len(WC)}개 대회의 모든 경기",
    "openfootball worldcup.json", "https://github.com/openfootball/worldcup.json",
    [
        ranged("wc1", f"{WC_SPAN} 월드컵에서 브라질은 몇 번 우승했을까요?",
               len(bra), "회", 0, 8, 1,
               f"{WC_SPAN} {len(WC)}개 대회에서 결승 승자(1950년은 결선 리그 1위)를 "
               f"세면 브라질은 {len(bra)}회({', '.join(map(str, bra))})입니다",
               "가장 많이 우승한 나라라는 건 알아도, 몇 번인지는 대개 흐릿합니다."),
        ranged("wc2", f"{WC_SPAN} 월드컵 본선 통산 개인 최다 골은 몇 골일까요?",
               top_career, "골", 5, 30, 1,
               f"{WC_SPAN} 월드컵 모든 경기의 득점자 기록을 선수별로 더하면(자책골 "
               f"제외) 가장 많은 선수는 "
               f"{', '.join(n for n, v in career.items() if v == top_career)}"
               f"의 {top_career}골입니다",
               "오래된 기록을 떠올리기 쉬운데, 통산 기록은 최근 대회에서도 바뀝니다."),
        ranged("wc3", f"{WC_SPAN} 월드컵 한 대회에서 한 선수가 넣은 최다 골은?",
               top_cup, "골", 5, 20, 1,
               f"{WC_SPAN} 대회마다 선수별 골을 세면(자책골 제외) 가장 많은 값은 "
               f"{', '.join(f'{name} {y}년' for n, name, y in by_cup if n == top_cup)}"
               f"의 {top_cup}골입니다",
               "득점왕은 대개 5~8골이라, 그 감각으로 상한을 잡게 됩니다."),
        ranged("wc4", f"{WC_SPAN} 월드컵 한 경기에서 나온 최다 골(양 팀 합계, "
                      "연장 포함)은?",
               wc_tot, "골", 5, 15, 1,
               f"{WC_SPAN} 모든 경기의 양 팀 골 합계(연장 포함, 승부차기 제외) 중 "
               f"최댓값은 {wc_tot}골"
               f"({'; '.join(f'{y}년 ' + m['team1'] + ' ' + '-'.join(map(str, wc_score(m))) + ' ' + m['team2'] for y, m in wc_tot_games)})입니다",
               "가장 유명한 대승 스코어가 기준점이 되어, 난타전 기록을 놓치기 쉽습니다."),
        ranged("wc5", f"{WC_LAST} 월드컵 본선은 모두 몇 경기를 치렀을까요?",
               len(WC[WC_LAST]), "경기", 48, 128, 1,
               f"{WC_LAST}년 대회 경기 기록을 세면 {len(WC[WC_LAST])}경기"
               f"(직전 {WC_LAST - 4}년 대회는 {len(WC[WC_LAST - 4])}경기)입니다",
               "참가국이 늘어난 것을 모르면 직전 대회 경기 수에 묶여 짐작하게 됩니다."),
    ],
    caveat="득점자는 이름으로 묶어 셌고, 대소문자·악센트만 다른 표기는 같은 선수로 "
           "합쳤습니다. 자책골은 빼고, 승부차기 골은 넣지 않았습니다.")

# ── 축구 5. 한국 축구 ────────────────────────────────────────────
kor_years = [y for y in sorted(WC)
             if any(KOR in (m["team1"], m["team2"]) for m in WC[y])]
streak = []
for y in sorted(WC, reverse=True):
    if y not in kor_years:
        break
    streak.append(y)
kor_games = [m for y in WC for m in WC[y]
             if KOR in (m["team1"], m["team2"])]


def kor_for_against(m):
    a, b = wc_score(m)
    return (a, b) if m["team1"] == KOR else (b, a)


kor_w = sum(1 for m in kor_games if kor_for_against(m)[0] > kor_for_against(m)[1])
kor_d = sum(1 for m in kor_games if kor_for_against(m)[0] == kor_for_against(m)[1])
kor_gf = sum(kor_for_against(m)[0] for m in kor_games)
kor_players = Counter(name for _, _, name, cc in UCL_GOALS if cc == "KOR")
son = ucl_goals_of(ucl_player("Heung-Min Son"))

topic(
    "soccer-korea", "🇰🇷", "한국 축구",
    "월드컵 속 한국, 챔스 속 한국 선수",
    "openfootball worldcup.json · UEFA 경기 기록",
    "https://github.com/openfootball/worldcup.json",
    [
        ranged("kr1", f"{WC_LAST}년 대회까지, 한국은 월드컵 본선에 몇 회 연속 "
                      "나갔을까요?",
               len(streak), "회", 1, 15, 1,
               f"{WC_SPAN} 대회별 본선 경기 기록에 한국이 있는지 보고 {WC_LAST}년부터 "
               f"거꾸로 세면 {len(streak)}회 연속({streak[-1]}~{streak[0]}년)입니다",
               "'매번 나가는 것 같다'는 느낌은 있어도, 그게 몇 회째인지는 대부분 "
               "모릅니다."),
        ranged("kr2", f"{WC_SPAN} 월드컵 본선에서 한국은 몇 번 이겼을까요? "
                      "(승부차기는 무승부)",
               kor_w, "승", 0, 20, 1,
               f"{WC_SPAN} 한국의 본선 경기를 세면(승부차기 경기는 무승부) "
               f"{len(kor_games)}경기 {kor_w}승 {kor_d}무 "
               f"{len(kor_games) - kor_w - kor_d}패입니다",
               "2002년의 기억이 크게 남아서 승리 수를 실제보다 많게 짐작하기 "
               "쉽습니다."),
        ranged("kr3", f"{WC_SPAN} 월드컵 본선에서 한국이 넣은 골은 모두 "
                      "몇 골일까요? (승부차기 제외)",
               kor_gf, "골", 10, 60, 1,
               f"{WC_SPAN} 한국의 본선 {len(kor_games)}경기에서 한국 쪽 골"
               f"(연장 포함, 승부차기 제외)을 더하면 {kor_gf}골입니다",
               "명장면 골 몇 개가 기억을 채워서, 전체 골 수는 감으로 잡기 어렵습니다."),
        ranged("kr4", f"{UCL_SPAN} 시즌 챔피언스리그 본선에서 한국 선수들이 넣은 골을 "
                      "모두 더하면?",
               sum(kor_players.values()), "골", 0, 60, 1,
               f"{UCL_SPAN} 시즌 UEFA 경기 기록에서 예선을 뺀 본선 경기 중 국적이 "
               f"한국(KOR)인 선수의 골을 더하면 {sum(kor_players.values())}골"
               f"({', '.join(f'{n} {v}' for n, v in kor_players.most_common())})입니다",
               "손흥민 한 명만 떠올리기 쉽지만, 챔스에서 골을 넣은 한국 선수는 "
               "여럿입니다."),
        ranged("kr5", f"{UCL_SPAN} 시즌, 손흥민이 챔피언스리그 본선에서 넣은 골은 "
                      "모두 몇 골일까요?",
               son, "골", 0, 40, 1,
               f"{UCL_SPAN} 시즌 UEFA 경기 기록에서 예선을 뺀 본선 경기의 손흥민 득점"
               f"(자책골 제외)을 소속팀 구분 없이 세면 {son}골입니다",
               "리그 득점 감각으로 짐작하면 챔스 골은 크게 빗나갑니다."),
    ],
    caveat="월드컵 전적에서 승부차기로 끝난 경기는 FIFA 방식대로 무승부로 세고, "
           "3·4위전도 넣습니다. 챔스의 '한국 선수'는 UEFA 기록의 국적(KOR) 기준이고, "
           "골은 예선을 뺀 본선 중 끝까지 치른 경기만 셉니다.")

# ── 축구 6. 챔피언스리그 ─────────────────────────────────────────
rm_ucl = [end for end, m in FINALS.items() if ucl_winner(m) == RM]
margin = {end: abs(m["score"]["total"]["home"] - m["score"]["total"]["away"])
          for end, m in FINALS.items()}
big = max(margin.values())
pens = [end for end, m in FINALS.items() if m["score"].get("penalty")]
cr7 = ucl_goals_of(ucl_player("Cristiano Ronaldo"))
per_season = Counter((end, pid) for end, pid, _, _ in UCL_GOALS)
top_season = max(per_season.values())
names = {pid: n for _, pid, n, _ in UCL_GOALS}


def final_str(end):
    m = FINALS[end]
    h, a = ucl_teams(m)
    return f"{ucl_season(end)} {h} {m['score']['total']['home']}-{m['score']['total']['away']} {a}"


topic(
    "soccer-ucl", "⭐", "챔피언스리그",
    f"{ucl_season(UCL_FIRST)} 유러피언컵부터 {ucl_season(UCL_LAST)}까지",
    "UEFA 경기 기록 (match.uefa.com)",
    "https://py.sportsdataverse.org/docs/soccer/reference/uefa",
    [
        ranged("ucl1", f"{UCL_SPAN} 시즌 레알 마드리드의 유러피언컵·챔스 우승은 "
                       "몇 번일까요?",
               len(rm_ucl), "회", 5, 20, 1,
               f"{UCL_SPAN} 시즌 결승 경기 기록(재경기는 마지막 경기, 승부차기 포함)의 "
               f"승자를 세면 레알 마드리드는 {len(rm_ucl)}회입니다",
               "두 자릿수라는 걸 모르면 다른 강팀들과 비슷하게 짐작하게 됩니다."),
        ranged("ucl2", f"{UCL_SPAN} 시즌 결승에서 나온 가장 큰 점수 차는 몇 골일까요?",
               big, "골", 1, 8, 1,
               f"{UCL_SPAN} 시즌 결승 {len(FINALS)}경기의 최종 스코어(연장 포함) 점수 차 "
               f"중 최댓값은 {big}골"
               f"({'; '.join(final_str(e) for e, v in margin.items() if v == big)})입니다",
               "결승은 늘 박빙이라는 인상 때문에 점수 차를 작게 잡기 쉽습니다."),
        ranged("ucl3", f"{UCL_SPAN} 시즌 결승 중 승부차기로 우승팀이 갈린 경기는 "
                       "몇 번일까요?",
               len(pens), "번", 0, 20, 1,
               f"{UCL_SPAN} 시즌 결승 {len(FINALS)}경기 중 승부차기 기록이 있는 경기를 "
               f"세면 {len(pens)}번({', '.join(ucl_season(e) for e in pens)})입니다",
               "승부차기 결승은 장면이 강렬해서 실제보다 많게 기억되기도 합니다."),
        ranged("ucl4", f"{UCL_SPAN} 시즌, 크리스티아누 호날두가 챔피언스리그 본선에서 "
                       "넣은 골은 모두 몇 골일까요?",
               cr7, "골", 50, 200, 1,
               f"{UCL_SPAN} 시즌 UEFA 경기 기록에서 예선을 뺀 본선 경기의 호날두 득점"
               f"(자책골 제외)을 소속팀 구분 없이 세면 {cr7}골입니다",
               "100골이 넘는지조차 감이 엇갈립니다. 한 시즌 몇 골씩 쌓였는지 "
               "떠올려 보면 다릅니다."),
        ranged("ucl5", f"{UCL_SPAN} 시즌, 한 선수가 한 시즌 챔스 본선에서 넣은 "
                       "최다 골은?",
               top_season, "골", 5, 25, 1,
               f"{UCL_SPAN} 시즌마다 예선을 뺀 본선 경기의 선수별 골(자책골 제외)을 "
               f"세면 가장 많은 값은 "
               f"{', '.join(f'{names[p]} {ucl_season(e)}' for (e, p), v in per_season.items() if v == top_season)}"
               f"의 {top_season}골입니다",
               "리그 득점왕 숫자에 익숙하면, 챔스 한 시즌 기록을 낮게 잡게 됩니다."),
    ],
    caveat="골은 예선을 뺀 본선 경기, 그중 끝까지 치른 경기만 셉니다(1991-92 시즌까지의 "
           "유러피언컵은 전 라운드). 취소·중단·미개최 경기 "
           f"{sum(UCL_SKIPPED.values())}개의 기록과 자책골, 득점자가 기록되지 않은 본선 골 "
           f"{len(UCL_NO_SCORER)}개(모두 {ucl_season(max(UCL_NO_SCORER))} 시즌 이전)는 "
           "뺐습니다.")

# 축구만 다시 계산할 때는 여기서 파일을 쓰고 끝낸다. 아래 10주제는 건드리지 않는다
if __name__ == "__main__" and "--soccer" in sys.argv:
    main()
    sys.exit(0)


# ════════════════════════════════════════════════════════════════
# 기상 공통
# ════════════════════════════════════════════════════════════════
w = load_json("seoul_weather.json")["daily"]
W = [{"d": dt.date.fromisoformat(t), "hi": hi, "lo": lo, "rain": r}
     for t, hi, lo, r in zip(w["time"], w["temperature_2m_max"],
                             w["temperature_2m_min"], w["precipitation_sum"])]
W24 = [x for x in W if x["d"].year == 2024]


def years(a, b):
    return [x for x in W if a <= x["d"].year <= b]


# ── 1. 서울 기온 ─────────────────────────────────────────────────
# ERA5 는 1950~70년대 구간의 품질이 낮고(초기 확장), 격자 평균이라 도심
# 관측값보다 낮게 나온다. 그래서 '역대 최고기온'이나 '폭염일 추세'처럼
# 그 구간에 기대는 문항은 쓰지 않는다. 열대야·연평균처럼 신호가 뚜렷한 것만 쓴다.
tropical_24 = sum(1 for x in W24 if x["lo"] >= 25)
trop_50s = sum(1 for x in years(1950, 1959) if x["lo"] >= 25) / 10
trop_10s = sum(1 for x in years(2015, 2024) if x["lo"] >= 25) / 10
t_ratio = trop_10s / trop_50s if trop_50s else 0
mean_50s = mean((x["hi"] + x["lo"]) / 2 for x in years(1950, 1959))
mean_10s = mean((x["hi"] + x["lo"]) / 2 for x in years(2015, 2024))
warming = mean_10s - mean_50s
below0_24 = sum(1 for x in W24 if x["lo"] < 0)
hot_days = Counter((x["d"].month, x["d"].day)
                   for x in years(1995, 2024) if x["hi"] >= 33)
peak_day = hot_days.most_common(1)[0]
# 한계 문장의 숫자도 손으로 적지 않는다 — 원본에서 가장 더웠던 날을 찾는다
hottest = max(W, key=lambda x: x["hi"])

topic(
    "seoul-heat", "🌡️", "서울은 얼마나 더워졌나",
    "1950년부터 2024년까지, 서울의 매일 기온",
    "Open-Meteo Archive (ERA5 재분석)", "https://open-meteo.com/",
    [
        slider("h1", "2024년 서울에서 열대야(밤 최저기온 25도 이상)는 며칠이었을까요?",
               tropical_24, "일", 0, 60, 1,
               f"2024년 일최저기온 25도 이상인 날 {tropical_24}일",
               "유난히 더웠던 밤 몇 번이 기억을 지배합니다. 실제 일수는 세어 봐야 "
               "압니다."),
        # 보기는 배수에 가장 가까운 것이 정답이 되게 경계를 둔다 (2.8배 → «약 3배»)
        choice("h2", "1950년대와 2015~2024년, 열대야는 몇 배 차이일까요?",
               ["거의 같다", "약 2배", "약 3배", "약 5배"],
               ["거의 같다", "약 2배", "약 3배", "약 5배"][
                   0 if t_ratio < 1.5 else 1 if t_ratio < 2.5
                   else 2 if t_ratio < 4 else 3],
               f"연평균 열대야 1950년대 {trop_50s:.1f}일 → 2015~2024년 "
               f"{trop_10s:.1f}일 ({t_ratio:.1f}배)",
               "'옛날에도 더웠다'는 느낌과 기록은 다릅니다. 기억은 유난히 더웠던 "
               "몇 밤으로 남지만, 기록은 해마다 빠짐없이 셉니다."),
        slider("h3", "1950년대와 비교해 서울의 연평균 기온은 몇 도 올랐을까요?",
               warming, "도", 0, 4, 0.1,
               f"1950년대 {mean_50s:.2f}도 → 2015~2024년 {mean_10s:.2f}도 "
               f"(+{warming:.2f}도)",
               "1~2도는 작아 보이지만, 그 변화가 열대야 일수를 몇 배로 바꿉니다. "
               "평균의 변화와 극단의 변화는 크기가 다릅니다."),
        choice("h4", "최근 30년간 33도 이상인 날이 가장 잦았던 날짜는?",
               ["7월 초", "7월 말", "8월 초", "8월 말"],
               "7월 말" if peak_day[0][0] == 7 and peak_day[0][1] >= 20
               else "8월 초" if peak_day[0][0] == 8 and peak_day[0][1] <= 10
               else "7월 초" if peak_day[0][0] == 7 else "8월 말",
               f"1995~2024년 중 가장 잦았던 날짜는 {peak_day[0][0]}월 "
               f"{peak_day[0][1]}일 ({peak_day[1]}회)",
               "장마가 끝나는 시점과 가장 더운 시점은 다릅니다."),
        slider("h5", "2024년 서울에서 밤 기온이 영하로 내려간 날은 며칠이었을까요?",
               below0_24, "일", 30, 150, 5,
               f"2024년 일최저기온 0도 미만인 날 {below0_24}일",
               "겨울이 짧아졌다고 느끼지만, 영하로 내려가는 날은 여전히 석 달 "
               "치가 넘습니다."),
    ],
    caveat="ERA5는 넓은 격자의 재분석 값이라 도심 관측소와 다르게 나옵니다. "
           f"예컨대 여기서는 역대 최고기온이 {hottest['hi']:.1f}도"
           f"({hottest['d']:%Y년})지만 기상청 서울 관측 기록은 2018년 39.6도입니다. "
           "같은 '서울 기온'도 출처에 따라 다릅니다.")

# ── 2. 비 ────────────────────────────────────────────────────────
rain_days = [sum(1 for x in W if x["d"].year == y and x["rain"] >= 1.0)
             for y in range(1995, 2025)]
rain_avg = mean(rain_days)
by_month = {m: mean([sum(x["rain"] for x in W
                         if x["d"].year == y and x["d"].month == m)
                     for y in range(1995, 2025)]) for m in range(1, 13)}
wettest_m = max(by_month, key=by_month.get)
max_day = max(W, key=lambda x: x["rain"])
ann = {y: sum(x["rain"] for x in W if x["d"].year == y) for y in range(1995, 2025)}
norm = mean(ann.values())
r2024 = ann[2024]


def days_to_half(y):
    v = sorted((x["rain"] for x in W if x["d"].year == y), reverse=True)
    half, s = sum(v) / 2, 0
    for i, r in enumerate(v, 1):
        s += r
        if s >= half:
            return i
    return len(v)


half_days = round(mean(days_to_half(y) for y in range(1995, 2025)))

topic(
    "seoul-rain", "☔", "비는 언제, 얼마나",
    "서울의 하루치 강수량 30년",
    "Open-Meteo Archive (ERA5 재분석)", "https://open-meteo.com/",
    [
        slider("r1", "서울에서 1년 중 비가 온 날(1mm 이상)은 며칠쯤일까요?",
               rain_avg, "일", 40, 160, 5,
               f"1995~2024년 평균 {rain_avg:.1f}일 "
               f"(최소 {min(rain_days)}일 · 최대 {max(rain_days)}일)",
               "비 오는 날은 기억에 오래 남아서 실제보다 많게 느껴집니다."),
        choice("r2", "1년 강수량이 가장 많은 달은?",
               ["6월", "7월", "8월", "9월"], f"{wettest_m}월",
               " · ".join(f"{m}월 {by_month[m]:.0f}mm" for m in (6, 7, 8, 9)),
               "장마가 낀 달과 비가 가장 많이 오는 달이 같지 않을 수 있습니다."),
        slider("r3", "하루에 내린 비의 최대 기록은?",
               max_day["rain"], "mm", 100, 500, 10,
               f"{max_day['d']:%Y년 %m월 %d일} {max_day['rain']:.1f}mm",
               f"가장 많이 온 날 하루에, 비가 가장 많은 {wettest_m}월 한 달 평균"
               f"({by_month[wettest_m]:.0f}mm)의 {max_day['rain'] / by_month[wettest_m] * 100:.0f}%가 "
               "쏟아졌습니다. 비는 고르게 오지 않습니다."),
        slider("r4", "1년 강수량의 절반은 '비 온 날' 며칠 만에 채워질까요?",
               half_days, "일", 3, 40, 1,
               f"많이 온 날부터 더해서 연 강수량의 절반에 도달하는 데 "
               f"평균 {half_days}일 (1995~2024년)",
               "비는 고르게 오지 않습니다. 열흘 남짓이 1년의 절반을 만듭니다."),
        slider("r5", "2024년 서울 강수량은 30년 평균의 몇 %였을까요?",
               r2024 / norm * 100, "%", 50, 180, 5,
               f"2024년 {r2024:.0f}mm · 1995~2024년 평균 {norm:.0f}mm",
               "'올해 비가 많았다'는 체감과 실제 총량은 자주 어긋납니다."),
    ],
    caveat="ERA5 재분석 값입니다. 기상청 관측 강수량과 조금씩 다릅니다.")

# ── 3. 미세먼지 ──────────────────────────────────────────────────
a = load_json("seoul_air.json")["hourly"]
A = [{"t": dt.datetime.fromisoformat(t), "pm25": p25, "pm10": p10}
     for t, p25, p10 in zip(a["time"], a["pm2_5"], a["pm10"])]
A24 = [x for x in A if x["t"].year == 2024]
pm_month = {m: mean([x["pm25"] for x in A if x["t"].month == m])
            for m in range(1, 13)}
worst_m = max(pm_month, key=pm_month.get)
pm_hour = {h: mean([x["pm25"] for x in A if x["t"].hour == h])
           for h in range(24)}
worst_h = max(pm_hour, key=pm_hour.get)
pm24_avg = mean(x["pm25"] for x in A24)


def daily_avg(year):
    d = {}
    for x in A:
        if x["t"].year == year:
            d.setdefault(x["t"].date(), []).append(x["pm25"])
    return {k: mean(v) for k, v in d.items()}


d24 = daily_avg(2024)
d23 = daily_avg(2023)
bad_ratio = sum(1 for v in d24.values() if v > 35) / len(d24) * 100
worse_year = "2023년" if mean(d23.values()) > mean(d24.values()) else "2024년"

topic(
    "seoul-air", "😷", "미세먼지, 언제 나쁜가",
    "서울의 시간별 초미세먼지 2년치",
    "Open-Meteo Air Quality (CAMS)", "https://open-meteo.com/",
    [
        choice("a1", "초미세먼지(PM2.5)가 가장 나쁜 달은?",
               ["1월", "3월", "5월", "11월"],
               f"{worst_m}월" if f"{worst_m}월" in ["1월", "3월", "5월", "11월"]
               else "3월",
               " · ".join(f"{m}월 {pm_month[m]:.1f}" for m in (1, 3, 5, 11))
               + f" (최악은 {worst_m}월 {pm_month[worst_m]:.1f})",
               "황사 뉴스가 많은 달과 실제 수치가 높은 달은 다를 수 있습니다."),
        slider("a2", "2024년 서울의 초미세먼지 연평균 농도는?",
               pm24_avg, "㎍/㎥", 5, 60, 1,
               f"2024년 시간값 {len(A24):,}개의 평균 {pm24_avg:.1f}㎍/㎥ "
               f"(WHO 권고 연평균 5, 국내 기준 15)",
               "'나쁨'인 날이 인상에 남아서 연평균을 높게 잡게 됩니다."),
        choice("a3", "하루 중 초미세먼지가 가장 높은 시간대는?",
               ["새벽 4시", "오전 10시", "오후 3시", "밤 9시"],
               {4: "새벽 4시", 10: "오전 10시", 15: "오후 3시",
                21: "밤 9시"}.get(worst_h, "오전 10시"),
               " · ".join(f"{h}시 {pm_hour[h]:.1f}" for h in (4, 10, 15, 21))
               + f" (최고는 {worst_h}시)",
               "출퇴근 시간이 가장 나쁠 것 같지만 대기가 정체되는 시간은 따로 "
               "있습니다."),
        slider("a4", "2024년 하루 평균이 '나쁨'(35㎍/㎥ 초과)이었던 날의 비율은?",
               bad_ratio, "%", 0, 60, 1,
               f"2024년 {len(d24)}일 중 "
               f"{sum(1 for v in d24.values() if v > 35)}일",
               "마스크를 챙긴 날은 강하게 기억되지만, 1년 전체로 보면 비율이 "
               "다릅니다."),
        choice("a5", "2023년과 2024년 중 초미세먼지가 더 나빴던 해는?",
               ["2023년", "2024년"], worse_year,
               f"연평균 2023년 {mean(d23.values()):.1f} · "
               f"2024년 {mean(d24.values()):.1f}㎍/㎥",
               "체감은 최근 쪽으로 쏠립니다. 두 해 차이는 생각보다 작습니다."),
    ],
    caveat="CAMS 대기질 모델의 추정값입니다. 에어코리아 측정소 실측값과 "
           "다를 수 있습니다.")

# ── 4. 노동시간 ──────────────────────────────────────────────────
wh = [r for r in load_csv("working_hours.csv") if r["working_hours_omm"]]
latest_year = max(int(r["year"]) for r in wh if r["code"] == "KOR")
cur = owid_countries(wh, latest_year, "working_hours_omm")
kor = cur["South Korea"]
rank = sorted(cur.items(), key=lambda kv: -kv[1])
kor_rank = [k for k, _ in rank].index("South Korea") + 1
longer = kor_rank - 1
past = {int(r["year"]): float(r["working_hours_omm"])
        for r in wh if r["code"] == "KOR"}
y30 = latest_year - 30
drop = past[y30] - kor
trio = {c: cur[c] for c in ("South Korea", "Japan", "Germany") if c in cur}
shortest = min(trio, key=trio.get)
name_ko = {"South Korea": "한국", "Japan": "일본", "Germany": "독일"}

topic(
    "working-hours", "⏰", "우리는 얼마나 일하나",
    "나라별 1인당 연간 노동시간",
    "Our World in Data", "https://ourworldindata.org/grapher/annual-working-hours-per-worker",
    [
        slider("w1", f"{latest_year}년 한국의 1인당 연간 노동시간은?",
               kor, "시간", 1200, 2600, 50,
               f"{latest_year}년 한국 {kor:,.0f}시간 "
               f"(주 5일 기준 하루 약 {kor / 250:.1f}시간)",
               "연 단위로 물으면 감이 잘 안 옵니다. 하루로 나눠 보면 체감과 "
               "맞는지 확인할 수 있습니다."),
        slider("w2", f"한국보다 더 오래 일하는 나라는 {len(cur)}개국 중 몇 개일까요?",
               longer, "개국", 0, 60, 1,
               f"{latest_year}년 기준 {len(cur)}개국 중 한국은 {kor_rank}위",
               "'한국이 제일 많이 일한다'는 인상이 강하지만, 비교 대상에 따라 "
               "순위가 달라집니다."),
        slider("w3", f"한국의 노동시간은 30년 전({y30}년)보다 몇 시간 줄었을까요?",
               drop, "시간", 0, 900, 50,
               f"{y30}년 {past[y30]:,.0f}시간 → {latest_year}년 {kor:,.0f}시간",
               "줄어든 폭은 대개 과소평가됩니다. 하루로 치면 크게 달라진 값입니다."),
        choice("w4", "한국·일본·독일 중 가장 적게 일하는 나라는?",
               ["한국", "일본", "독일"], name_ko[shortest],
               " · ".join(f"{name_ko[c]} {trio[c]:,.0f}시간" for c in trio),
               "나라마다 통계 기준이 다릅니다. 순위보다 격차의 크기를 봅니다."),
        slider("w5", "한국과 독일의 연간 노동시간 차이는?",
               abs(cur["South Korea"] - cur["Germany"]), "시간", 0, 900, 50,
               f"한국 {cur['South Korea']:,.0f} · 독일 "
               f"{cur['Germany']:,.0f}시간",
               "두 나라 차이를 주 단위로 나눠 보면 체감이 확 달라집니다."),
    ],
    caveat="이 자료에는 개발도상국이 많이 포함돼 있어, OECD 안에서의 순위와 "
           "전체 순위가 다릅니다. '어느 집단과 비교하느냐'가 순위를 만듭니다.")

# ── 5. 인구와 출산 ───────────────────────────────────────────────
fert = [r for r in load_json("wb_fertility.json")[1] if r["value"] is not None]
f_latest = max(int(r["date"]) for r in fert if r["countryiso3code"] == "KOR")
f_cur = wb_countries(fert, f_latest)
kor_f = f_cur["Korea, Rep."]
f_rank = sorted(f_cur.items(), key=lambda kv: kv[1])
kor_f_rank = [k for k, _ in f_rank].index("Korea, Rep.") + 1
kor_1970 = next(r["value"] for r in fert
                if r["countryiso3code"] == "KOR" and r["date"] == "1970")

pop = load_json("wb_pop_kor.json")[1]
tot = {int(r["date"]): r["value"] for r in pop
       if r["indicator"]["id"] == "SP.POP.TOTL" and r["value"]}
old = {int(r["date"]): r["value"] for r in pop
       if r["indicator"]["id"] == "SP.POP.65UP.TO.ZS" and r["value"]}
urb = {int(r["date"]): r["value"] for r in pop
       if r["indicator"]["id"] == "SP.URB.TOTL.IN.ZS" and r["value"]}
peak_year = max(tot, key=tot.get)
old_latest = max(old)
urb_latest = max(urb)

topic(
    "population", "👶", "인구와 출산",
    "전 세계 출산율과 한국의 인구 구조",
    "World Bank Open Data", "https://data.worldbank.org/",
    [
        slider("p1", f"{f_latest}년 한국의 합계출산율(여성 1명당 출생아 수)은?",
               kor_f, "명", 0.5, 3.0, 0.05,
               f"{f_latest}년 한국 {kor_f:.2f}명",
               "숫자는 자주 들었어도 '여성 1명당'이라는 단위는 잘 안 와닿습니다."),
        slider("p2", f"출산율이 낮은 순으로 세면 한국은 {len(f_cur)}개 나라·지역 중 몇 위일까요?",
               kor_f_rank, "위", 1, 30, 1,
               f"{f_latest}년 기준 {len(f_cur)}곳 중 {kor_f_rank}위 "
               f"(1위 {f_rank[0][0]} {f_rank[0][1]:.2f})",
               "'꼴찌'라고 알고 있지만, 비교 목록에 어떤 나라·지역이 들어가느냐에 "
               "따라 순위가 달라집니다."),
        slider("p3", "1970년 한국의 출산율은 몇 명이었을까요?",
               kor_1970, "명", 1.0, 7.0, 0.1,
               f"1970년 {kor_1970:.2f}명 → {f_latest}년 {kor_f:.2f}명",
               "한 세대 만에 일어난 변화의 크기는 대개 과소평가됩니다."),
        slider("p4", f"{old_latest}년 한국에서 65세 이상 인구의 비율은?",
               old[old_latest], "%", 5, 35, 1,
               f"{old_latest}년 {old[old_latest]:.1f}% "
               f"(World Bank 최신 공표치. 최근 연도는 추계값입니다)",
               "고령화는 '다가올 일'로 느껴지지만 이미 지나온 숫자입니다."),
        slider("p5", f"{urb_latest}년 한국에서 도시에 사는 사람의 비율은?",
               urb[urb_latest], "%", 50, 100, 1,
               f"{urb_latest}년 {urb[urb_latest]:.1f}% "
               f"(World Bank 최신 공표치. 최근 연도는 추계값입니다)",
               "'절반쯤'이라고 답하기 쉽지만 한국은 세계에서도 손꼽히는 도시 국가입니다."),
    ])

# ── 6. 인터넷 ────────────────────────────────────────────────────
net = [r for r in load_json("wb_internet.json")[1] if r["value"] is not None]
n_latest = max(int(r["date"]) for r in net if r["countryiso3code"] == "KOR")
n_cur = wb_countries(net, n_latest)
kor_n = n_cur["Korea, Rep."]
n_rank = sorted(n_cur.items(), key=lambda kv: -kv[1])
kor_n_rank = [k for k, _ in n_rank].index("Korea, Rep.") + 1
kor_2000 = next(r["value"] for r in net
                if r["countryiso3code"] == "KOR" and r["date"] == "2000")
world = next((r["value"] for r in net
              if r["countryiso3code"] == "WLD" and int(r["date"]) == n_latest), None)
if world is None:
    world = mean(n_cur.values())
offline = 100 - world

topic(
    "internet", "🌐", "인터넷과 연결",
    "나라별 인터넷 사용 인구 비율",
    "World Bank Open Data", "https://data.worldbank.org/",
    [
        slider("i1", f"{n_latest}년 한국에서 인터넷을 쓰는 사람의 비율은?",
               kor_n, "%", 60, 100, 1,
               f"{n_latest}년 한국 {kor_n:.1f}%",
               "'거의 다'라고 생각하지만 100%는 아닙니다. 남은 몇 %가 누구인지가 "
               "정책의 대상입니다."),
        slider("i2", f"한국보다 인터넷 사용률이 높은 나라는 {len(n_cur)}곳 중 몇 곳일까요?",
               kor_n_rank - 1, "곳", 0, 60, 1,
               f"{n_latest}년 {len(n_cur)}곳 중 한국 {kor_n_rank}위",
               "'IT 강국'이라는 말과 실제 보급률 순위는 다른 이야기입니다."),
        slider("i3", "2000년 한국의 인터넷 사용률은?",
               kor_2000, "%", 0, 100, 5,
               f"2000년 {kor_2000:.1f}% → {n_latest}년 {kor_n:.1f}%",
               "20여 년 전을 떠올릴 때는 지금의 기준으로 과대평가하기 쉽습니다."),
        slider("i4", f"{n_latest}년 전 세계 평균 인터넷 사용률은?",
               world, "%", 20, 100, 5,
               f"{n_latest}년 세계 {world:.1f}%",
               "내 주변이 전부 연결돼 있으면 세계도 그럴 거라고 생각하게 됩니다."),
        slider("i5", "전 세계에서 인터넷을 쓰지 않는 사람은 몇 %일까요?",
               offline, "%", 0, 70, 5,
               f"100 - {world:.1f} = {offline:.1f}%",
               "같은 사실을 뒤집어 물으면 전혀 다른 크기로 느껴집니다."),
    ])

# ── 7. 환율 ──────────────────────────────────────────────────────
fx = load_json("usdkrw.json")["rates"]
FX = sorted((d, v["KRW"]) for d, v in fx.items() if "KRW" in v)
hi_d, hi_v = max(FX, key=lambda x: x[1])
lo_d, lo_v = min(FX, key=lambda x: x[1])
avg_fx = mean(v for _, v in FX)
under1200 = sum(1 for _, v in FX if v < 1200) / len(FX) * 100
last_d, last_v = FX[-1]
era = ("1997~1999년 외환위기" if hi_d < "2005" else
       "2008~2009년 금융위기" if hi_d < "2012" else
       "2020년 코로나" if hi_d < "2022" else "2022년 이후")

topic(
    "usdkrw", "💵", "원달러 환율 26년",
    "1999년부터 오늘까지의 원달러 환율",
    "Frankfurter (유럽중앙은행 고시)", "https://frankfurter.dev/",
    [
        slider("x1", "1999년 이후 원달러 환율의 최고 기록은?",
               hi_v, "원", 1100, 1800, 25,
               f"{hi_d} {hi_v:,.2f}원",
               "최고치는 위기의 기억과 함께 남지만, 정확한 시점은 자주 헷갈립니다."),
        choice("x2", "그 최고치를 찍은 시기는?",
               ["1997~1999년 외환위기", "2008~2009년 금융위기",
                "2020년 코로나", "2022년 이후"], era,
               f"최고 {hi_v:,.2f}원 ({hi_d}). 이 데이터는 1999년부터라 "
               f"1997~98년 외환위기 구간은 포함되어 있지 않습니다",
               "데이터가 시작하는 시점을 확인하지 않으면 '역대 최고'를 잘못 "
               "말하게 됩니다."),
        slider("x3", "26년간의 평균 환율은?",
               avg_fx, "원", 900, 1500, 25,
               f"{FX[0][0]} ~ {FX[-1][0]} 거래일 {len(FX):,}일 평균 "
               f"{avg_fx:,.0f}원 (최저 {lo_v:,.0f}원 · {lo_d})",
               "최근 값이 기준점이 되어 과거 평균을 높게 잡게 됩니다."),
        slider("x4", "환율이 1,200원 아래였던 날은 전체의 몇 %일까요?",
               under1200, "%", 0, 100, 5,
               f"거래일 {len(FX):,}일 중 1,200원 미만은 "
               f"{sum(1 for _, v in FX if v < 1200):,}일",
               "'원래 1,100원대였는데'라는 감각이 맞는지 비율로 확인해 봅니다."),
        slider("x5", f"{last_d} 기준 환율은?",
               last_v, "원", 1100, 1800, 25,
               f"{last_d} {last_v:,.2f}원",
               "가장 최근 값조차 기억은 며칠 전 뉴스에 묶여 있습니다."),
    ])

# ── 8. 도시 비교 ─────────────────────────────────────────────────
CITY = {}
for cid in ("seoul", "tokyo", "london", "singapore"):
    _d = load_json(f"city_{cid}.json")["daily"]
    CITY[cid] = [{"d": dt.date.fromisoformat(t), "hi": a, "lo": b, "r": c}
                 for t, a, b, c in zip(_d["time"], _d["temperature_2m_max"],
                                       _d["temperature_2m_min"],
                                       _d["precipitation_sum"])]
CN = {"seoul": "서울", "tokyo": "도쿄", "london": "런던", "singapore": "싱가포르"}
YRS = 30
c_rain = {k: sum(x["r"] for x in v) / YRS for k, v in CITY.items()}
c_days = {k: sum(1 for x in v if x["r"] >= 1) / YRS for k, v in CITY.items()}
c_temp = {k: mean((x["hi"] + x["lo"]) / 2 for x in v) for k, v in CITY.items()}
c_hot = {k: max(x["hi"] for x in v) for k, v in CITY.items()}
c_jan = {k: mean(x["lo"] for x in v if x["d"].month == 1) for k, v in CITY.items()}
dry = min(c_rain, key=c_rain.get)
hottest = max(c_hot, key=c_hot.get)
colder = "서울" if c_jan["seoul"] < c_jan["tokyo"] else "도쿄"

topic(
    "cities", "🏙️", "서울·도쿄·런던·싱가포르",
    "네 도시의 30년 평년값 (1991~2020)",
    "Open-Meteo Archive (ERA5 재분석)", "https://open-meteo.com/",
    [
        choice("c1", "1년 강수량이 가장 적은 도시는?",
               ["서울", "도쿄", "런던", "싱가포르"], CN[dry],
               " · ".join(f"{CN[k]} {c_rain[k]:,.0f}mm" for k in CITY),
               "비가 자주 오는 것과 많이 오는 것은 다릅니다. 런던은 자주 오지만 "
               "적게 옵니다."),
        slider("c2", "런던에서 1년에 비가 오는 날(1mm 이상)은 며칠일까요?",
               c_days["london"], "일", 40, 220, 5,
               f"런던 {c_days['london']:.0f}일 · 서울 {c_days['seoul']:.0f}일 "
               f"(강수량은 런던 {c_rain['london']:,.0f}mm · "
               f"서울 {c_rain['seoul']:,.0f}mm)",
               "런던은 서울보다 비 오는 날이 많은데 총량은 절반입니다. "
               "'며칠 왔나'와 '얼마나 왔나'는 다른 질문입니다."),
        choice("c3", "30년간 가장 높은 기온을 기록한 도시는?",
               ["서울", "도쿄", "런던", "싱가포르"], CN[hottest],
               " · ".join(f"{CN[k]} {c_hot[k]:.1f}도" for k in CITY),
               "적도에 가까울수록 덥다고 생각하지만, 최고기온 기록은 중위도 "
               "도시에서 나옵니다."),
        slider("c4", "서울의 연평균 기온은?",
               c_temp["seoul"], "도", 5, 30, 0.5,
               " · ".join(f"{CN[k]} {c_temp[k]:.1f}도" for k in CITY),
               "여름과 겨울의 기억이 강해서 연평균은 감이 잘 안 옵니다."),
        choice("c5", "1월 밤이 더 추운 도시는?",
               ["서울", "도쿄"], colder,
               f"1월 평균 최저기온 서울 {c_jan['seoul']:.1f}도 · "
               f"도쿄 {c_jan['tokyo']:.1f}도",
               "위도가 비슷해도 대륙의 영향을 받는 도시가 훨씬 춥습니다."),
    ],
    caveat="ERA5 재분석 값이고, 도시별로 관측소 위치와 기준이 다릅니다.")

# ── 9. 지진 ──────────────────────────────────────────────────────
Q = [f["properties"] for f in load_json("quakes.geojson")["features"]]
QK = [f["properties"] for f in load_json("quakes_korea.geojson")["features"]]
n_years = 25
per_year = len(Q) / n_years
m7 = sum(1 for p in Q if p["mag"] >= 7.0) / n_years
biggest = max(Q, key=lambda p: p["mag"])


def region(place):
    return (place or "").split(",")[-1].strip()


top_region = Counter(region(p["place"]) for p in Q).most_common(1)[0]
region_ko = {"Japan": "일본", "Indonesia": "인도네시아", "Chile": "칠레",
             "Philippines": "필리핀"}
kr_band = ("50건 미만" if len(QK) < 50 else "50~150건" if len(QK) <= 150
           else "150~400건" if len(QK) <= 400 else "400건 이상")

topic(
    "quakes", "🌎", "지진은 얼마나 자주",
    "2000~2024년 전 세계 지진 기록",
    "USGS 지진 카탈로그", "https://earthquake.usgs.gov/",
    [
        slider("q1", "규모 5.5 이상 지진은 전 세계에서 1년에 몇 번쯤 일어날까요?",
               per_year, "회", 50, 1200, 50,
               f"2000~2024년 {len(Q):,}건 ÷ {n_years}년 = "
               f"연평균 {per_year:.0f}회",
               "뉴스에 나오는 지진만 세면 실제보다 훨씬 적게 잡게 됩니다."),
        slider("q2", "규모 7.0 이상은 1년에 몇 번쯤일까요?",
               m7, "회", 0, 40, 1,
               f"2000~2024년 규모 7.0 이상 "
               f"{sum(1 for p in Q if p['mag'] >= 7.0)}건, 연평균 {m7:.1f}회",
               "규모는 로그 척도입니다. 0.5만 올라가도 횟수가 크게 줄어듭니다."),
        choice("q3", "규모 5.5 이상 지진이 가장 자주 기록된 나라는?",
               ["일본", "인도네시아", "칠레", "필리핀"],
               region_ko.get(top_region[0], "인도네시아"),
               f"1위 {top_region[0]} {top_region[1]:,}건",
               "지진 하면 떠오르는 나라와 실제로 가장 많이 기록되는 곳은 "
               "다를 수 있습니다."),
        slider("q4", "2000년 이후 기록된 가장 큰 지진의 규모는?",
               biggest["mag"], "", 7.0, 9.9, 0.1,
               f"규모 {biggest['mag']} · "
               f"{dt.datetime.fromtimestamp(biggest['time'] / 1000, dt.UTC):%Y-%m-%d} "
               f"{biggest['place']}",
               "규모 9는 8보다 약 32배 큰 에너지입니다."),
        choice("q5", "한반도 주변(위도 33~39.5도)에서 25년간 기록된 규모 3.0 이상 지진은?",
               ["50건 미만", "50~150건", "150~400건", "400건 이상"], kr_band,
               f"USGS 기준 {len(QK)}건. 이 관측망은 작은 지진을 모두 잡지는 "
               f"못하므로 기상청 집계와 다릅니다",
               "'어느 기관이 센 숫자인가'를 확인하지 않으면 같은 현상도 다른 "
               "값이 됩니다."),
    ],
    caveat="USGS 카탈로그는 작은 지진을 모두 담지 못합니다. 한반도 지진은 "
           "기상청 집계가 더 많습니다.")

# ── 10. 수명 ─────────────────────────────────────────────────────
le = [r for r in load_csv("life_expectancy.csv") if r["life_expectancy_0"]]
l_latest = max(int(r["year"]) for r in le if r["code"] == "KOR")
l_cur = owid_countries(le, l_latest, "life_expectancy_0")
kor_l = l_cur["South Korea"]
l_rank = sorted(l_cur.items(), key=lambda kv: -kv[1])
kor_l_rank = [k for k, _ in l_rank].index("South Korea") + 1
_kle = {r["year"]: float(r["life_expectancy_0"]) for r in le if r["code"] == "KOR"}
kor_1950, kor_1953, kor_1955 = _kle["1950"], _kle["1953"], _kle["1955"]
wld = next(float(r["life_expectancy_0"]) for r in le
           if r["code"] == "OWID_WRL" and int(r["year"]) == l_latest)
trio_l = {c: l_cur[c] for c in ("South Korea", "Japan", "United States")
          if c in l_cur}
top_l = max(trio_l, key=trio_l.get)
name_l = {"South Korea": "한국", "Japan": "일본", "United States": "미국"}

topic(
    "life", "🩺", "얼마나 오래 사나",
    "나라별 기대수명 1950~현재",
    "Our World in Data", "https://ourworldindata.org/grapher/life-expectancy",
    [
        slider("l1", f"{l_latest}년 한국의 기대수명은?",
               kor_l, "세", 60, 95, 1,
               f"{l_latest}년 한국 {kor_l:.1f}세",
               "기대수명은 '지금 태어난 아이가 평균적으로 살 햇수'입니다. "
               "지금 살아 있는 사람의 예상 수명과는 다릅니다."),
        slider("l2", f"기대수명이 긴 순으로 세면 한국은 {len(l_cur)}곳 중 몇 위일까요?",
               kor_l_rank, "위", 1, 60, 1,
               f"{l_latest}년 {len(l_cur)}곳 중 {kor_l_rank}위 "
               f"(1위 {l_rank[0][0]} {l_rank[0][1]:.1f}세)",
               "상위권인 것은 맞지만 몇 위인지는 대개 크게 빗나갑니다."),
        slider("l3", "1950년 한국의 기대수명은?",
               kor_1950, "세", 20, 70, 1,
               f"1950년 {kor_1950:.1f}세. 한국전쟁 기간의 사망이 반영된 값이라 "
               f"1953년 {kor_1953:.1f}세, 1955년 {kor_1955:.1f}세로 빠르게 "
               f"회복합니다. {l_latest}년은 {kor_l:.1f}세",
               "숫자가 튀면 사건을 의심해야 합니다. 이 값은 오류가 아니라 "
               "전쟁의 기록입니다."),
        choice("l4", "한국·일본·미국 중 기대수명이 가장 긴 나라는?",
               ["한국", "일본", "미국"], name_l[top_l],
               " · ".join(f"{name_l[c]} {trio_l[c]:.1f}세" for c in trio_l),
               "가장 잘사는 나라가 가장 오래 사는 나라는 아닙니다."),
        slider("l5", f"{l_latest}년 세계 평균 기대수명은?",
               wld, "세", 50, 90, 1,
               f"{l_latest}년 세계 평균 {wld:.1f}세 · 한국 {kor_l:.1f}세",
               "내가 사는 곳의 수준을 세계 평균으로 착각하기 쉽습니다."),
    ])


if __name__ == "__main__":
    main()
