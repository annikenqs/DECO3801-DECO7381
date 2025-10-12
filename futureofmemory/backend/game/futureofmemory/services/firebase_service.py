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
        "faction": faction,
        "year": year,
        "scenarios": [],
        "factionVotes": [
            {"faction": "rightists", "votes": 0},
            {"faction": "resourceists", "votes": 0},
            {"faction": "responsibilists", "votes": 0}
        ],
        "playersWhoVoted": []
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

def update_faction(pin: int, faction: str):
    """Updates the faction for a session."""
    ref.document(pin).update({"faction": faction})

def vote_for_faction(pin: int, faction: str, player_id: str):
    """
    Records a player's vote for a faction.
    Returns updated vote counts and whether all players have voted.
    """
    session = get_session_by_pin(pin)
    if not session:
        raise ValueError("Invalid PIN.")
    
    if faction not in ["rightists", "resourceists", "responsibilists"]:
        raise ValueError("Invalid faction.")
    
    # Check if player already voted
    players_who_voted = session.get("playersWhoVoted", [])
    if player_id in players_who_voted:
        raise ValueError("Player has already voted.")
    
    # Update vote count for the faction
    faction_votes = session.get("factionVotes", [
        {"faction": "rightists", "votes": 0},
        {"faction": "resourceists", "votes": 0},
        {"faction": "responsibilists", "votes": 0}
    ])
    
    for vote_entry in faction_votes:
        if vote_entry["faction"] == faction:
            vote_entry["votes"] += 1
            break
    
    # Add player to voted list
    players_who_voted.append(player_id)
    
    # Update Firestore
    ref.document(pin).update({
        "factionVotes": faction_votes,
        "playersWhoVoted": players_who_voted
    })
    
    # Check if all players have voted
    total_players = session.get("numberOfPlayers", 1)
    all_voted = len(players_who_voted) >= total_players
    
    return {
        "factionVotes": faction_votes,
        "playersWhoVoted": players_who_voted,
        "allVoted": all_voted
    }

def finalize_faction_vote(pin: int):
    """
    Determines the winning faction based on votes.
    If there's a tie, randomly selects one of the tied factions.
    Returns the chosen faction.
    """
    session = get_session_by_pin(pin)
    if not session:
        raise ValueError("Invalid PIN.")
    
    faction_votes = session.get("factionVotes", [])
    
    # Find the maximum vote count
    max_votes = max(vote["votes"] for vote in faction_votes)
    
    # Get all factions with the maximum votes (handles ties)
    winning_factions = [
        vote["faction"] 
        for vote in faction_votes 
        if vote["votes"] == max_votes
    ]
    
    # Randomly select if there's a tie
    chosen_faction = random.choice(winning_factions)
    
    # Update the session with the chosen faction
    ref.document(pin).update({"faction": chosen_faction})
    
    return {
        "faction": chosen_faction,
        "factionVotes": faction_votes,
        "wasTie": len(winning_factions) > 1
    }

def get_faction_votes(pin: int):
    """
    Gets current faction vote status.
    """
    session = get_session_by_pin(pin)
    if not session:
        raise ValueError("Invalid PIN.")
    
    faction_votes = session.get("factionVotes", [])
    players_who_voted = session.get("playersWhoVoted", [])
    total_players = session.get("numberOfPlayers", 1)
    all_voted = len(players_who_voted) >= total_players
    
    print(f"[get_faction_votes] PIN: {pin}")
    print(f"[get_faction_votes] Total players: {total_players}")
    print(f"[get_faction_votes] Players who voted: {len(players_who_voted)} - {players_who_voted}")
    print(f"[get_faction_votes] All voted: {all_voted}")
    print(f"[get_faction_votes] Current faction in session: {session.get('faction')}")
    
    return {
        "factionVotes": faction_votes,
        "totalPlayers": total_players,
        "votedPlayers": len(players_who_voted),
        "allVoted": all_voted,
        "faction": session.get("faction") if all_voted else None
    }