import firebase_admin
from firebase_admin import credentials, firestore

# constants
max_players = 5



# Init Firebase app only once
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# converts an integer to a six-digit string
# i.e. 1 => 000001, 3 => 000003, 102345 => 102345
def integer_to_string(number: int) -> str:
    return f"{number:06d}"

# increments pin untill overflow
def increment_pin(number: int) -> int:
    return 0 if number >= 999999 else number + 1

# uses Firestore's Transaction to maintain last pin

# @firestore.transactional: ensures the function can be run safely as a Firestore Transaction
@firestore.transactional
def allocate_pin_transaction(transaction: firestore.Transaction) -> str:

    # uses a pin counter document

    # 1. sets up a 'pin counter' object and names it as counter reference
    # 2. obtains the reference itself
    # 3. obtains the last snapshot if it exists (which is the pin)
    # 4. increments and sets the pin to a string
    # 5. sets the transaction as:
    # 1. from the pin-counter reference
    # the last value is the new value
    # and merge this

    # 1. sets up a 'pin counter' object and names it as counter reference
    counter_reference = db.collection("meta").document("pin-counter")
    # 2. obtains the reference itself
    snap = counter_reference.get(transaction=transaction)

    # gets the last snapshot if it exists, which is the pin, (otherwise makes a last snapshot of -1, 
    # which is incremented to 000000)
    last = snap.get("last") if snap.exists else -1

    # increment and set pin to string
    new_val = increment_pin(last)
    new_pin = integer_to_string(new_val)

    # sets the transaction as:
    # the pin counter object, the last value (which is the new value), and a merge command which enables merging
    transaction.set(counter_reference, {"last": new_val}, merge=True)
    # return the new pin
    return new_pin

# allocates a pin
def allocate_pin() -> str:
    tx = db.transaction()
    return allocate_pin_transaction(tx)

# creates a new session
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

# helpers - gets the pin
def get_pin(doc_id: str) -> str:
    doc_ref = db.collection("games").document(doc_id)
    snapshot = doc_ref.get()

    if not snapshot.exists:
        return ValueError("Session ID doesn't exist")

# update pin
def update_pin(doc_id: str) -> str:
    doc_ref = db.collection("games").document(doc_id)
    snapshot = doc_ref.get()

    if not snapshot.exists:
        return ValueError("Session ID doesn't exist")
    
    current_pin = snapshot.get("pin")
    try:
        current_val = int(current_pin)
    except (TypeError, ValueError):
        current_val = -1
    
    new_pin = integer_to_string(current_val)
    doc_ref.update({"pin":new_pin})
    return new_pin

def game_update(pin):
    doc = db.collection("games").document(pin).get()
    if (doc.get("numberofplayers") >= 1 or (doc.get("year") == None)): 
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