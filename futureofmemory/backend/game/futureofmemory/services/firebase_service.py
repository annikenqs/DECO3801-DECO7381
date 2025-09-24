import firebase_admin
from firebase_admin import credentials, firestore

# Init Firebase app only once
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

def create_session(session_id: str, faction: str, year: int):
    doc_ref = db.collection("games").document(session_id)
    doc_ref.set({
        "sessionId": session_id,
        "faction": faction,
        "year": year,
        "scenarios": []
    })
    return {"sessionId": session_id, "faction": faction, "year": year}

def get_session(session_id: str):
    doc = db.collection("games").document(session_id).get()
    if doc.exists:
        return doc.to_dict()
    return None

def add_scenario(session_id: str, scenario: dict):
    doc_ref = db.collection("games").document(session_id)
    doc_ref.update({
        "scenarios": firestore.ArrayUnion([scenario])
    })
    
def update_scenarios(session_id: str, scenarios: list):
    db.collection("games").document(session_id).update({"scenarios": scenarios})

def update_year(session_id: str, year: int):
    db.collection("games").document(session_id).update({"year": year})

def update_faction(session_id: str, faction: str):
    db.collection("games").document(session_id).update({"faction": faction})