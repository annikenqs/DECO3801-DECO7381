import firebase_admin
from firebase_admin import credentials, firestore
import random

# Init Firebase app only once
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()
ref = db.collection('games')

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
def create_session(faction: str, year: int, status: str, pin: int, numberofplayers: int):
    doc_ref = db.collection("games").document(pin)
    doc_ref.set({
        "pin": pin,
        "status": status,
        "numberofplayers": numberofplayers,
        "faction": None,
        "year": year,
        "scenarios": [],
        "factionVotes": {
            "rightists": 0,
            "resourceists": 0,
            "responsibilists": 0
        },
        "factionVotedCount": 0
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

def join_session(pin: int):
    """
    Adds a player to an existing session if conditions are met.
    """
    session = get_session_by_pin(pin)

    if not session:
        raise ValueError("Invalid PIN.")

    if session.get("status") != "lobby":
        print(session.get("status"))
        raise ValueError("Game has already started and cannot be joined.")

    number_of_players = session.get("numberofplayers", 0)
    if number_of_players >= 5:
        raise ValueError("This game is full.")

    ref.document(pin).update({"numberofplayers": number_of_players + 1})

    session["numberofplayers"] = number_of_players + 1
    return session

def get_session_by_pin(pin: int):
    """Gets a session by its PIN."""
    doc = ref.document(pin).get()
    if doc.exists:
        return doc.to_dict()
    return None

def get_player_count(pin: int):
    """Returns the number of players in a session."""
    session = get_session_by_pin(pin)
    if not session:
        raise ValueError("Invalid PIN.")
    return session.get("numberofplayers", 0)

def update_game_state(pin: int, new_state: str):
    """Updates the status of a game session (e.g., from 'lobby' to 'in-progress')."""
    session = get_session_by_pin(pin)
    if not session:
        raise ValueError("Invalid PIN.")
    
    if new_state not in ["lobby", "in-progress", "finished"]:
        raise ValueError(f"Invalid game status: {new_state}")

    ref.document(pin).update({"status": new_state})
    return {"pin": pin, "status": new_state}

# The original get_session is now get_session_by_pin
get_session = get_session_by_pin

def add_scenario(pin: int, scenario: dict):
    """Adds a scenario to a session."""
    session = get_session_by_pin(pin)
    if not session:
        raise ValueError("Invalid PIN.")
    
    scenarios = session.get("scenarios", [])
    scenarios.append(scenario)
    ref.document(pin).update({"scenarios": scenarios})

def update_scenarios(pin: int, scenarios: list):
    """Updates the entire scenarios list for a session."""
    ref.document(pin).update({"scenarios": scenarios})

def update_year(pin: int, new_year: int):
    """Updates the year for a session."""
    ref.document(pin).update({"year": new_year})


def vote_for_faction(pin: str, faction: str):
    """
    Records a player's vote for a faction.
    Returns updated vote counts and whether all players have voted.
    """
    if faction not in ["rightists", "resourceists", "responsibilists"]:
        raise ValueError("Invalid faction.")

    doc_ref = ref.document(pin)
    snap = doc_ref.get()
    if not snap.exists:
        raise ValueError("Invalid PIN.")

    data = snap.to_dict() or {}

    total_players = int(data.get("numberofplayers", 0))
    voted_count = int(data.get("factionVotedCount", 0))

    if total_players > 0 and voted_count >= total_players:
        return {
            "factionVotes": data.get("factionVotes", {}),
            "allVoted": True
        }

    doc_ref.update({
        f"factionVotes.{faction}": firestore.Increment(1),
        "factionVotedCount": firestore.Increment(1)
    })

    snap = doc_ref.get()
    data = snap.to_dict() or {}
    votes = data.get("factionVotes", {})
    vc = data.get("factionVotedCount", 0)
    all_voted = (total_players > 0 and vc >= total_players)

    return {
        "factionVotes": votes,
        "allVoted": all_voted
    }


def finalize_faction_vote(pin: str):
    session = get_session_by_pin(pin)
    if not session:
        raise ValueError("Invalid PIN.")
    
    faction_votes = session.get("factionVotes", {})

    if not faction_votes:
        raise ValueError("No votes recorded.")

    max_votes = max(faction_votes.values())

    # get all factions with max votes (to handle ties)
    winning_factions = [f for f, v in faction_votes.items() if v == max_votes]

    # randomly select in case of tie
    chosen_faction = random.choice(winning_factions)

    # update session
    ref.document(pin).update({"faction": chosen_faction})

    return {
        "faction": chosen_faction,
        "factionVotes": faction_votes,
        "wasTie": len(winning_factions) > 1
    }


def get_faction_votes(pin: str):
    session = get_session_by_pin(pin)
    if not session:
        raise ValueError("Invalid PIN.")

    total_players = int(session.get("numberofplayers", 0))
    voted_players = int(session.get("factionVotedCount", 0))
    all_voted = (total_players > 0 and voted_players >= total_players)

    return {
        "factionVotes": session.get("factionVotes", {}),
        "totalPlayers": total_players,
        "votedPlayers": voted_players,
        "allVoted": all_voted,
        "faction": session.get("faction") if all_voted else None
    }