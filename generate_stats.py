#!/usr/bin/env python3
"""Generate an animated GitHub stats card (SVG) for one user.

Usage:
    GITHUB_TOKEN=ghp_xxx python generate_stats.py            # live data
    python generate_stats.py --sample                        # preview, fake numbers

Env:
    GH_USER         GitHub username (default: ExcellenceOseagwina)
    TZ_OFFSET_HOURS Offset used for "commits by hour" (default: 1 = Africa/Lagos)
    OUT             Output path (default: stats.svg)

Only the standard library is used. The token needs no special scopes for public
data (the built-in GITHUB_TOKEN of a GitHub Action is enough).
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

FALLBACK_COLORS = ["#4F8EF7", "#F1E05A", "#F34B7D", "#2DD4BF", "#F97316", "#C084FC"]
KNOWN_COLORS = {
    "Python": "#4F8EF7", "JavaScript": "#F1E05A", "TypeScript": "#3178C6",
    "C": "#9AA4B2", "C++": "#F34B7D", "HTML": "#EF4444", "CSS": "#8B5CF6",
    "Jupyter Notebook": "#F97316", "Shell": "#4ADE80", "PHP": "#8892BF",
}


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

    # contributions: one query per calendar year (API limit is 1 year per call)
    created = dt.datetime.fromisoformat(base["createdAt"].replace("Z", "+00:00"))
    today = dt.datetime.now(dt.timezone.utc)
    days = {}
    for year in range(created.year, today.year + 1):
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
        days[d.isoformat()] = 0 if (i % 9 == 4 or i > 330) else (i * 7) % 5 + 1
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
    items = sorted(days.items())
    runs, start, last, run = [], None, None, 0
    for d, c in items:
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
    today = dt.date.today()
    cur = (0, None, None)
    if runs:
        end = dt.date.fromisoformat(runs[-1][2])
        if (today - end).days <= 1:
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
        tgt = (r.get("defaultBranchRef") or {}).get("target") or {}
        h = tgt.get("history") or {}
        n = h.get("totalCount", 0)
        by_commit[lang] += n
        commits += n
        for node in h.get("nodes", []):
            t = dt.datetime.fromisoformat(node["committedDate"].replace("Z", "+00:00"))
            hours[int((t.hour + TZ) % 24)] += 1
    cur, longest = streaks(days)
    created = dt.datetime.fromisoformat(base["createdAt"].replace("Z", "+00:00"))
    return dict(
        total=sum(days.values()), cur=cur, longest=longest,
        by_repo=pct_rows(by_repo), by_commit=pct_rows(by_commit),
        by_bytes=pct_rows(by_bytes, 6), hours=[hours.get(h, 0) for h in range(24)],
        colors=colors, stars=stars, commits=commits,
        since=created.strftime("%b %Y"), first=min(days) if days else None,
    )


# --------------------------------------------------------------- render ----
def color(a, name, i):
    return a["colors"].get(name) or KNOWN_COLORS.get(name) or (
        "#64748B" if name == "Other" else FALLBACK_COLORS[i % len(FALLBACK_COLORS)])


def donut(a, rows, cx, cy, r=52, w=22, delay=0.6):
    circ = 2 * 3.14159265 * r
    parts = [f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#fff" '
             f'stroke-opacity=".07" stroke-width="{w}"/>']
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
        parts.append(f'<text x="{cx}" y="{cy + 2}" text-anchor="middle" font-size="22" '
                     f'font-weight="800" fill="url(#num)">{rows[0][1]:.0f}%</text>'
                     f'<text x="{cx}" y="{cy + 19}" text-anchor="middle" font-size="11" '
                     f'fill="#8B94B3">{escape(rows[0][0][:12])}</text>')
    return "".join(parts)


def legend(a, rows, x, y):
    out = []
    for i, (name, p) in enumerate(rows):
        yy = y + i * 27
        out.append(f'<circle cx="{x}" cy="{yy - 4}" r="5" fill="{color(a, name, i)}"/>'
                   f'<text x="{x + 16}" y="{yy}" font-size="13" fill="#E8ECF8">{escape(name[:16])}</text>'
                   f'<text x="{x + 175}" y="{yy}" text-anchor="end" font-size="13" '
                   f'font-weight="600" fill="#8B94B3">{p:.0f}%</text>')
    return "".join(out)


def tile(x, y, w, h, title, edge=False):
    stroke = 'url(#edge)' if edge else '#FFFFFF'
    op = 1 if edge else .09
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="#fff" '
            f'fill-opacity=".04" stroke="{stroke}" stroke-opacity="{op}" stroke-width="1.2"/>'
            f'<text x="{x + 26}" y="{y + 38}" font-size="16" font-weight="700" '
            f'fill="#E8ECF8">{escape(title)}</text>')


def render(base, a, sample):
    H = 990
    s = []
    s.append(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {H}" width="1200" height="{H}" role="img" aria-labelledby="t d">
<title id="t">GitHub stats for {escape(USER)}</title>
<desc id="d">Contributions, streaks, profile details, commits by hour and top languages by repository, by commit and by code size.</desc>
<style>
text{{font-family:'Segoe UI Variable Display','Segoe UI',Inter,system-ui,-apple-system,Roboto,Arial,sans-serif;font-variant-numeric:tabular-nums}}
.b{{transform-box:fill-box;transform-origin:50% 100%;animation:grow .9s cubic-bezier(.2,.8,.2,1) both}}
@keyframes grow{{from{{transform:scaleY(0)}}}}
.seg{{animation:draw .9s cubic-bezier(.2,.8,.2,1) both}}
@keyframes draw{{from{{stroke-dasharray:0 400}}}}
.ring{{animation:ring 1.4s cubic-bezier(.2,.8,.2,1) both}}
@keyframes ring{{from{{stroke-dashoffset:352}}}}
.fade{{animation:fade .8s ease both}}
@keyframes fade{{from{{opacity:0;transform:translateY(6px)}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0A0F1F"/><stop offset="1" stop-color="#0F1530"/></linearGradient>
<radialGradient id="gA" cx=".12" cy=".05" r=".55"><stop offset="0" stop-color="#7C5CFF" stop-opacity=".28"/><stop offset="1" stop-color="#7C5CFF" stop-opacity="0"/></radialGradient>
<radialGradient id="gB" cx=".92" cy=".98" r=".5"><stop offset="0" stop-color="#22D3EE" stop-opacity=".2"/><stop offset="1" stop-color="#22D3EE" stop-opacity="0"/></radialGradient>
<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#fff" fill-opacity=".055"/></pattern>
<linearGradient id="num" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#C9D2F5"/></linearGradient>
<linearGradient id="ringg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5EEAD4"/><stop offset=".55" stop-color="#818CF8"/><stop offset="1" stop-color="#C084FC"/></linearGradient>
<linearGradient id="bar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8B9BFF"/><stop offset="1" stop-color="#4338CA" stop-opacity=".75"/></linearGradient>
<linearGradient id="peak" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7CF3E0"/><stop offset="1" stop-color="#6366F1"/></linearGradient>
<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5EEAD4" stop-opacity=".55"/><stop offset=".5" stop-color="#818CF8" stop-opacity=".35"/><stop offset="1" stop-color="#C084FC" stop-opacity=".55"/></linearGradient>
<filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<clipPath id="frame"><rect width="1200" height="{H}" rx="28"/></clipPath>
</defs>
<g clip-path="url(#frame)"><rect width="1200" height="{H}" fill="url(#bg)"/><rect width="1200" height="{H}" fill="url(#dots)"/><rect width="1200" height="{H}" fill="url(#gA)"/><rect width="1200" height="{H}" fill="url(#gB)"/></g>
<rect x=".5" y=".5" width="1199" height="{H - 1}" rx="28" fill="none" stroke="#fff" stroke-opacity=".08"/>
<text x="40" y="54" font-size="27" font-weight="800" fill="#E8ECF8" letter-spacing="-.4">GitHub stats</text>
<text x="40" y="78" font-size="14" fill="#8B94B3">@{escape(USER)}</text>''')

    if sample:
        s.append('<text x="1160" y="54" text-anchor="end" font-size="13" font-weight="700" '
                 'fill="#F97316">PREVIEW - SAMPLE NUMBERS, NOT REAL DATA</text>')

    # --- row A: contributions / current streak / longest streak
    s.append(tile(40, 96, 300, 190, "Total contributions"))
    s.append(f'<text class="fade" x="66" y="215" font-size="68" font-weight="800" fill="url(#num)">{a["total"]:,}</text>')
    s.append(f'<text x="66" y="260" font-size="13" font-weight="600" fill="#5EEAD4">{escape(fmt_date(a["first"]))} to present</text>')

    n, st, en = a["cur"]
    s.append(tile(360, 96, 480, 190, "Current streak", edge=True))
    frac = min(n / max(a["longest"][0], 1), 1)
    s.append('<circle cx="472" cy="206" r="56" fill="none" stroke="#fff" stroke-opacity=".1" stroke-width="10"/>'
             f'<circle class="ring" cx="472" cy="206" r="56" fill="none" stroke="url(#ringg)" stroke-width="10" '
             f'stroke-linecap="round" stroke-dasharray="351.86" stroke-dashoffset="{351.86 * (1 - frac):.2f}" '
             'transform="rotate(-90 472 206)" filter="url(#glow)"/>'
             f'<text x="472" y="214" text-anchor="middle" font-size="40" font-weight="800" fill="url(#num)">{n}</text>'
             '<text x="472" y="234" text-anchor="middle" font-size="12" font-weight="600" fill="#8B94B3">days</text>')
    rng = f"{fmt_date(st)} to {fmt_date(en)}" if n else "No active streak"
    note = "Matches the longest streak" if n and n == a["longest"][0] else \
        f"{max(a['longest'][0] - n, 0)} days from the record"
    s.append(f'<text x="574" y="180" font-size="19" font-weight="700" fill="#E8ECF8">Keep it going</text>'
             f'<text x="574" y="206" font-size="14" font-weight="600" fill="#5EEAD4">{escape(rng)}</text>'
             f'<text x="574" y="234" font-size="13" fill="#8B94B3">{escape(note)}</text>')

    n2, st2, en2 = a["longest"]
    s.append(tile(860, 96, 300, 190, "Longest streak"))
    s.append(f'<text class="fade" x="886" y="215" font-size="68" font-weight="800" fill="url(#num)">{n2}</text>'
             f'<text x="{886 + 40 * len(str(n2)) + 12}" y="215" font-size="20" font-weight="600" fill="#8B94B3">days</text>'
             f'<text x="886" y="260" font-size="13" font-weight="600" fill="#5EEAD4">'
             f'{escape(fmt_date(st2))} to {escape(fmt_date(en2))}</text>')

    # --- row B: profile details / statistics
    s.append(tile(40, 306, 540, 180, "Profile details"))
    bio = (base.get("bio") or "No bio yet")[:64]
    rows = [("Name", base.get("name") or USER), ("Bio", bio),
            ("Location", base.get("location") or "-"), ("Joined GitHub", a["since"]),
            ("Followers / following", f'{base["followers"]["totalCount"]} / {base["following"]["totalCount"]}')]
    for i, (k, v) in enumerate(rows):
        y = 372 + i * 22
        s.append(f'<text x="66" y="{y}" font-size="13" fill="#8B94B3">{k}</text>'
                 f'<text x="230" y="{y}" font-size="13" font-weight="600" fill="#E8ECF8">{escape(str(v))}</text>')

    s.append(tile(600, 306, 560, 180, "GitHub statistics"))
    kpis = [(base["repositories"]["totalCount"], "Public repos"), (a["stars"], "Stars earned"),
            (a["commits"], "Commits"), (a["total"], "Contributions")]
    for i, (v, lab) in enumerate(kpis):
        x = 626 + i * 132
        s.append(f'<text x="{x}" y="415" font-size="34" font-weight="800" fill="url(#num)">{v:,}</text>'
                 f'<text x="{x}" y="437" font-size="11" fill="#8B94B3">{escape(lab[:26])}</text>')
    s.append(f'<text x="626" y="468" font-size="12" fill="#5EEAD4">Most used language: '
             f'{escape(a["by_bytes"][0][0]) if a["by_bytes"] else "-"}</text>')

    # --- row C: commits by hour
    s.append(tile(40, 506, 1120, 200, "Commits by hour"))
    s.append(f'<text x="1134" y="544" text-anchor="end" font-size="13" fill="#8B94B3">UTC{TZ:+g}</text>')
    mx = max(a["hours"]) or 1
    base_y, top = 672, 70
    s.append(f'<line x1="70" y1="{base_y}" x2="1134" y2="{base_y}" stroke="#fff" stroke-opacity=".16"/>')
    peaks = set(sorted(range(24), key=lambda h: -a["hours"][h])[:3]) if max(a["hours"]) else set()
    for h, v in enumerate(a["hours"]):
        bh = max(v / mx * top, 2 if v else 0)
        x = 80 + h * 43.5
        s.append(f'<rect class="b" x="{x:.1f}" y="{base_y - bh:.1f}" width="26" height="{bh:.1f}" rx="5" '
                 f'fill="url(#{"peak" if h in peaks else "bar"})" style="animation-delay:{h * .03:.2f}s"/>')
        if h % 3 == 0 or h == 23:
            s.append(f'<text x="{x + 13:.1f}" y="{base_y + 18}" text-anchor="middle" font-size="11" '
                     f'fill="#8B94B3">{h:02d}</text>')

    # --- row D: three language tiles
    ty = 726
    s.append(tile(40, ty, 360, 240, "Top languages by repository"))
    s.append(legend(a, a["by_repo"], 66, ty + 80))
    s.append(donut(a, a["by_repo"], 330, ty + 150))
    s.append(tile(420, ty, 360, 240, "Top languages by commit"))
    s.append(legend(a, a["by_commit"], 446, ty + 80))
    s.append(donut(a, a["by_commit"], 710, ty + 150, delay=.9))
    s.append(tile(800, ty, 360, 240, "Most used languages (code size)"))
    for i, (name, p) in enumerate(a["by_bytes"]):
        y = ty + 76 + i * 25
        s.append(f'<text x="826" y="{y}" font-size="12" fill="#E8ECF8">{escape(name[:20])}</text>'
                 f'<rect x="960" y="{y - 10}" width="150" height="9" rx="4.5" fill="#fff" fill-opacity=".07"/>'
                 f'<rect class="b" x="960" y="{y - 10}" width="{max(p * 1.3, 3):.1f}" height="9" rx="4.5" '
                 f'fill="{color(a, name, i)}" style="transform-origin:0 50%;animation:none"/>'
                 f'<text x="1134" y="{y}" text-anchor="end" font-size="12" font-weight="600" '
                 f'fill="#8B94B3">{p:.0f}%</text>')
    s.append("</svg>")
    return "\n".join(s)


if __name__ == "__main__":
    data = sample_data() if SAMPLE else fetch_live()
    analysis = analyse(*data)
    svg = render(data[0], analysis, SAMPLE)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {OUT} ({len(svg):,} bytes)")
