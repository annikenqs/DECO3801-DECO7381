import firebase_admin
from firebase_admin import credentials, firestore

# constants
max_players = 5



# Init Firebase app only once
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

def create_session(faction: str, year: int, status: str, pin: str, numberofplayers: int):
    doc_ref = db.collection("games").document(pin)
    doc_ref.set({
        "pin": pin,
        "status": status,
        "numberofplayers": numberofplayers,
        "faction": faction,
        "year": year,
        "scenarios": []
    })
    return {"pin": pin, "faction": faction, "year": year}


# converts an integer to a six-digit string
# i.e. 1 => 000001, 3 => 000003, 102345 => 102345
def integer_to_string(number: int) -> str:
    return f"{number:06d}"

# increments pin untill overflow
def increment_pin(number: int) -> int:
    return 0 if number >= 999999 else number + 1

# gets the pin
def get_pin(pin: str) -> str:

    doc = db.collection("games").document(pin)
    doc_ref = doc.get()

    # if the document doesn't exist, return none
    if not doc_ref.exists:
        return None
    
    value = doc_ref.get("pin")

    # if the pin doesn't exist, make one (start of very first game)
    if value == None:
        doc.update({"pin":integer_to_string(0)})
        return integer_to_string(0)
    else:
        return str(value)

# updates the pin
def update_pin(doc_id: str):
    doc = db.collection("games").document(doc_id)

    current_pin = get_pin(doc_id)

    if current_pin is None:
        return None
    
    try:
        current_value = int(current_pin)
    except (TypeError, ValueError):
        current_value = -1
    
    new_val = increment_pin(current_value)
    new_pin = integer_to_string(new_val)
    doc.update({"pin":new_pin})

    return new_pin
    

# to do:
# create "status"
# create "numberOfPlayers" (limit = 5)
# create "choices"

def game_update(pin):
    doc = db.collection("games").document(pin).get()
    if (doc.get("numberofplayers") >= 1 or (doc.get("year") == None)): # since 
        db.collection("games").document(pin).update({"status": "lobby"})
    elif (doc.get("year") >= 2075):
        db.collection("games").document(pin).update({"status": "active"})
    elif (doc.get("year") == 2085):
        db.collection("games").document(pin).update({"status": "finished"})

# status is lobby when we're in lobby
# status is active when game has started
# status is finished when game has finished

def update_numberofplayers(pin: str, numberofplayers: int):
    db.collection("games").document(pin).update({"numberofplayers": numberofplayers})

def get_session(pin: str):
    doc = db.collection("games").document(pin).get()
    if doc.exists:
        return doc.to_dict()
    return None

def add_scenario(pin: str, scenario: dict):
    doc_ref = db.collection("games").document(pin)
    doc_ref.update({
        "scenarios": firestore.ArrayUnion([scenario])
    })
    
def update_scenarios(pin: str, scenarios: list):
    db.collection("games").document(pin).update({"scenarios": scenarios})

def update_year(pin: str, year: int):
    db.collection("games").document(pin).update({"year": year})

def update_faction(pin: str, faction: str):
    db.collection("games").document(pin).update({"faction": faction})

def get_lobby_status(pin: str):
    # TODO: implement later
    return None

def join_lobby(pin: str, player_id=None, nickname=None):
    # TODO: implement later
    return {"ok": True, "msg": "Placeholder"}