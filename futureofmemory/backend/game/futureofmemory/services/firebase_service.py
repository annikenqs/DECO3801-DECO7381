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
    if value is None:
        doc.update({"pin":integer_to_string(0)})
        return integer_to_string(0)
    else:
        return str(value)

# updates the pin
def update_pin(doc_id: str):

    if doc_id is None:
        return None
    
    doc = db.collection("games").document(doc_id) # which is the pin

    def transaction_logic(trans):
        snap = doc.get(transaction=trans) # obtains a document snapshot
        if not snap.exists:
            # Option 1: create it with 000000
            zero = integer_to_string(0)
            trans.set(doc, {"pin": zero}, merge=True)
            return zero

        value = snap.get("pin")
        try:
            cur = int(value) # try converting value to int
        except (TypeError, ValueError): # if errors:
            cur = -1 # increment transforms -1 to 0 => 000000                              

        new_val = increment_pin(cur)
        new_pin = integer_to_string(new_val)
        trans.update(doc, {"pin": new_pin})
        return new_pin
    return db.transaction()(transaction_logic)
    

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