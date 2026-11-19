#!/usr/bin/env python3
"""Animated black "cyber-ops terminal" GitHub stats card (SVG), v2.

Usage:
    GITHUB_TOKEN=ghp_xxx python generate_stats.py     # live data
    python generate_stats.py --sample                 # preview with fake numbers

Env:
    GH_USER          GitHub username (default: ExcellenceOseagwina)
    TZ_OFFSET_HOURS  Offset for "commits by hour" (default: 1 = Africa/Lagos)
    OUT              Output path (default: stats.svg)

Standard library only. Public data needs no special token scopes
(the built-in Actions GITHUB_TOKEN is enough).

Layout (1200 wide):
    A  title bar / typed command
    B  contributions | current streak | longest streak
    C  whoami (profile details) | stats --summary
    D  contribution heatmap (26 weeks) | commits by hour
    E  langs by repo | langs by commit | langs by size
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from collections import Counter
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "ExcellenceOseagwina")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
TZ = float(os.environ.get("TZ_OFFSET_HOURS", "1"))
OUT = os.environ.get("OUT", "stats.svg")
SAMPLE = "--sample" in sys.argv

# ---- palette: true black base, terminal green primary, cyan secondary, red/amber status
BG, PANEL = "#000000", "#04080B"
GREEN, CYAN, RED, AMBER = "#00FF9C", "#00E5FF", "#FF2E63", "#FFB000"
TEXT, MUTED = "#D4F7EA", "#6F8A83"
MONO = "'JetBrains Mono','Fira Code','Cascadia Code','SF Mono',Consolas,'Courier New',monospace"

FALLBACK = ["#00E5FF", "#FFB000", "#FF2E63", "#00FF9C", "#B388FF", "#FF7A00"]
KNOWN = {
    "Python": "#00E5FF", "JavaScript": "#FFD400", "TypeScript": "#3B82F6",
    "C": "#94A3B8", "C++": "#FF2E63", "HTML": "#FF5C39", "CSS": "#B388FF",
    "Jupyter Notebook": "#FF7A00", "Shell": "#00FF9C", "PHP": "#8892BF",
    "Go": "#00ADD8", "Rust": "#FF9E64", "Java": "#FFB000",
}
HEAT = ["#FFFFFF0F", "#065F46", "#00A86B", "#00FF9C", "#C8FFE9"]


# ----------------------------------------------------------------- data ----
def gql(query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "stats-card"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
    if "errors" in out:
        raise SystemExit(f"GraphQL error: {out['errors']}")
    return out["data"]


def fetch_live():
    if not TOKEN:
        raise SystemExit("Set GITHUB_TOKEN (or run with --sample for a preview).")
    base = gql("""query($l:String!){user(login:$l){
        id name bio location createdAt
        followers{totalCount} following{totalCount}
        repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC){totalCount}
    }}""", {"l": USER})["user"]

    created = dt.datetime.fromisoformat(base["createdAt"].replace("Z", "+00:00"))
    today = dt.datetime.now(dt.timezone.utc)
    days = {}
    for year in range(created.year, today.year + 1):  # API allows 1 year per call
        d = gql("""query($l:String!,$f:DateTime!,$t:DateTime!){user(login:$l){
            contributionsCollection(from:$f,to:$t){contributionCalendar{
              weeks{contributionDays{date contributionCount}}}}}}""",
                {"l": USER, "f": f"{year}-01-01T00:00:00Z", "t": f"{year}-12-31T23:59:59Z"})
        for w in d["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for day in w["contributionDays"]:
                days[day["date"]] = day["contributionCount"]

    repos, cursor = [], None
    while True:
        d = gql("""query($l:String!,$u:ID!,$c:String){user(login:$l){
            repositories(first:50,after:$c,ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC){
              pageInfo{hasNextPage endCursor}
              nodes{name stargazerCount primaryLanguage{name color}
                languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}
                defaultBranchRef{target{... on Commit{
                  history(first:100,author:{id:$u}){totalCount nodes{committedDate}}}}}}}}}""",
                {"l": USER, "u": base["id"], "c": cursor})["user"]["repositories"]
        repos += d["nodes"]
        if not d["pageInfo"]["hasNextPage"]:
            break
        cursor = d["pageInfo"]["endCursor"]
    return base, days, repos


def sample_data():
    base = {"name": "Sample Name", "bio": "SAMPLE DATA - run with a token for real numbers",
            "location": "Nigeria", "createdAt": "2023-01-10T00:00:00Z",
            "followers": {"totalCount": 12}, "following": {"totalCount": 20},
            "repositories": {"totalCount": 14}}
    today = dt.date.today()
    days = {}
    for i in range(400):
        d = today - dt.timedelta(days=i)
        days[d.isoformat()] = 0 if (i % 9 == 4 or i > 330) else (i * 7) % 6 + 1
    langs = [("Python", 5), ("JavaScript", 3), ("C", 2), ("HTML", 2), ("Jupyter Notebook", 2)]
    repos = []
    for n, (lang, k) in enumerate(langs):
        for j in range(k):
            hrs = [dt.datetime(2026, 1, 1, (n * 5 + j * 3 + h) % 24, 0).isoformat() + "Z"
                   for h in range(6 + n)]
            repos.append({
                "name": f"{lang}-{j}", "stargazerCount": n % 3,
                "primaryLanguage": {"name": lang, "color": None},
                "languages": {"edges": [{"size": 9000 * (6 - n) + j * 500,
                                         "node": {"name": lang, "color": None}}]},
                "defaultBranchRef": {"target": {"history": {
                    "totalCount": len(hrs), "nodes": [{"committedDate": h} for h in hrs]}}},
            })
    return base, days, repos


# ------------------------------------------------------------- analysis ----
def streaks(days):
    today = dt.date.today()
    runs, start, last, run = [], None, None, 0
    for d, c in sorted(days.items()):
        if dt.date.fromisoformat(d) > today:
            break
        if c > 0:
            if run == 0:
                start = d
            run += 1
            last = d
        else:
            if run:
                runs.append((run, start, last))
            run = 0
    if run:
        runs.append((run, start, last))
    cur = (0, None, None)
    if runs and (today - dt.date.fromisoformat(runs[-1][2])).days <= 1:
        cur = runs[-1]
    longest = max(runs, key=lambda r: r[0]) if runs else (0, None, None)
    return cur, longest


def fmt_date(s):
    if not s:
        return "-"
    d = dt.date.fromisoformat(s)
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def pct_rows(counter, n=5):
    total = sum(counter.values()) or 1
    rows = counter.most_common(n)
    rest = total - sum(v for _, v in rows)
    out = [(k, v / total * 100) for k, v in rows]
    if rest > 0:
        out.append(("Other", rest / total * 100))
    return out


def analyse(base, days, repos):
    by_repo, by_commit, by_bytes, hours = Counter(), Counter(), Counter(), Counter()
    colors, stars, commits = {}, 0, 0
    for r in repos:
        stars += r["stargazerCount"]
        pl = r["primaryLanguage"]
        lang = pl["name"] if pl else "Other"
        if pl and pl["color"]:
            colors.setdefault(lang, pl["color"])
        by_repo[lang] += 1
        for e in r["languages"]["edges"]:
            by_bytes[e["node"]["name"]] += e["size"]
            if e["node"]["color"]:
                colors.setdefault(e["node"]["name"], e["node"]["color"])
        h = ((r.get("defaultBranchRef") or {}).get("target") or {}).get("history") or {}
        n = h.get("totalCount", 0)
        by_commit[lang] += n
        commits += n
        for node in h.get("nodes", []):
            t = dt.datetime.fromisoformat(node["committedDate"].replace("Z", "+00:00"))
            hours[int((t.hour + TZ) % 24)] += 1
    cur, longest = streaks(days)
    created = dt.datetime.fromisoformat(base["createdAt"].replace("Z", "+00:00"))
    today = dt.date.today()
    past = {d: c for d, c in days.items() if dt.date.fromisoformat(d) <= today}
    busiest = max(past.items(), key=lambda kv: kv[1]) if past else (None, 0)
    return dict(
        total=sum(past.values()), days=past, cur=cur, longest=longest, busiest=busiest,
        by_repo=pct_rows(by_repo), by_commit=pct_rows(by_commit),
        by_bytes=pct_rows(by_bytes, 6), hours=[hours.get(h, 0) for h in range(24)],
        colors=colors, stars=stars, commits=commits,
        since=created.strftime("%b %Y"), first=min(past) if past else None,
    )


# --------------------------------------------------------------- render ----
def color(a, name, i):
    if name == "Other":
        return "#64748B"
    return KNOWN.get(name) or a["colors"].get(name) or FALLBACK[i % len(FALLBACK)]


def panel(x, y, w, h, title, body, delay, accent=GREEN):
    """Terminal window: dark glass, glowing corner brackets, `// title` label."""
    L = 14
    corners = (f"M{x},{y + L} V{y} H{x + L} M{x + w - L},{y} H{x + w} V{y + L} "
               f"M{x + w},{y + h - L} V{y + h} H{x + w - L} M{x + L},{y + h} H{x} V{y + h - L}")
    return (f'<g class="fade" style="animation-delay:{delay:.2f}s">'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{PANEL}" fill-opacity=".92" '
            f'stroke="{accent}" stroke-opacity=".22"/>'
            f'<path d="{corners}" fill="none" stroke="{accent}" stroke-width="2" filter="url(#glow)"/>'
            f'<text x="{x + 22}" y="{y + 31}" font-size="13" font-weight="700" fill="{accent}">'
            f'// {escape(title)}</text>'
            f'<circle class="pulse" cx="{x + w - 22}" cy="{y + 27}" r="3" fill="{accent}"/>'
            f'<line x1="{x + 22}" y1="{y + 43}" x2="{x + w - 22}" y2="{y + 43}" stroke="{accent}" '
            f'stroke-opacity=".16" stroke-dasharray="2 4"/>'
            f'{body}</g>')


def donut(a, rows, cx, cy, r=46, w=18, delay=0.6):
    circ = 2 * 3.14159265 * r
    parts = [f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#fff" '
             f'stroke-opacity=".06" stroke-width="{w}"/>']
    off = 0.0
    for i, (name, p) in enumerate(rows):
        ln = max(p / 100 * circ - 2, 0.5)
        parts.append(
            f'<circle class="seg" cx="{cx}" cy="{cy}" r="{r}" fill="none" '
            f'stroke="{color(a, name, i)}" stroke-width="{w}" '
            f'stroke-dasharray="{ln:.2f} {circ:.2f}" stroke-dashoffset="{-off:.2f}" '
            f'transform="rotate(-90 {cx} {cy})" style="animation-delay:{delay + i * .18:.2f}s"/>')
        off += p / 100 * circ
    if rows:
        parts.append(f'<text x="{cx}" y="{cy + 3}" text-anchor="middle" font-size="19" '
                     f'font-weight="800" fill="{TEXT}">{rows[0][1]:.0f}%</text>'
                     f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" font-size="9.5" '
                     f'fill="{MUTED}">{escape(rows[0][0][:10])}</text>')
    return "".join(parts)


def legend(a, rows, x, y):
    out = []
    for i, (name, p) in enumerate(rows):
        yy = y + i * 27
        out.append(f'<rect x="{x}" y="{yy - 9}" width="9" height="9" rx="1" fill="{color(a, name, i)}"/>'
                   f'<text x="{x + 18}" y="{yy}" font-size="13" fill="{TEXT}">{escape(name[:14])}</text>'
                   f'<text x="{x + 176}" y="{yy}" text-anchor="end" font-size="13" '
                   f'font-weight="700" fill="{MUTED}">{p:.0f}%</text>')
    return "".join(out)


def chronotype(hours):
    if not any(hours):
        return "no data"
    p = max(range(24), key=lambda h: hours[h])
    if 5 <= p < 12:
        return "early bird"
    if 12 <= p < 18:
        return "daytime builder"
    if 18 <= p < 22:
        return "evening hacker"
    return "night owl"


def heatmap(a, x0, y0, weeks=26, step=18, size=14):
    """GitHub-style contribution grid for the last `weeks` weeks (Sunday-first)."""
    today = dt.date.today()
    start = today - dt.timedelta(days=(today.weekday() + 1) % 7 + (weeks - 1) * 7)
    vals = [a["days"].get((start + dt.timedelta(days=i)).isoformat(), 0) for i in range(weeks * 7)]
    mx = max(vals) or 1
    out, last_month = [], None
    for w in range(weeks):
        col = start + dt.timedelta(days=w * 7)
        if col.month != last_month:
            out.append(f'<text x="{x0 + w * step}" y="{y0 - 9}" font-size="10" fill="{MUTED}">{col.strftime("%b")}</text>')
            last_month = col.month
        for d in range(7):
            date = start + dt.timedelta(days=w * 7 + d)
            if date > today:
                continue
            v = vals[w * 7 + d]
            lvl = 0 if v == 0 else 1 + min(int(v / mx * 3.999), 3)
            out.append(f'<rect class="cell" x="{x0 + w * step}" y="{y0 + d * step}" width="{size}" '
                       f'height="{size}" rx="2" fill="{HEAT[lvl]}" '
                       f'style="animation-delay:{.9 + w * .03:.2f}s"/>')
    for d, lab in ((1, "M"), (3, "W"), (5, "F")):
        out.append(f'<text x="{x0 - 16}" y="{y0 + d * step + 11}" font-size="10" fill="{MUTED}">{lab}</text>')
    # legend
    lx = x0 + weeks * step - 5 * 18 - 70
    out.append(f'<text x="{lx}" y="{y0 + 7 * step + 14}" font-size="10" fill="{MUTED}">less</text>')
    for i, c in enumerate(HEAT):
        out.append(f'<rect x="{lx + 32 + i * 16}" y="{y0 + 7 * step + 5}" width="11" height="11" rx="2" fill="{c}"/>')
    out.append(f'<text x="{lx + 32 + 5 * 16 + 4}" y="{y0 + 7 * step + 14}" font-size="10" fill="{MUTED}">more</text>')
    return "".join(out)


STYLE = """
text{font-family:__MONO__;font-variant-numeric:tabular-nums}
.fade{animation:fade .7s cubic-bezier(.2,.8,.2,1) both}
@keyframes fade{from{opacity:0;transform:translateY(8px)}}
.b{transform-box:fill-box;transform-origin:50% 100%;animation:grow .9s cubic-bezier(.2,.8,.2,1) both}
@keyframes grow{from{transform:scaleY(0)}}
.hb{transform-box:fill-box;transform-origin:0 50%;animation:growx .9s cubic-bezier(.2,.8,.2,1) both}
@keyframes growx{from{transform:scaleX(0)}}
.cell{animation:cell .5s ease-out both}
@keyframes cell{from{opacity:0}}
.seg{animation:draw .9s cubic-bezier(.2,.8,.2,1) both}
@keyframes draw{from{stroke-dasharray:0 400}}
.ring{animation:ring 1.4s cubic-bezier(.2,.8,.2,1) both}
@keyframes ring{from{stroke-dashoffset:302}}
.spin{transform-box:fill-box;transform-origin:center;animation:spin 18s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.spin-r{transform-box:fill-box;transform-origin:center;animation:spin 28s linear infinite reverse}
.scan{animation:scan 7s linear infinite}
@keyframes scan{from{transform:translateY(-90px)}to{transform:translateY(__H__px)}}
.blink{animation:blink 1.05s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
.pulse{animation:pulse 2s ease-in-out infinite}
@keyframes pulse{50%{opacity:.25}}
.type{animation:type 2.4s steps(__N__) .2s both}
@keyframes type{from{width:0}}
.sweep{animation:sweep 5s ease-in-out infinite}
@keyframes sweep{0%,100%{opacity:.25}50%{opacity:1}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
""".replace("__MONO__", MONO)


def render(base, a, sample):
    H = 1042
    cmd = f"$ ./gh-stats --user {USER} --mode=full"
    s = []
    s.append(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {H}" width="1200" height="{H}" role="img" aria-labelledby="t d">
<title id="t">GitHub stats for {escape(USER)}</title>
<desc id="d">Contributions, streaks, profile details, activity heatmap, commits by hour and top languages by repository, by commit and by code size.</desc>
<style>{STYLE.replace("__H__", str(H)).replace("__N__", str(len(cmd) + 1))}</style>
<defs>
<pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="{GREEN}" stroke-opacity=".045"/></pattern>
<radialGradient id="vig" cx=".5" cy=".45" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".85"/></radialGradient>
<radialGradient id="gA" cx=".08" cy=".02" r=".5"><stop offset="0" stop-color="{GREEN}" stop-opacity=".13"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></radialGradient>
<radialGradient id="gB" cx=".95" cy=".98" r=".45"><stop offset="0" stop-color="{CYAN}" stop-opacity=".11"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
<linearGradient id="scang" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GREEN}" stop-opacity="0"/><stop offset=".92" stop-color="{GREEN}" stop-opacity=".07"/><stop offset="1" stop-color="{GREEN}" stop-opacity=".4"/></linearGradient>
<pattern id="lines" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" fill-opacity=".28"/></pattern>
<linearGradient id="ringg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{GREEN}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
<linearGradient id="bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CYAN}" stop-opacity=".9"/><stop offset="1" stop-color="{CYAN}" stop-opacity=".15"/></linearGradient>
<linearGradient id="peak" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GREEN}"/><stop offset="1" stop-color="{GREEN}" stop-opacity=".25"/></linearGradient>
<filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<clipPath id="frame"><rect width="1200" height="{H}" rx="14"/></clipPath>
<clipPath id="typeclip"><rect class="type" x="118" y="34" width="{len(cmd) * 10 + 30}" height="30"/></clipPath>
</defs>
<g clip-path="url(#frame)">
<rect width="1200" height="{H}" fill="{BG}"/>
<rect width="1200" height="{H}" fill="url(#grid)"/>
<rect width="1200" height="{H}" fill="url(#gA)"/>
<rect width="1200" height="{H}" fill="url(#gB)"/>
</g>
<rect x=".5" y=".5" width="1199" height="{H - 1}" rx="14" fill="none" stroke="{GREEN}" stroke-opacity=".18"/>''')

    # --- A: terminal title bar
    s.append(f'''<g class="fade">
<rect x="40" y="24" width="1120" height="56" rx="3" fill="{PANEL}" stroke="{GREEN}" stroke-opacity=".22"/>
<circle cx="64" cy="52" r="5" fill="{RED}"/><circle cx="84" cy="52" r="5" fill="{AMBER}"/><circle cx="104" cy="52" r="5" fill="{GREEN}"/>
<g clip-path="url(#typeclip)"><text x="124" y="58" font-size="17" font-weight="700" fill="{GREEN}" filter="url(#glow)">{escape(cmd)}<tspan class="blink" fill="{GREEN}">█</tspan></text></g>''')
    if sample:
        s.append(f'<text x="1138" y="57" text-anchor="end" font-size="13" font-weight="700" fill="{AMBER}">'
                 f'[ PREVIEW: SAMPLE DATA ]</text>')
    else:
        s.append(f'<circle class="pulse" cx="1000" cy="52" r="5" fill="{GREEN}" filter="url(#glow)"/>'
                 f'<text x="1138" y="57" text-anchor="end" font-size="13" font-weight="700" fill="{GREEN}">'
                 f'SESSION ACTIVE</text>')
    s.append("</g>")

    # --- B: contributions / current streak / longest streak
    ay, ah = 104, 190
    recent = [a["days"].get((dt.date.today() - dt.timedelta(days=27 - i)).isoformat(), 0) for i in range(28)]
    mxr = max(recent) or 1
    spark = "".join(
        f'<rect class="b" x="{90 + i * 9}" y="{ay + 178 - max(v / mxr * 18, 2 if v else 1):.1f}" width="6" '
        f'height="{max(v / mxr * 18, 2 if v else 1):.1f}" fill="{GREEN if v else "#fff"}" '
        f'fill-opacity="{1 if v else .12}" style="animation-delay:{.5 + i * .02:.2f}s"/>'
        for i, v in enumerate(recent))
    body = (f'<text x="62" y="{ay + 112}" font-size="58" font-weight="800" fill="{TEXT}" filter="url(#glow)">{a["total"]:,}</text>'
            f'<text x="62" y="{ay + 138}" font-size="12" fill="{CYAN}">{escape(fmt_date(a["first"]))} → now</text>'
            f'<text x="62" y="{ay + 177}" font-size="11" fill="{MUTED}">28d</text>{spark}')
    s.append(panel(40, ay, 300, ah, "total_contributions", body, .15))

    n, st, en = a["cur"]
    frac = min(n / max(a["longest"][0], 1), 1)
    cx, cy = 510, ay + 124
    active = n > 0
    status_c = GREEN if active else RED
    rng = f"{fmt_date(st)} → {fmt_date(en)}" if n else "no active streak"
    note = ("matches the record" if n and n == a["longest"][0]
            else f"{max(a['longest'][0] - n, 0)} days to beat the record")
    body = (f'<circle class="spin" cx="{cx}" cy="{cy}" r="60" fill="none" stroke="{CYAN}" stroke-opacity=".5" stroke-dasharray="3 9"/>'
            f'<circle class="spin-r" cx="{cx}" cy="{cy}" r="68" fill="none" stroke="{GREEN}" stroke-opacity=".18" stroke-dasharray="14 22"/>'
            f'<circle cx="{cx}" cy="{cy}" r="48" fill="none" stroke="#fff" stroke-opacity=".08" stroke-width="9"/>'
            f'<circle class="ring" cx="{cx}" cy="{cy}" r="48" fill="none" stroke="url(#ringg)" stroke-width="9" '
            f'stroke-linecap="round" stroke-dasharray="301.59" stroke-dashoffset="{301.59 * (1 - frac):.2f}" '
            f'transform="rotate(-90 {cx} {cy})" filter="url(#glow)"/>'
            f'<text x="{cx}" y="{cy + 8}" text-anchor="middle" font-size="32" font-weight="800" fill="{TEXT}">{n}</text>'
            f'<text x="{cx}" y="{cy + 25}" text-anchor="middle" font-size="11" fill="{MUTED}">days</text>'
            f'<circle class="pulse" cx="{cx + 124}" cy="{cy - 37}" r="5" fill="{status_c}" filter="url(#glow)"/>'
            f'<text x="{cx + 138}" y="{cy - 32}" font-size="15" font-weight="700" fill="{status_c}">'
            f'{"STREAK ALIVE" if active else "STREAK BROKEN"}</text>'
            f'<text x="{cx + 124}" y="{cy - 4}" font-size="14" fill="{TEXT}">{escape(rng)}</text>'
            f'<text x="{cx + 124}" y="{cy + 22}" font-size="12.5" fill="{MUTED}">{escape(note)}</text>')
    s.append(panel(360, ay, 480, ah, "current_streak", body, .3, accent=CYAN))

    n2, st2, en2 = a["longest"]
    body = (f'<text x="886" y="{ay + 112}" font-size="58" font-weight="800" fill="{TEXT}" filter="url(#glow)">{n2}</text>'
            f'<text x="{886 + 35 * len(str(n2)) + 12}" y="{ay + 112}" font-size="18" fill="{MUTED}">days</text>'
            f'<text x="886" y="{ay + 138}" font-size="12" fill="{CYAN}">{escape(fmt_date(st2))} → {escape(fmt_date(en2))}</text>'
            f'<rect x="886" y="{ay + 160}" width="228" height="6" rx="3" fill="#fff" fill-opacity=".08"/>'
            f'<rect class="hb" x="886" y="{ay + 160}" width="{228 * frac:.1f}" height="6" rx="3" fill="{GREEN}" filter="url(#glow)"/>'
            f'<text x="886" y="{ay + 181}" font-size="11" fill="{MUTED}">current vs record: {frac * 100:.0f}%</text>')
    s.append(panel(860, ay, 300, ah, "longest_streak", body, .45))

    # --- C: profile details / statistics
    by = 314
    bio = base.get("bio") or "No bio yet"
    bio = bio if len(bio) <= 46 else bio[:45] + "…"
    rows = [("name", base.get("name") or USER), ("user", f"@{USER}"), ("bio", bio),
            ("location", base.get("location") or "-"), ("joined", a["since"]),
            ("network", f'{base["followers"]["totalCount"]} followers · {base["following"]["totalCount"]} following')]
    body = ""
    for i, (k, v) in enumerate(rows):
        y = by + 70 + i * 20
        body += (f'<text x="62" y="{y}" font-size="13" fill="{GREEN}">›</text>'
                 f'<text x="78" y="{y}" font-size="13" fill="{CYAN}">{k}</text>'
                 f'<text x="160" y="{y}" font-size="13" fill="{TEXT}">{escape(str(v))}</text>')
    s.append(panel(40, by, 540, 180, "whoami", body, .6))

    kpis = [(base["repositories"]["totalCount"], "public repos"), (a["stars"], "stars earned"),
            (a["commits"], "commits"), (a["total"], "contributions")]
    body = ""
    for i, (v, lab) in enumerate(kpis):
        x = 626 + i * 132
        body += (f'<text x="{x}" y="{by + 96}" font-size="30" font-weight="800" fill="{TEXT}">{v:,}</text>'
                 f'<text x="{x}" y="{by + 116}" font-size="11" fill="{MUTED}">{escape(lab)}</text>'
                 f'<rect x="{x}" y="{by + 126}" width="40" height="2" fill="{GREEN if i % 2 == 0 else CYAN}" '
                 f'class="sweep" style="animation-delay:{i * .4:.1f}s"/>')
    top = a["by_bytes"][0][0] if a["by_bytes"] else "-"
    bd, bn = a["busiest"]
    body += (f'<text x="626" y="{by + 156}" font-size="12" fill="{MUTED}">top_language:</text>'
             f'<rect x="716" y="{by + 147}" width="9" height="9" rx="1" fill="{color(a, top, 0)}"/>'
             f'<text x="732" y="{by + 156}" font-size="12" font-weight="700" fill="{TEXT}">{escape(top)}</text>'
             f'<text x="850" y="{by + 156}" font-size="12" fill="{MUTED}">busiest_day:</text>'
             f'<text x="942" y="{by + 156}" font-size="12" font-weight="700" fill="{TEXT}">'
             f'{bn} <tspan fill="{MUTED}" font-weight="400">on {escape(fmt_date(bd))}</tspan></text>')
    s.append(panel(600, by, 560, 180, "stats --summary", body, .75, accent=CYAN))

    # --- D: heatmap / commits by hour
    dy = 514
    s.append(panel(40, dy, 560, 210, "activity --26w", heatmap(a, 84, dy + 68), .9))

    body = (f'<text x="1138" y="{dy + 53}" text-anchor="end" font-size="11" fill="{MUTED}">'
            f'UTC{TZ:+g} · <tspan fill="{GREEN}" font-weight="700">{chronotype(a["hours"])}</tspan></text>')
    mx = max(a["hours"]) or 1
    base_y, th = dy + 178, 90
    body += f'<line x1="646" y1="{base_y}" x2="1138" y2="{base_y}" stroke="{GREEN}" stroke-opacity=".25"/>'
    for g in (.5, 1):
        body += (f'<line x1="646" y1="{base_y - th * g:.1f}" x2="1138" y2="{base_y - th * g:.1f}" '
                 f'stroke="#fff" stroke-opacity=".05" stroke-dasharray="3 6"/>')
    peaks = set(sorted(range(24), key=lambda h: -a["hours"][h])[:3]) if max(a["hours"]) else set()
    for h, v in enumerate(a["hours"]):
        bh = max(v / mx * th, 2 if v else 0)
        x = 650 + h * 20.4
        is_peak = h in peaks
        extra = ' filter="url(#glow)"' if is_peak else ""
        body += (f'<rect class="b" x="{x:.1f}" y="{base_y - bh:.1f}" width="14" height="{bh:.1f}" rx="2" '
                 f'fill="url(#{"peak" if is_peak else "bar"})"{extra} style="animation-delay:{h * .03:.2f}s"/>')
        if v and is_peak:
            body += (f'<text x="{x + 7:.1f}" y="{base_y - bh - 6:.1f}" text-anchor="middle" '
                     f'font-size="10" fill="{GREEN}">{v}</text>')
        if h % 3 == 0 or h == 23:
            body += (f'<text x="{x + 7:.1f}" y="{base_y + 16}" text-anchor="middle" font-size="10" '
                     f'fill="{MUTED}">{h:02d}h</text>')
    s.append(panel(620, dy, 540, 210, "commits_by_hour", body, 1.0, accent=CYAN))

    # --- E: language panels
    ty = 744
    body = legend(a, a["by_repo"], 66, ty + 80) + donut(a, a["by_repo"], 328, ty + 140)
    s.append(panel(40, ty, 360, 240, "langs --by-repo", body, 1.1, accent=CYAN))
    body = legend(a, a["by_commit"], 446, ty + 80) + donut(a, a["by_commit"], 708, ty + 140, delay=.9)
    s.append(panel(420, ty, 360, 240, "langs --by-commit", body, 1.25))
    body = ""
    for i, (name, p) in enumerate(a["by_bytes"]):
        y = ty + 76 + i * 24
        body += (f'<text x="826" y="{y}" font-size="12" fill="{TEXT}">{escape(name[:14])}</text>'
                 f'<rect x="936" y="{y - 9}" width="150" height="8" rx="1" fill="#fff" fill-opacity=".07"/>'
                 f'<rect class="hb" x="936" y="{y - 9}" width="{max(p * 1.5, 3):.1f}" height="8" rx="1" '
                 f'fill="{color(a, name, i)}" style="animation-delay:{1.4 + i * .1:.1f}s"/>'
                 f'<text x="1134" y="{y}" text-anchor="end" font-size="12" font-weight="700" '
                 f'fill="{MUTED}">{p:.0f}%</text>')
    s.append(panel(800, ty, 360, 240, "langs --by-size", body, 1.4, accent=CYAN))

    # --- footer + global fx (CRT lines, scanline sweep, vignette)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    s.append(f'<text x="40" y="{H - 24}" font-size="11" fill="{MUTED}">[ updated {now} ]  '
             f'<tspan fill="{GREEN}">exit 0</tspan><tspan class="blink" fill="{GREEN}"> █</tspan></text>')
    s.append(f'<g clip-path="url(#frame)" pointer-events="none">'
             f'<rect width="1200" height="{H}" fill="url(#lines)"/>'
             f'<rect class="scan" width="1200" height="90" fill="url(#scang)"/>'
             f'<rect width="1200" height="{H}" fill="url(#vig)"/></g>')
    s.append("</svg>")
    return "\n".join(s)


if __name__ == "__main__":
    data = sample_data() if SAMPLE else fetch_live()
    analysis = analyse(*data)
    svg = render(data[0], analysis, SAMPLE)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {OUT} ({len(svg):,} bytes)")
