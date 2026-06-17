"""KSP Crime Intelligence Platform — Configuration & Reference Data"""

DB_PATH = "ksp_crime.db"

# External API endpoints (all free, no keys required)
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
WIKI_URL = "https://en.wikipedia.org/api/rest_v1/page/summary"

# Karnataka districts with real coordinates and police station names
DISTRICTS = {
    "Bangalore Urban": {"lat": 12.9716, "lng": 77.5946,
        "stations": ["Koramangala PS", "Indiranagar PS", "Whitefield PS", "JP Nagar PS",
                      "Rajajinagar PS", "HSR Layout PS", "Marathahalli PS",
                      "Electronic City PS", "Banashankari PS", "Jayanagar PS"]},
    "Bangalore Rural": {"lat": 13.0, "lng": 77.5,
        "stations": ["Devanahalli PS", "Hoskote PS", "Nelamangala PS", "Doddaballapur PS"]},
    "Mysore": {"lat": 12.2958, "lng": 76.6394,
        "stations": ["Nazarbad PS", "Vidyaranyapuram PS", "Saraswathipuram PS",
                      "Kuvempunagar PS", "Gokulam PS"]},
    "Hubli-Dharwad": {"lat": 15.3647, "lng": 75.124,
        "stations": ["Hubli East PS", "Hubli West PS", "Dharwad Rural PS", "Navanagar PS"]},
    "Mangalore": {"lat": 12.9141, "lng": 74.856,
        "stations": ["Pandeshwara PS", "Kadri PS", "Bunder PS", "Surathkal PS", "Attavar PS"]},
    "Belgaum": {"lat": 15.8522, "lng": 74.4986,
        "stations": ["Camp PS", "Market PS", "Shahpur PS", "Tilakwadi PS"]},
    "Gulbarga": {"lat": 17.3297, "lng": 76.8343,
        "stations": ["Gulbarga Town PS", "Afzalpur PS", "Chittapur PS"]},
    "Davangere": {"lat": 14.4643, "lng": 75.9282,
        "stations": ["Davangere Town PS", "Harihar PS", "Channagiri PS"]},
    "Bellary": {"lat": 15.1394, "lng": 76.9214,
        "stations": ["Bellary Town PS", "Hospet PS", "Siruguppa PS"]},
    "Shimoga": {"lat": 13.9299, "lng": 75.5681,
        "stations": ["Shimoga Town PS", "Bhadravathi PS", "Sagar PS"]},
    "Tumkur": {"lat": 13.34, "lng": 77.0998,
        "stations": ["Tumkur Town PS", "Madhugiri PS", "Turuvekere PS"]},
    "Raichur": {"lat": 16.2076, "lng": 77.3463,
        "stations": ["Raichur Town PS", "Manvi PS", "Sindhnur PS"]},
    "Hassan": {"lat": 13.0072, "lng": 76.0984,
        "stations": ["Hassan Town PS", "Belur PS", "Chikmagalur Road PS"]},
    "Udupi": {"lat": 13.3409, "lng": 74.742,
        "stations": ["Udupi Town PS", "Manipal PS", "Karkala PS"]},
    "Chitradurga": {"lat": 14.2284, "lng": 76.3947,
        "stations": ["Chitradurga Town PS", "Hiriyur PS", "Hosadurga PS"]},
    "Mandya": {"lat": 12.5223, "lng": 76.8966,
        "stations": ["Mandya Town PS", "Maddur PS", "Srirangapatna PS"]},
    "Bidar": {"lat": 17.9104, "lng": 77.5199,
        "stations": ["Bidar Town PS", "Basavakalyan PS", "Humnabad PS"]},
    "Dakshina Kannada": {"lat": 12.85, "lng": 75.0,
        "stations": ["Puttur PS", "Sullia PS", "Bantwal PS"]},
    "Uttara Kannada": {"lat": 14.546, "lng": 74.4955,
        "stations": ["Karwar PS", "Sirsi PS", "Honavar PS"]},
    "Koppal": {"lat": 15.3519, "lng": 76.1516,
        "stations": ["Koppal Town PS", "Gangavathi PS", "Kushtagi PS"]},
    "Gadag": {"lat": 15.4168, "lng": 75.6287,
        "stations": ["Gadag Town PS", "Laxmeshwar PS", "Nargund PS"]},
    "Haveri": {"lat": 14.7938, "lng": 75.3976,
        "stations": ["Haveri Town PS", "Ranebennur PS", "Savanur PS"]},
    "Bagalkot": {"lat": 16.1852, "lng": 75.6901,
        "stations": ["Bagalkot Town PS", "Jamkhandi PS", "Badami PS"]},
    "Chamarajanagar": {"lat": 11.9225, "lng": 76.9422,
        "stations": ["Chamarajanagar Town PS", "Kollegal PS", "Gundlupet PS"]},
    "Kodagu": {"lat": 12.3375, "lng": 75.8069,
        "stations": ["Madikeri PS", "Virajpet PS", "Somwarpet PS"]},
    "Ramanagara": {"lat": 12.7174, "lng": 77.2753,
        "stations": ["Ramanagara Town PS", "Channapatna PS", "Kanakapura PS"]},
    "Yadgir": {"lat": 16.768, "lng": 77.1323,
        "stations": ["Yadgir Town PS", "Shorapur PS", "Sedam PS"]},
}

CRIME_TYPES = [
    "Theft", "Robbery", "Burglary", "Murder", "Assault",
    "Cyber Crime", "Drug Offense", "Vehicle Theft", "Chain Snatching",
    "Fraud", "Kidnapping", "Rioting", "Arson", "Sexual Offense", "Cheating"
]
CRIME_WEIGHTS = [15, 8, 10, 3, 12, 10, 7, 12, 8, 7, 2, 3, 1, 3, 6]

SEVERITY_MAP = {
    "Theft": 3, "Robbery": 5, "Burglary": 4, "Murder": 10, "Assault": 6,
    "Cyber Crime": 7, "Drug Offense": 6, "Vehicle Theft": 4, "Chain Snatching": 3,
    "Fraud": 5, "Kidnapping": 9, "Rioting": 6, "Arson": 7, "Sexual Offense": 9, "Cheating": 4
}

MODUS_OPERANDI = [
    "Break-in through rear window", "Distraction technique",
    "Impersonation of official", "Pickpocketing in crowd", "Cyber phishing",
    "Forced entry at night", "Surveillance before attack", "Use of stolen vehicle",
    "Social engineering", "Fake identity documents", "Snatching from moving vehicle",
    "Letter bomb threat", "Hacking through public WiFi",
    "Armed confrontation", "Gaslighting victim"
]

STATUSES = [
    "Under Investigation", "Chargesheet Filed", "Closed - Untraced",
    "Convicted", "Acquitted", "Pending Trial"
]
STATUS_WEIGHTS = [25, 20, 15, 15, 10, 15]

FIRST_NAMES_M = [
    "Ravi", "Suresh", "Manoj", "Pradeep", "Kumar", "Venkatesh", "Rajesh",
    "Mohan", "Nagaraj", "Ganesh", "Shankar", "Krishna", "Murthy",
    "Basavaraj", "Mahesh", "Deepak", "Vinay", "Arun", "Siddharth", "Karthik"
]
FIRST_NAMES_F = [
    "Lakshmi", "Sujatha", "Geetha", "Priya", "Anitha", "Bhagya", "Nandini",
    "Pooja", "Divya", "Shruti", "Meera", "Kavitha", "Rekha", "Vijaya",
    "Saritha", "Asha", "Nirmala", "Padma", "Yashoda", "Suma"
]
LAST_NAMES = [
    "Kumar", "Reddy", "Gowda", "Sharma", "Patil", "Naik", "Rao", "Hegde",
    "Shetty", "Pai", "Bhat", "Kulkarni", "Desai", "Joshi", "Menon", "Nair",
    "Acharya", "Deshpande", "Mujawar", "Siddiqui"
]

# OSM uses new names; our DB uses old names
NAME_MAP = {
    "Bengaluru Urban": "Bangalore Urban", "Bengaluru Rural": "Bangalore Rural",
    "Mysuru": "Mysore", "Kalaburagi": "Gulbarga", "Ballari": "Bellary",
    "Shivamogga": "Shimoga", "Tumakuru": "Tumkur", "Chikkamagaluru": "Chikmagalur"
}
NAME_MAP_REV = {v: k for k, v in NAME_MAP.items()}

WEATHER_CITIES = [
    {"name": "Bangalore", "lat": 12.97, "lng": 77.59},
    {"name": "Mysore", "lat": 12.30, "lng": 76.65},
    {"name": "Mangalore", "lat": 12.91, "lng": 74.86},
    {"name": "Hubli", "lat": 15.36, "lng": 75.12},
    {"name": "Belgaum", "lat": 15.85, "lng": 74.50},
    {"name": "Gulbarga", "lat": 17.33, "lng": 76.83},
]
