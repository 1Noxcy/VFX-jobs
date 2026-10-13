"""Veille offres jeu vidéo. Lance: python check.py  (DISCORD_WEBHOOK_URL en variable d'env pour les alertes)"""
import json, os, re, time, datetime as dt
from html.parser import HTMLParser
import requests

UA = {"User-Agent": "Mozilla/5.0 (veille-offres perso; 1 requete par studio / 5h)"}
PRIO = ["vfx", "niagara", "technical artist", "tech artist", "technical animator", "unreal", "fx artist", "effects", "shader", "lighting artist"]
SEC = [r"\bqa\b", r"\btest(er|eur)?\b", r"\bstage\b", r"stagiaire", r"\bintern(ship)?\b", r"alternan", r"apprenti",
       r"\bjunior", r"spontan", r"environment artist", r"level (artist|design)", r"3d (character |prop |environment )?artist",
       r"artiste 3d", r"character artist", r"prop artist", r"vehicle artist", r"animat", r"generalist", r"g\u00e9n\u00e9raliste"]
GENERIC = {"lire la suite", "read more", "consult", "consulter", "backstage", "en savoir plus", "learn more", "voir plus",
           "view all", "see all jobs", "\u00e9tudiants et jeunes dipl\u00f4m\u00e9s"}
JOBWORDS = PRIO + SEC + ["artist", "artiste", "designer", "3d"]

def score(t):
    t = t.lower()
    if any(k in t for k in PRIO): return 2
    if any(re.search(k, t) for k in SEC): return 1
    return 0

def clean_title(t):
    t = " ".join(t.split())
    m = re.match(r"^(.*?)\s*(\d{2}/\d{2}/\d{4})$", t)
    return (m.group(1), m.group(2)) if m else (t, None)

def junk(t):
    return ("{" in t or "}" in t or t.isupper() or t.lower() in GENERIC
            or (len(t.split()) < 2 and "artist" not in t.lower()))

def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=25, **kw); r.raise_for_status(); return r

def lever(s, eu):
    base = "api.eu.lever.co" if eu else "api.lever.co"
    return [{"id": j["id"], "title": j["text"], "url": j["hostedUrl"],
             "location": (j.get("categories") or {}).get("location", "")}
            for j in get(f"https://{base}/v0/postings/{s['slug']}?mode=json").json()]

def greenhouse(s):
    d = get(f"https://boards-api.greenhouse.io/v1/boards/{s['slug']}/jobs").json()
    return [{"id": str(j["id"]), "title": j["title"], "url": j["absolute_url"],
             "location": (j.get("location") or {}).get("name", "")} for j in d["jobs"]]

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links, self._h, self._t = [], None, ""
    def handle_starttag(self, tag, a):
        if tag == "a": self._h, self._t = dict(a).get("href"), ""
    def handle_data(self, d):
        if self._h is not None: self._t += d
    def handle_endtag(self, tag):
        if tag == "a" and self._h is not None:
            self.links.append((self._h, " ".join(self._t.split()))); self._h = None

def page(s):
    from urllib.parse import urljoin
    p = Links(); p.feed(get(s["url"]).text); out = {}
    for h, t in p.links:
        if h and 4 < len(t) < 140 and not junk(t) and any(k in (t + h).lower() for k in JOBWORDS):
            u = urljoin(s["url"], h); out[u] = {"id": u, "title": t, "url": u, "location": ""}
    return list(out.values())

def fetch(s):
    a = s["ats"]
    return lever(s, a == "lever_eu") if a in ("lever", "lever_eu") else greenhouse(s) if a == "greenhouse" else page(s)

def discord(msg):
    w = os.environ.get("DISCORD_WEBHOOK_URL")
    if w and msg:
        for i in range(0, len(msg), 1800):
            requests.post(w, json={"content": msg[i:i + 1800]}, timeout=20); time.sleep(1)

def main():
    studios = json.load(open("studios.json", encoding="utf-8"))
    path = "data/jobs.json"
    old = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {"studios": {}}
    first_run = not old["studios"]
    now = dt.datetime.utcnow().isoformat(timespec="minutes") + "Z"
    new_state, alerts = {}, []
    for s in studios:
        prev = old["studios"].get(s["name"], {"jobs": {}})
        e = {"city": s["city"], "country": s["country"], "url": s["url"], "email": s["email"], "confirmed": s["confirmed"],
             "ats": s["ats"], "mode": prev.get("mode"), "warn": None, "jobs": prev["jobs"], "last_checked": prev.get("last_checked"), "error": None}
        if not s["url"]:
            e["error"] = "pas de lien (à compléter)"; new_state[s["name"]] = e; continue
        try:
            found = {}
            for j in fetch(s):
                j["title"], j["published"] = clean_title(j["title"]); found[j["id"]] = j
            e["last_checked"] = now
            e["mode"] = "page" if s["ats"] == "page" else "api"
            if e["mode"] == "page" and not found:
                e["warn"] = "0 offre d\u00e9tect\u00e9e : le site charge peut-\u00eatre ses offres en JavaScript, \u00e0 v\u00e9rifier \u00e0 la main"
            for jid in list(e["jobs"]):
                if jid not in found and junk(e["jobs"][jid]["title"]): del e["jobs"][jid]
            for jid, j in found.items():
                if jid in e["jobs"]:
                    e["jobs"][jid].update(last_seen=now, closed_at=None, title=j["title"], published=j["published"], match=score(j["title"]))
                else:
                    j.update(first_seen=now, last_seen=now, closed_at=None, match=score(j["title"]))
                    e["jobs"][jid] = j
                    if j["match"] and not first_run: alerts.append(f"🆕 **{s['name']}** ({s['city']}) : {j['title']}\n{j['url']}")
            for jid, j in e["jobs"].items():
                if jid not in found and not j.get("closed_at"): j["closed_at"] = now
        except Exception as ex:
            e["error"] = f"{type(ex).__name__}: {str(ex)[:120]}"
        new_state[s["name"]] = e; time.sleep(2)
    json.dump({"updated": now, "studios": new_state}, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if first_run:
        n = sum(1 for st in new_state.values() for j in st["jobs"].values() if j.get("match"))
        discord(f"✅ Veille lancée : {len(studios)} studios, {n} offres pertinentes déjà ouvertes. Les nouvelles offres seront alertées ici.")
    else:
        discord("\n\n".join(alerts))
    print(f"{len(alerts)} alertes, {sum(1 for st in new_state.values() if st['error'])} studios en erreur")

if __name__ == "__main__": main()
