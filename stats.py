#!/usr/bin/env python3
"""Genera github-stats.svg (actividad, racha y lenguajes) con la API GraphQL de GitHub."""
import html, json, os, sys, urllib.request
from datetime import date

USER = os.environ.get("GH_USER", "RubenMeju")
TOKEN = os.environ.get("GH_TOKEN")
OUT = os.environ.get("OUT", "github-stats.svg")

QUERY = """
query($login:String!){ user(login:$login){
  repositories(ownerAffiliations:OWNER,isFork:false,first:100){
    totalCount
    nodes{ stargazerCount languages(first:10,orderBy:{field:SIZE,direction:DESC}){ edges{ size node{ name color } } } }
  }
  pullRequests{ totalCount }
  issues{ totalCount }
  contributionsCollection{
    totalCommitContributions
    contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } }
  }
}}"""

def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "stats-card"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(json.dumps(data["errors"]))
    return data["data"]["user"]

def demo():
    days = [{"date": f"2026-01-{d:02d}", "contributionCount": (d % 4)} for d in range(1, 29)]
    return {
        "repositories": {"totalCount": 12, "nodes": [{"stargazerCount": 3, "languages": {"edges": [
            {"size": 500, "node": {"name": "TypeScript", "color": "#3178c6"}},
            {"size": 300, "node": {"name": "C++", "color": "#f34b7d"}},
            {"size": 200, "node": {"name": "Python", "color": "#3572A5"}}]}}]},
        "pullRequests": {"totalCount": 40}, "issues": {"totalCount": 8},
        "contributionsCollection": {"totalCommitContributions": 900,
            "contributionCalendar": {"totalContributions": 2441, "weeks": [{"contributionDays": days}]}},
    }

def compute(u):
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    today = date.today().isoformat()
    days = sorted((d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"])
    days = [d for d in days if d[0] <= today]
    i = len(days) - 1
    if i >= 0 and days[i][1] == 0:
        i -= 1
    cur = 0
    while i >= 0 and days[i][1] > 0:
        cur += 1
        i -= 1
    best = run = 0
    for _, c in days:
        run = run + 1 if c > 0 else 0
        best = max(best, run)
    langs, stars = {}, 0
    for r in u["repositories"]["nodes"]:
        stars += r["stargazerCount"]
        for e in r["languages"]["edges"]:
            n = e["node"]
            l = langs.setdefault(n["name"], [0, n["color"] or "#5ee7ff"])
            l[0] += e["size"]
    total = sum(v[0] for v in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:5]
    return {
        "total": cal["totalContributions"], "commits": cc["totalCommitContributions"],
        "prs": u["pullRequests"]["totalCount"], "issues": u["issues"]["totalCount"],
        "stars": stars, "repos": u["repositories"]["totalCount"],
        "cur": cur, "best": best, "active": sum(1 for _, c in days if c > 0),
        "langs": [(n, v[0] / total * 100, v[1]) for n, v in top],
    }

def render(s):
    F = 'font-family="ui-monospace,Menlo,Consolas,monospace"'
    rows = [("Commits", s["commits"]), ("Pull requests", s["prs"]), ("Issues", s["issues"]),
            ("Estrellas", s["stars"]), ("Repositorios", s["repos"])]
    p1 = "".join(f'<text x="36" y="{142+20*i}" font-size="13" fill="#7fb6c4">{k}</text>'
                 f'<text x="274" y="{142+20*i}" font-size="13" fill="#cfeaf1" text-anchor="end">{v}</text>'
                 for i, (k, v) in enumerate(rows))
    ratio = min(s["cur"] / s["best"], 1) if s["best"] else 0
    circ = 2 * 3.14159 * 46
    p3 = ""
    for i, (name, pct, color) in enumerate(s["langs"]):
        y = 78 + 32 * i
        w = max(pct / 100 * 238, 3)
        p3 += (f'<text x="626" y="{y}" font-size="13" fill="#cfeaf1">{html.escape(name)}</text>'
               f'<text x="864" y="{y}" font-size="13" fill="#7fb6c4" text-anchor="end">{pct:.1f}%</text>'
               f'<rect x="626" y="{y+8}" width="238" height="6" rx="3" fill="#0b2e3b"/>'
               f'<rect x="626" y="{y+8}" width="0" height="6" rx="3" fill="{color}">'
               f'<animate attributeName="width" from="0" to="{w:.1f}" dur="1.2s" begin="{0.15*i:.2f}s" fill="freeze"/></rect>')
    box = lambda x: f'<rect x="{x}" y="20" width="270" height="220" rx="8" fill="#03121a" stroke="#1d6a7a" stroke-width="1.5"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 260" width="900" height="260" role="img" aria-label="Estadísticas de GitHub de {html.escape(USER)}">
<rect width="900" height="260" rx="14" fill="#041820"/>
{box(20)}{box(315)}{box(610)}
<g {F}>
<text x="36" y="46" font-size="12" fill="#7fb6c4">actividad, últimos 12 meses</text>
<text x="36" y="98" font-size="40" font-weight="700" fill="#5ee7ff">{s["total"]}</text>
<text x="36" y="118" font-size="12" fill="#7fb6c4">contribuciones</text>
{p1}
<text x="331" y="46" font-size="12" fill="#7fb6c4">racha diaria</text>
<circle cx="450" cy="106" r="46" fill="none" stroke="#0b2e3b" stroke-width="6"/>
<circle cx="450" cy="106" r="46" fill="none" stroke="#ffb547" stroke-width="6" stroke-linecap="round" stroke-dasharray="{circ*ratio:.0f} {circ:.0f}" transform="rotate(-90 450 106)"/>
<text x="450" y="118" font-size="34" font-weight="700" fill="#ffb547" text-anchor="middle">{s["cur"]}</text>
<text x="450" y="176" font-size="12" fill="#7fb6c4" text-anchor="middle">días seguidos</text>
<text x="331" y="204" font-size="13" fill="#7fb6c4">Mejor racha</text><text x="569" y="204" font-size="13" fill="#cfeaf1" text-anchor="end">{s["best"]} días</text>
<text x="331" y="224" font-size="13" fill="#7fb6c4">Días activos</text><text x="569" y="224" font-size="13" fill="#cfeaf1" text-anchor="end">{s["active"]}</text>
<text x="626" y="46" font-size="12" fill="#7fb6c4">lenguajes más usados</text>
{p3}
</g></svg>
'''

if __name__ == "__main__":
    if not TOKEN and "--demo" not in sys.argv:
        sys.exit("Falta GH_TOKEN")
    open(OUT, "w", encoding="utf-8").write(render(compute(demo() if "--demo" in sys.argv else fetch())))
    print("OK", OUT)
