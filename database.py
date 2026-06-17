"""KSP Crime Intelligence Platform — Database Schema & Data Generation"""

import sqlite3
import random
import datetime
from config import (
    DB_PATH, DISTRICTS, CRIME_TYPES, CRIME_WEIGHTS, SEVERITY_MAP,
    MODUS_OPERANDI, STATUSES, STATUS_WEIGHTS,
    FIRST_NAMES_M, FIRST_NAMES_F, LAST_NAMES
)


def get_db():
    """Get a database connection with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crime_type TEXT, district TEXT, station TEXT,
        latitude REAL, longitude REAL, date TEXT, time TEXT,
        hour INTEGER, status TEXT, severity INTEGER, modus_operandi TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS persons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, role TEXT, age INTEGER, gender TEXT,
        alias TEXT, last_known_location TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS incident_persons (
        incident_id INTEGER, person_id INTEGER, relationship TEXT,
        PRIMARY KEY(incident_id, person_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS person_associations (
        person_id_1 INTEGER, person_id_2 INTEGER,
        association_type TEXT, weight REAL,
        PRIMARY KEY(person_id_1, person_id_2)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS api_cache (
        key TEXT PRIMARY KEY, data TEXT NOT NULL, fetched_at REAL NOT NULL
    )""")
    conn.commit()
    conn.close()


def generate_data():
    """Generate 5000 simulated crime incidents across Karnataka."""
    conn = get_db()
    c = conn.cursor()

    # Check if data already exists
    c.execute("SELECT COUNT(*) FROM incidents")
    if c.fetchone()[0] > 0:
        conn.close()
        print("[DB] Data already exists — skipping generation")
        return

    print("[DB] Generating 5000 simulated incidents...")
    base_date = datetime.date(2023, 1, 1)
    district_names = list(DISTRICTS.keys())

    for _ in range(5000):
        dist = random.choice(district_names)
        info = DISTRICTS[dist]
        station = random.choice(info["stations"])
        ctype = random.choices(CRIME_TYPES, weights=CRIME_WEIGHTS, k=1)[0]
        lat = info["lat"] + random.uniform(-0.15, 0.15)
        lng = info["lng"] + random.uniform(-0.15, 0.15)
        date = base_date + datetime.timedelta(days=random.randint(0, 730))
        # Realistic hourly distribution: more crime at night
        hour = random.choices(
            range(24),
            weights=[1,1,1,1,1,2,3,4,3,3,4,5,6,6,5,5,5,6,7,8,7,5,4,2],
            k=1
        )[0]
        status = random.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
        mo = random.choice(MODUS_OPERANDI)

        c.execute("""INSERT INTO incidents
            (crime_type, district, station, latitude, longitude,
             date, time, hour, status, severity, modus_operandi)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (ctype, dist, station, lat, lng, date.isoformat(),
             f"{hour:02d}:{random.randint(0,59):02d}", hour,
             status, SEVERITY_MAP[ctype], mo))

        incident_id = c.lastrowid

        # Generate 1-3 persons per incident
        for _ in range(random.randint(1, 3)):
            gender = random.choice(["Male", "Female"])
            first = random.choice(FIRST_NAMES_M if gender == "Male" else FIRST_NAMES_F)
            name = first + " " + random.choice(LAST_NAMES)
            role = random.choices(
                ["Suspect", "Victim", "Witness"], weights=[30, 50, 20], k=1
            )[0]
            alias = ""
            if role == "Suspect" and random.random() > 0.6:
                alias = first[0] + "." + name.split()[-1]

            c.execute("""INSERT INTO persons
                (name, role, age, gender, alias, last_known_location)
                VALUES (?,?,?,?,?,?)""",
                (name, role, random.randint(18, 65), gender,
                 alias, dist if alias else ""))

            person_id = c.lastrowid
            rel_map = {
                "Suspect": "suspect_in",
                "Victim": "victim_of",
                "Witness": "witness_to"
            }
            c.execute("INSERT INTO incident_persons VALUES (?,?,?)",
                      (incident_id, person_id, rel_map[role]))

    # Generate suspect associations
    c.execute("""SELECT DISTINCT person_id FROM incident_persons
                 WHERE relationship='suspect_in'""")
    suspect_ids = [r[0] for r in c.fetchall()]
    association_types = [
        "Known Associate", "Co-accused", "Family Connection",
        "Same Gang", "Prior Cellmate"
    ]
    for _ in range(min(250, len(suspect_ids))):
        p1, p2 = random.sample(suspect_ids, 2)
        atype = random.choice(association_types)
        c.execute("INSERT OR IGNORE INTO person_associations VALUES (?,?,?,?)",
                  (p1, p2, atype, round(random.uniform(0.3, 1.0), 2)))

    conn.commit()
    conn.close()
    print("[DB] 5000 incidents generated successfully")
