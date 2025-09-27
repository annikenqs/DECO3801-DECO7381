import firebase_admin
from firebase_admin import credentials, firestore
import random
import string

# Init Firebase app only once
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
ref = db.collection('games')

def _generate_pin(length=6):
    """Generates a random alphanumeric PIN."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def _generate_unique_pin():
    """Generates a unique PIN that is not already in use."""
    while True:
        pin = _generate_pin()
        doc = ref.document(pin).get()
        if not doc.exists:
            return pin

def create_session(faction: str = "Unknown", year: int = 2075):
    """
    Creates a new game session with a unique PIN.
    The creator is automatically added as the host.
    """
    pin = _generate_unique_pin()
    session_data = {
        "pin": pin,
        "state": "lobby",  # Game states: "lobby", "in-progress", "finished"
        "numberOfPlayers": 1,
        "faction": faction,
        "year": year,
        "scenarios": []
    }
    ref.document(pin).set(session_data)
    return session_data

def join_session(pin: str, nickname: str):
    """
    Adds a player to an existing session if conditions are met.
    """
    session = get_session_by_pin(pin)

    if not session:
        raise ValueError("Invalid PIN.")

    if session.get("state") != "lobby":
        print(session.get("state"))
        raise ValueError("Game has already started and cannot be joined.")

    number_of_players = session.get("numberOfPlayers", 0)
    if number_of_players >= 5:
        raise ValueError("This game is full.")


    ref.document(pin).update({"numberOfPlayers": number_of_players + 1})

    session["numberOfPlayers"] = number_of_players + 1
    return session

def get_session_by_pin(pin: str):
    """Gets a session by its PIN."""
    doc = ref.document(pin).get()
    if doc.exists:
        return doc.to_dict()
    return None

def get_player_count(pin: str):
    """Returns the number of players in a session."""
    session = get_session_by_pin(pin)
    if not session:
        raise ValueError("Invalid PIN.")
    return session.get("numberOfPlayers", 0)

def update_game_state(pin: str, new_state: str):
    """Updates the state of a game session (e.g., from 'lobby' to 'in-progress')."""
    session = get_session_by_pin(pin)
    if not session:
        raise ValueError("Invalid PIN.")
    
    if new_state not in ["lobby", "in-progress", "finished"]:
        raise ValueError(f"Invalid game state: {new_state}")

    ref.document(pin).update({"state": new_state})
    return {"pin": pin, "state": new_state}

# The original get_session is now get_session_by_pin
get_session = get_session_by_pin

def add_scenario(pin: str, scenario: dict):
    """Adds a scenario to a session."""
    session = get_session_by_pin(pin)
    if not session:
        raise ValueError("Invalid PIN.")
    
    scenarios = session.get("scenarios", [])
    scenarios.append(scenario)
    ref.document(pin).update({"scenarios": scenarios})

def update_scenarios(pin: str, scenarios: list):
    """Updates the entire scenarios list for a session."""
    ref.document(pin).update({"scenarios": scenarios})

def update_year(pin: str, new_year: int):
    """Updates the year for a session."""
    ref.document(pin).update({"year": new_year})

def update_faction(pin: str, faction: str):
    """Updates the faction for a session."""
    ref.document(pin).update({"faction": faction})