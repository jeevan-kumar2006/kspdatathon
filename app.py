"""
KSP Crime Intelligence & Analytical Platform — Backend
Integrates: Overpass API, Nominatim, Open-Meteo, Wikipedia REST API
ML: KMeans clustering, Isolation Forest, Linear Regression
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional
import sqlite3, random, datetime, json, time, urllib.request, urllib.parse
import numpy as np
from collections import Counter, defaultdict
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder, StandardScaler
import os

# ── Lifespan: replaces deprecated @app.on_event("startup") ───────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("[KSP] Starting up — initializing database...")
    init_db()
    generate_data()
    print("[KSP] Startup complete — server ready")
    yield
    # Shutdown logic (if needed)
    print("[KSP] Shutting down")

app = FastAPI(title="KSP Crime Intelligence Platform", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

DB_PATH = "ksp_crime.db"
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Serve index.html at root — fixes the 404 ─────────────────────────
@app.get("/")
async def serve_index():
    path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(path):
        return FileResponse(path, media_type="text/html")
    return {"error": "index.html not found in the same directory as app.py"}

# ── External API Endpoints (all free, no keys) ───────────────────────
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
WIKI_URL = "https://en.wikipedia.org/api/rest_v1/page/summary"

# ── Karnataka Reference Data ──────────────────────────────────────────
DISTRICTS = {
    "Bangalore Urban":{"lat":12.9716,"lng":77.5946,"stations":["Koramangala","Indiranagar","Whitefield","JP Nagar","Rajajinagar","HSR Layout","Marathahalli","Electronic City","Banashankari","Jayanagar"]},
    "Bangalore Rural":{"lat":13.0,"lng":77.5,"stations":["Devanahalli","Hoskote","Nelamangala","Doddaballapur"]},
    "Mysore":{"lat":12.2958,"lng":76.6394,"stations":["Nazarbad","Vidyaranyapuram","Saraswathipuram","Kuvempunagar","Gokulam"]},
    "Hubli-Dharwad":{"lat":15.3647,"lng":75.124,"stations":["Hubli East","Hubli West","Dharwad Rural","Navanagar"]},
    "Mangalore":{"lat":12.9141,"lng":74.856,"stations":["Pandeshwara","Kadri","Bunder","Surathkal","Attavar"]},
    "Belgaum":{"lat":15.8522,"lng":74.4986,"stations":["Camp","Market","Shahpur","Tilakwadi"]},
    "Gulbarga":{"lat":17.3297,"lng":76.8343,"stations":["Gulbarga Town","Afzalpur","Chittapur"]},
    "Davangere":{"lat":14.4643,"lng":75.9282,"stations":["Davangere Town","Harihar","Channagiri"]},
    "Bellary":{"lat":15.1394,"lng":76.9214,"stations":["Bellary Town","Hospet","Siruguppa"]},
    "Shimoga":{"lat":13.9299,"lng":75.5681,"stations":["Shimoga Town","Bhadravathi","Sagar"]},
    "Tumkur":{"lat":13.34,"lng":77.0998,"stations":["Tumkur Town","Madhugiri","Turuvekere"]},
    "Raichur":{"lat":16.2076,"lng":77.3463,"stations":["Raichur Town","Manvi","Sindhnur"]},
    "Hassan":{"lat":13.0072,"lng":76.0984,"stations":["Hassan Town","Belur","Chikmagalur Road"]},
    "Udupi":{"lat":13.3409,"lng":74.742,"stations":["Udupi Town","Manipal","Karkala"]},
    "Chitradurga":{"lat":14.2284,"lng":76.3947,"stations":["Chitradurga Town","Hiriyur","Hosadurga"]},
    "Mandya":{"lat":12.5223,"lng":76.8966,"stations":["Mandya Town","Maddur","Srirangapatna"]},
    "Bidar":{"lat":17.9104,"lng":77.5199,"stations":["Bidar Town","Basavakalyan","Humnabad"]},
    "Dakshina Kannada":{"lat":12.85,"lng":75.0,"stations":["Puttur","Sullia","Bantwal"]},
    "Uttara Kannada":{"lat":14.546,"lng":74.4955,"stations":["Karwar","Sirsi","Honavar"]},
    "Koppal":{"lat":15.3519,"lng":76.1516,"stations":["Koppal Town","Gangavathi","Kushtagi"]},
    "Gadag":{"lat":15.4168,"lng":75.6287,"stations":["Gadag Town","Laxmeshwar","Nargund"]},
    "Haveri":{"lat":14.7938,"lng":75.3976,"stations":["Haveri Town","Ranebennur","Savanur"]},
    "Bagalkot":{"lat":16.1852,"lng":75.6901,"stations":["Bagalkot Town","Jamkhandi","Badami"]},
    "Chamarajanagar":{"lat":11.9225,"lng":76.9422,"stations":["Chamarajanagar Town","Kollegal","Gundlupet"]},
    "Kodagu":{"lat":12.3375,"lng":75.8069,"stations":["Madikeri","Virajpet","Somwarpet"]},
    "Ramanagara":{"lat":12.7174,"lng":77.2753,"stations":["Ramanagara Town","Channapatna","Kanakapura"]},
    "Yadgir":{"lat":16.768,"lng":77.1323,"stations":["Yadgir Town","Shorapur","Sedam"]},
}

CRIME_TYPES = ["Theft","Robbery","Burglary","Murder","Assault","Cyber Crime",
               "Drug Offense","Vehicle Theft","Chain Snatching","Fraud",
               "Kidnapping","Rioting","Arson","Sexual Offense","Cheating"]
CRIME_WEIGHTS = [15,8,10,3,12,10,7,12,8,7,2,3,1,3,6]
SEVERITY_MAP = {"Theft":3,"Robbery":5,"Burglary":4,"Murder":10,"Assault":6,
    "Cyber Crime":7,"Drug Offense":6,"Vehicle Theft":4,"Chain Snatching":3,
    "Fraud":5,"Kidnapping":9,"Rioting":6,"Arson":7,"Sexual Offense":9,"Cheating":4}
MODUS_OPERANDI = ["Break-in through rear window","Distraction technique",
    "Impersonation of official","Pickpocketing in crowd","Cyber phishing",
    "Forced entry at night","Surveillance before attack","Use of stolen vehicle",
    "Social engineering","Fake identity documents","Snatching from moving vehicle",
    "Letter bomb threat","Hacking through public WiFi","Armed confrontation","Gaslighting victim"]
STATUSES = ["Under Investigation","Chargesheet Filed","Closed - Untraced","Convicted","Acquitted","Pending Trial"]
STATUS_WEIGHTS = [25,20,15,15,10,15]
FIRST_M = ["Ravi","Suresh","Manoj","Pradeep","Kumar","Venkatesh","Rajesh","Mohan",
           "Nagaraj","Ganesh","Shankar","Krishna","Murthy","Basavaraj","Mahesh",
           "Deepak","Vinay","Arun","Siddharth","Karthik"]
FIRST_F = ["Lakshmi","Sujatha","Geetha","Priya","Anitha","Bhagya","Nandini","Pooja",
           "Divya","Shruti","Meera","Kavitha","Rekha","Vijaya","Saritha","Asha",
           "Nirmala","Padma","Yashoda","Suma"]
LASTS = ["Kumar","Reddy","Gowda","Sharma","Patil","Naik","Rao","Hegde",
         "Shetty","Pai","Bhat","Kulkarni","Desai","Joshi","Menon","Nair",
         "Acharya","Deshpande","Mujawar","Siddiqui"]

NAME_MAP = {"Bengaluru Urban":"Bangalore Urban","Bengaluru Rural":"Bangalore Rural",
    "Mysuru":"Mysore","Kalaburagi":"Gulbarga","Ballari":"Bellary",
    "Shivamogga":"Shimoga","Tumakuru":"Tumkur","Chikkamagaluru":"Chikmagalur"}
NAME_MAP_REV = {v:k for k,v in NAME_MAP.items()}

WEATHER_CITIES = [
    {"name":"Bangalore","lat":12.97,"lng":77.59},
    {"name":"Mysore","lat":12.30,"lng":76.65},
    {"name":"Mangalore","lat":12.91,"lng":74.86},
    {"name":"Hubli","lat":15.36,"lng":75.12},
    {"name":"Belgaum","lat":15.85,"lng":74.50},
    {"name":"Gulbarga","lat":17.33,"lng":76.83},
]

# ── Database ─────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; return conn

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT, crime_type TEXT, district TEXT,
        station TEXT, latitude REAL, longitude REAL, date TEXT, time TEXT,
        hour INTEGER, status TEXT, severity INTEGER, modus_operandi TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS persons (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, role TEXT, age INTEGER,
        gender TEXT, alias TEXT, last_known_location TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS incident_persons (
        incident_id INTEGER, person_id INTEGER, relationship TEXT,
        PRIMARY KEY(incident_id, person_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS person_associations (
        person_id_1 INTEGER, person_id_2 INTEGER, association_type TEXT, weight REAL,
        PRIMARY KEY(person_id_1, person_id_2))''')
    c.execute('''CREATE TABLE IF NOT EXISTS api_cache (
        key TEXT PRIMARY KEY, data TEXT NOT NULL, fetched_at REAL NOT NULL)''')
    conn.commit(); conn.close()

def generate_data():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM incidents")
    if c.fetchone()[0] > 0: conn.close(); return
    base = datetime.date(2023, 1, 1)
    for _ in range(5000):
        dist = random.choice(list(DISTRICTS.keys()))
        info = DISTRICTS[dist]; station = random.choice(info["stations"])
        ctype = random.choices(CRIME_TYPES, weights=CRIME_WEIGHTS, k=1)[0]
        lat = info["lat"] + random.uniform(-0.15, 0.15)
        lng = info["lng"] + random.uniform(-0.15, 0.15)
        date = base + datetime.timedelta(days=random.randint(0, 730))
        hour = random.choices(range(24),
            weights=[1,1,1,1,1,2,3,4,3,3,4,5,6,6,5,5,5,6,7,8,7,5,4,2], k=1)[0]
        status = random.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
        mo = random.choice(MODUS_OPERANDI)
        c.execute('''INSERT INTO incidents
            (crime_type,district,station,latitude,longitude,date,time,hour,status,severity,modus_operandi)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
            (ctype,dist,station,lat,lng,date.isoformat(),
             f"{hour:02d}:{random.randint(0,59):02d}",hour,status,SEVERITY_MAP[ctype],mo))
        iid = c.lastrowid
        for _ in range(random.randint(1,3)):
            g = random.choice(["Male","Female"])
            fn = random.choice(FIRST_M if g=="Male" else FIRST_F)
            name = fn + " " + random.choice(LASTS)
            role = random.choices(["Suspect","Victim","Witness"], weights=[30,50,20], k=1)[0]
            alias = (fn[0]+"."+name.split()[-1]) if role=="Suspect" and random.random()>0.6 else ""
            c.execute('''INSERT INTO persons(name,role,age,gender,alias,last_known_location)
                VALUES(?,?,?,?,?,?)''', (name,role,random.randint(18,65),g,alias,dist if alias else ""))
            pid = c.lastrowid
            rel = {"Suspect":"suspect_in","Victim":"victim_of","Witness":"witness_to"}[role]
            c.execute('INSERT INTO incident_persons VALUES(?,?,?)', (iid,pid,rel))
    c.execute("SELECT DISTINCT person_id FROM incident_persons WHERE relationship='suspect_in'")
    sids = [r[0] for r in c.fetchall()]
    for _ in range(min(250, len(sids))):
        p1,p2 = random.sample(sids,2)
        atype = random.choice(["Known Associate","Co-accused","Family Connection","Same Gang","Prior Cellmate"])
        c.execute('INSERT OR IGNORE INTO person_associations VALUES(?,?,?,?)',
                  (p1,p2,atype,round(random.uniform(0.3,1.0),2)))
    conn.commit(); conn.close()
    print("[KSP] Database initialized — 5000 incidents generated")

# ── External API Helpers ─────────────────────────────────────────────
def cache_get(key):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT data,fetched_at FROM api_cache WHERE key=?", (key,))
    row = c.fetchone(); conn.close()
    if row: return json.loads(row["data"]), row["fetched_at"]
    return None, None

def cache_set(key, data, ttl=86400):
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO api_cache VALUES(?,?,?)",
              (key, json.dumps(data), time.time() + ttl))
    conn.commit(); conn.close()

def normalize_name(name):
    if not name: return ""
    for k,v in NAME_MAP.items():
        if k.lower() in name.lower(): return v
    return name.strip()

def fetch_district_boundaries():
    cached, exp = cache_get("overpass_boundaries")
    if cached and exp > time.time():
        print("[OSM] District boundaries from cache")
        return cached
    print("[OSM] Fetching district boundaries from Overpass API (this may take 30-90s on first run)...")
    query = """
    [out:json][timeout:180];
    area["name"="Karnataka"]["admin_level"="4"]->.state;
    rel(area.state)["admin_level"="6"]["boundary"="administrative"];
    out geom;
    """
    try:
        import requests
        r = requests.post(OVERPASS_URL, data={"data": query}, timeout=180)
        r.raise_for_status()
        data = r.json()
        geojson = relations_to_geojson(data.get("elements", []))
        cache_set("overpass_boundaries", geojson, ttl=86400*7)
        print(f"[OSM] Got {len(geojson['features'])} district boundaries")
        return geojson
    except Exception as e:
        print(f"[OSM] Boundary fetch failed: {e}")
        if cached: return cached
        return {"type":"FeatureCollection","features":[]}

def relations_to_geojson(relations):
    features = []
    for rel in relations:
        tags = rel.get("tags", {})
        name = tags.get("name", "Unknown")
        outers, inners = [], []
        for m in rel.get("members", []):
            if "geometry" not in m: continue
            coords = [[round(p["lon"],5), round(p["lat"],5)] for p in m["geometry"]]
            if len(coords) < 4: continue
            if coords[0] != coords[-1]: coords.append(coords[0])
            if m.get("role","outer") == "outer": outers.append(coords)
            else: inners.append(coords)
        if not outers: continue
        if len(outers) == 1:
            geom = {"type":"Polygon","coordinates":outers+inners}
        else:
            geom = {"type":"MultiPolygon","coordinates":[[o] for o in outers]}
        features.append({"type":"Feature","properties":{
            "name":name, "name_normalized":normalize_name(name),
            "osm_id":rel.get("id",0)}, "geometry":geom})
    return {"type":"FeatureCollection","features":features}

def fetch_police_stations():
    cached, exp = cache_get("overpass_stations")
    if cached and exp > time.time():
        print("[OSM] Police stations from cache")
        return cached
    print("[OSM] Fetching police stations from Overpass API...")
    query = """
    [out:json][timeout:90];
    area["name"="Karnataka"]->.state;
    (
      node["amenity"="police"](area.state);
      way["amenity"="police"](area.state);
    );
    out center body;
    """
    try:
        import requests
        r = requests.post(OVERPASS_URL, data={"data": query}, timeout=90)
        r.raise_for_status()
        data = r.json()
        stations = []
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            lat = el.get("lat") or el.get("center",{}).get("lat")
            lon = el.get("lon") or el.get("center",{}).get("lon")
            if lat and lon:
                stations.append({
                    "name": tags.get("name","Police Station"),
                    "lat": lat, "lng": lon,
                    "operator": tags.get("operator",""),
                    "addr": tags.get("addr:city",""),
                    "osm_id": el.get("id",0)
                })
        cache_set("overpass_stations", stations, ttl=86400*3)
        print(f"[OSM] Got {len(stations)} police stations")
        return stations
    except Exception as e:
        print(f"[OSM] Station fetch failed: {e}")
        if cached: return cached
        return []

def nominatim_search(q):
    import requests
    params = {"q": q, "format": "json", "limit": 8,
              "bounded": 1, "viewbox": "73.5,11.5,79.0,18.0",
              "accept-language": "en"}
    r = requests.get(NOMINATIM_URL, params=params, timeout=10,
                     headers={"User-Agent": "KSP-Crime-Intel/1.0"})
    r.raise_for_status()
    return [{"name":r["display_name"].split(",")[0],
             "full":r["display_name"],"lat":float(r["lat"]),"lng":float(r["lon"]),
             "type":r.get("type","")} for r in r.json()]

def fetch_weather(lat, lng):
    cache_key = f"weather_{lat:.1f}_{lng:.1f}"
    cached, exp = cache_get(cache_key)
    if cached and exp > time.time(): return cached
    try:
        import requests
        url = f"{OPENMETEO_URL}?latitude={lat}&longitude={lng}&current_weather=true"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json().get("current_weather", {})
        result = {"temperature": data.get("temperature"),
                  "windspeed": data.get("windspeed"),
                  "weathercode": data.get("weathercode"),
                  "winddir": data.get("winddirection")}
        cache_set(cache_key, result, ttl=1800)
        return result
    except: return cached if cached else None

def weather_description(code):
    codes = {0:"Clear sky",1:"Mainly clear",2:"Partly cloudy",3:"Overcast",
             45:"Fog",48:"Depositing rime fog",51:"Light drizzle",53:"Moderate drizzle",
             55:"Dense drizzle",61:"Slight rain",63:"Moderate rain",65:"Heavy rain",
             71:"Slight snow",73:"Moderate snow",75:"Heavy snow",
             80:"Slight rain showers",81:"Moderate rain showers",82:"Violent rain showers",
             95:"Thunderstorm",96:"Thunderstorm with hail"}
    return codes.get(code, "Unknown")

def weather_icon(code):
    if code <= 1: return "fa-sun"
    if code <= 3: return "fa-cloud-sun"
    if code <= 48: return "fa-smog"
    if code <= 65: return "fa-cloud-rain"
    if code <= 75: return "fa-snowflake"
    if code <= 82: return "fa-cloud-showers-heavy"
    return "fa-bolt"

def fetch_wiki_summary(title):
    cache_key = f"wiki_{title}"
    cached, exp = cache_get(cache_key)
    if cached and exp > time.time(): return cached
    try:
        import requests
        r = requests.get(f"{WIKI_URL}/{urllib.parse.quote(title)}", timeout=10,
                         headers={"User-Agent": "KSP-Crime-Intel/1.0"})
        if r.status_code == 200:
            data = r.json()
            result = {"title": data.get("title",""),
                      "extract": data.get("extract","")[:500],
                      "thumbnail": (data.get("thumbnail",{}) or {}).get("source","")}
            cache_set(cache_key, result, ttl=86400*7)
            return result
    except: pass
    return cached if cached else None

# ── ML Functions ─────────────────────────────────────────────────────
def compute_hotspots():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT latitude,longitude,crime_type,severity,hour FROM incidents")
    rows = c.fetchall(); conn.close()
    if len(rows) < 10: return []
    coords = np.array([[r[0],r[1]] for r in rows])
    nc = min(15, max(3, len(rows)//100))
    km = KMeans(n_clusters=nc, random_state=42, n_init=10)
    labels = km.fit_predict(coords)
    result = []
    for i in range(nc):
        pts = [rows[j] for j in range(len(rows)) if labels[j]==i]
        if len(pts) < 3: continue
        lats=[p[0] for p in pts]; lngs=[p[1] for p in pts]
        cc=Counter(p[2] for p in pts); top=cc.most_common(1)[0]
        ph=Counter(p[4] for p in pts).most_common(1)[0]
        avg_sev=round(sum(p[3] for p in pts)/len(pts),1)
        result.append({"lat":round(sum(lats)/len(lats),4),
            "lng":round(sum(lngs)/len(lngs),4),"count":len(pts),
            "top_crime":top[0],"top_crime_count":top[1],
            "peak_hour":ph[0],"avg_severity":avg_sev,
            "radius":min(250,len(pts)*5)})
    result.sort(key=lambda x:x["count"],reverse=True)
    return result

def compute_anomalies():
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT id,crime_type,district,station,date,time,hour,severity,modus_operandi FROM incidents")
    data=[dict(r) for r in c.fetchall()]; conn.close()
    if len(data)<50: return []
    le_d=LabelEncoder(); le_t=LabelEncoder(); le_s=LabelEncoder()
    feats=np.column_stack([le_d.fit_transform([d["district"] for d in data]),
        le_t.fit_transform([d["crime_type"] for d in data]),
        le_s.fit_transform([d["station"] for d in data]),
        [d["hour"] for d in data],[d["severity"] for d in data],
        [d["latitude"] for d in data],[d["longitude"] for d in data]])
    sc=StandardScaler(); iso=IsolationForest(contamination=0.05,random_state=42,n_estimators=100)
    preds=iso.fit_predict(sc.fit_transform(feats))
    out=[]
    for i,p in enumerate(preds):
        if p==-1:
            d=data[i]
            out.append({"id":d["id"],"crime_type":d["crime_type"],"district":d["district"],
                "station":d["station"],"date":d["date"],"time":d["time"],
                "severity":d["severity"],"modus_operandi":d["modus_operandi"],
                "reason":f"Unusual {d['crime_type']} in {d['district']} at {d['time']}"})
    return out[:50]

def compute_predictions():
    conn=get_db(); c=conn.cursor()
    c.execute('''SELECT district,strftime('%Y-%m',date) as m,COUNT(*) as c
                 FROM incidents GROUP BY district,m ORDER BY district,m''')
    rows=c.fetchall(); conn.close()
    dm=defaultdict(lambda: defaultdict(int))
    for r in rows: dm[r[0]][r[1]]=r[2]
    preds=[]
    for dist,months in dm.items():
        if len(months)<6: continue
        sm=sorted(months.keys())
        vals=np.array([months[m] for m in sm],dtype=float)
        x=np.arange(len(vals))
        coeffs=np.polyfit(x,vals,1)
        nxt=np.maximum(0,np.polyval(coeffs,[len(vals),len(vals)+1,len(vals)+2])).astype(int)
        recent_avg=np.mean(vals[-3:]) if len(vals)>=3 else np.mean(vals)
        pred_avg=np.mean(nxt)
        change=((pred_avg-recent_avg)/max(1,recent_avg))*100
        preds.append({"district":dist,"historical_avg":round(recent_avg,1),
            "p1":int(nxt[0]),"p2":int(nxt[1]),"p3":int(nxt[2]),
            "trend":"increasing" if coeffs[0]>1 else ("decreasing" if coeffs[0]<-1 else "stable"),
            "risk_change":round(change,1),
            "risk_level":"high" if change>20 else ("medium" if change>5 else "low")})
    preds.sort(key=lambda x:x["risk_change"],reverse=True)
    return preds

# ── API Routes: Internal Data ────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status":"operational","service":"KSP Crime Intelligence Platform v2.0",
            "apis":{"overpass":"active","nominatim":"active","openmeteo":"active","wikipedia":"active"}}

@app.get("/api/dashboard/stats")
def dashboard_stats():
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT COUNT(*) FROM incidents"); total=c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM incidents WHERE status='Under Investigation'"); pending=c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM incidents WHERE status='Chargesheet Filed'"); charged=c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT district) FROM incidents"); dists=c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT station) FROM incidents"); stats=c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT district) FROM incidents WHERE severity>=8"); highrisk=c.fetchone()[0]
    c.execute("SELECT strftime('%Y-%m',date) as m,COUNT(*) as c FROM incidents GROUP BY m ORDER BY m LIMIT 24")
    monthly=[{"month":r[0],"count":r[1]} for r in c.fetchall()]
    c.execute("SELECT crime_type,COUNT(*) as c FROM incidents GROUP BY crime_type ORDER BY c DESC")
    by_type=[{"type":r[0],"count":r[1]} for r in c.fetchall()]
    c.execute("SELECT district,COUNT(*) as c FROM incidents GROUP BY district ORDER BY c DESC LIMIT 10")
    by_dist=[{"district":r[0],"count":r[1]} for r in c.fetchall()]
    c.execute("SELECT hour,COUNT(*) as c FROM incidents GROUP BY hour ORDER BY hour")
    hourly=[{"hour":r[0],"count":r[1]} for r in c.fetchall()]
    c.execute("""SELECT CASE WHEN severity<=3 THEN 'Low' WHEN severity<=6 THEN 'Medium'
                 WHEN severity<=8 THEN 'High' ELSE 'Critical' END as lvl,COUNT(*) as c
                 FROM incidents GROUP BY lvl""")
    sev=[{"level":r[0],"count":r[1]} for r in c.fetchall()]
    c.execute("SELECT district,COUNT(*) as c,AVG(severity) as s FROM incidents GROUP BY district")
    dist_crime=[{"district":r[0],"count":r[1],"avg_sev":round(r[2],1)} for r in c.fetchall()]
    conn.close()
    return {"total_incidents":total,"pending_investigation":pending,"chargesheeted":charged,
            "districts_active":dists,"stations_active":stats,"high_risk_districts":highrisk,
            "monthly_trend":monthly,"by_crime_type":by_type,"by_district":by_dist,
            "hourly_distribution":hourly,"severity_distribution":sev,"district_crime":dist_crime}

@app.get("/api/incidents/map")
def map_incidents(district:Optional[str]=None, crime_type:Optional[str]=None, limit:int=1500):
    conn=get_db(); c=conn.cursor()
    q="SELECT id,crime_type,district,station,latitude,longitude,date,time,severity,status FROM incidents WHERE 1=1"
    p=[]
    if district: q+=" AND district=?"; p.append(district)
    if crime_type: q+=" AND crime_type=?"; p.append(crime_type)
    q+=f" ORDER BY RANDOM() LIMIT {limit}"
    c.execute(q,p)
    data=[dict(r) for r in c.fetchall()]; conn.close()
    return data

@app.get("/api/hotspots")
def hotspots(): return compute_hotspots()

@app.get("/api/network")
def network_data(limit:int=80):
    conn=get_db(); c=conn.cursor()
    c.execute('''SELECT p.id,p.name,p.role,p.alias,COUNT(ip.incident_id) as ic
                 FROM persons p JOIN incident_persons ip ON p.id=ip.person_id
                 GROUP BY p.id ORDER BY ic DESC LIMIT ?''', (limit,))
    nodes=[]; nmap={}
    for r in c.fetchall():
        nid=str(r[0])
        nodes.append({"id":nid,"label":r[1][:18],"title":f"{r[1]} ({r[2]}) — {r[4]} cases",
                       "group":r[2],"value":min(25,r[4]*3)})
        nmap[r[0]]=nid
    c.execute('''SELECT person_id_1,person_id_2,association_type,weight
                 FROM person_associations LIMIT 150''')
    edges=[]
    for r in c.fetchall():
        if r[0] in nmap and r[1] in nmap:
            edges.append({"from":nmap[r[0]],"to":nmap[r[1]],"label":r[2],
                          "title":f"{r[2]} ({r[3]})","value":r[3]*10})
    c.execute('''SELECT ip1.person_id,ip2.person_id,i.crime_type
                 FROM incident_persons ip1 JOIN incident_persons ip2
                 ON ip1.incident_id=ip2.incident_id AND ip1.person_id<ip2.person_id
                 JOIN incidents i ON i.id=ip1.incident_id LIMIT 120''')
    for r in c.fetchall():
        if r[0] in nmap and r[1] in nmap:
            edges.append({"from":nmap[r[0]],"to":nmap[r[1]],"label":"Co-involved",
                          "title":f"Linked via {r[2]}","value":2,"dashes":True})
    conn.close()
    return {"nodes":nodes,"edges":edges}

@app.get("/api/predictions")
def predictions(): return compute_predictions()

@app.get("/api/anomalies")
def anomalies(): return compute_anomalies()

@app.get("/api/trend-alerts")
def trend_alerts():
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT MAX(date) FROM incidents"); mx=c.fetchone()[0]
    if not mx: conn.close(); return []
    mx_dt=datetime.date.fromisoformat(mx)
    rs=(mx_dt-datetime.timedelta(days=30)).isoformat()
    ps=(mx_dt-datetime.timedelta(days=60)).isoformat()
    c.execute('''SELECT district,crime_type,
                 SUM(CASE WHEN date>=? THEN 1 ELSE 0 END) as rec,
                 SUM(CASE WHEN date>=? AND date<? THEN 1 ELSE 0 END) as prev
                 FROM incidents WHERE date>=?
                 GROUP BY district,crime_type
                 HAVING rec>prev*1.3 AND rec>3 ORDER BY (rec-prev) DESC LIMIT 8''', (rs,ps,rs,ps))
    alerts=[]
    for r in c.fetchall():
        pct=round(((r[2]-r[3])/max(1,r[3]))*100,0)
        alerts.append({"district":r[0],"crime_type":r[1],"recent":r[2],"previous":r[3],
            "increase_pct":pct,"severity":"critical" if pct>100 else ("high" if pct>50 else "medium")})
    conn.close(); return alerts

@app.get("/api/repeat-offenders")
def repeat_offenders(limit:int=15):
    conn=get_db(); c=conn.cursor()
    c.execute('''SELECT p.id,p.name,p.alias,p.age,p.gender,p.last_known_location,
                 COUNT(ip.incident_id) as ic,
                 GROUP_CONCAT(DISTINCT i.crime_type) as ct,
                 GROUP_CONCAT(DISTINCT i.modus_operandi) as mo,
                 GROUP_CONCAT(DISTINCT i.district) as dd
                 FROM persons p JOIN incident_persons ip ON p.id=ip.person_id
                 JOIN incidents i ON i.id=ip.incident_id
                 WHERE ip.relationship='suspect_in'
                 GROUP BY p.id HAVING ic>1 ORDER BY ic DESC LIMIT ?''', (limit,))
    out=[]
    for r in c.fetchall():
        out.append({"id":r[0],"name":r[1],"alias":r[2] or "","age":r[3],"gender":r[4],
            "location":r[5] or "Unknown","incident_count":r[6],
            "crime_types":list(set(r[7].split(","))) if r[7] else [],
            "methods":list(set(r[8].split(","))) if r[8] else [],
            "districts":list(set(r[9].split(","))) if r[9] else []})
    conn.close(); return out

@app.get("/api/socio-economic")
def socio_economic():
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT district,COUNT(*) as c,AVG(severity) as sev FROM incidents GROUP BY district")
    cd={r[0]:{"total":r[1],"avg_sev":round(r[2],2)} for r in c.fetchall()}; conn.close()
    out=[]
    for d,info in DISTRICTS.items():
        cr=cd.get(d,{"total":0,"avg_sev":0})
        out.append({"district":d,"crime_count":cr["total"],"avg_severity":cr["avg_sev"],
            "population_density":random.randint(200,8000),
            "urbanization_rate":round(random.uniform(0.2,0.95),2),
            "literacy_rate":round(random.uniform(0.6,0.95),2),
            "poverty_index":round(random.uniform(0.05,0.4),2)})
    return out

@app.get("/api/districts")
def get_districts(): return list(DISTRICTS.keys())

@app.get("/api/crime-types")
def get_crime_types(): return CRIME_TYPES

# ── API Routes: External Data ────────────────────────────────────────
@app.get("/api/geo/boundaries")
def geo_boundaries():
    """Fetch Karnataka district boundary polygons from OpenStreetMap Overpass API"""
    return fetch_district_boundaries()

@app.get("/api/geo/stations")
def geo_stations():
    """Fetch real police station POIs from OpenStreetMap Overpass API"""
    return fetch_police_stations()

@app.get("/api/geo/search")
def geo_search(q: str = Query(..., min_length=2)):
    """Geocode a location using OpenStreetMap Nominatim API"""
    try:
        return nominatim_search(q)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Nominatim error: {str(e)}")

@app.get("/api/geo/weather-cities")
def geo_weather_cities():
    """Fetch current weather for major Karnataka cities via Open-Meteo API"""
    results = []
    for city in WEATHER_CITIES:
        w = fetch_weather(city["lat"], city["lng"])
        if w:
            results.append({"city": city["name"],
                "temperature": w["temperature"], "windspeed": w["windspeed"],
                "weathercode": w["weathercode"], "winddir": w["winddir"],
                "description": weather_description(w["weathercode"]),
                "icon": weather_icon(w["weathercode"])})
    return results

@app.get("/api/geo/weather")
def geo_weather(lat: float, lng: float):
    """Fetch weather for arbitrary coordinates via Open-Meteo API"""
    w = fetch_weather(lat, lng)
    if not w: raise HTTPException(502, "Weather fetch failed")
    return {"temperature":w["temperature"],"windspeed":w["windspeed"],
            "weathercode":w["weathercode"],"description":weather_description(w["weathercode"]),
            "icon":weather_icon(w["weathercode"])}

@app.get("/api/geo/district-wiki/{district_name}")
def geo_district_wiki(district_name: str):
    """Fetch Wikipedia summary for a Karnataka district"""
    names_to_try = [district_name]
    if district_name in NAME_MAP_REV:
        names_to_try.append(NAME_MAP_REV[district_name] + " district")
    names_to_try.append(district_name + " district")
    for name in names_to_try:
        result = fetch_wiki_summary(name)
        if result and result.get("extract"):
            return result
    return {"title": district_name, "extract": "No Wikipedia data available.", "thumbnail": ""}

@app.get("/api/geo/boundaries-status")
def boundaries_status():
    """Check if boundaries are cached and ready"""
    cached, exp = cache_get("overpass_boundaries")
    if cached and exp > time.time():
        return {"status":"cached","feature_count":len(cached.get("features",[]))}
    return {"status":"needs_fetch"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
