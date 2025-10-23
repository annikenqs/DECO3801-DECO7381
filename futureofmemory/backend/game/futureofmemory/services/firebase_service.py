"""
firebase_service.py
-------------------
Handles all Firestore interactions for game sessions, including
PIN allocation, session creation, scenario updates, and voting logic.
"""
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Optional
import random
import json
import os
from game.futureofmemory.services.llm_service import _extract_json_obj

# Init Firebase app 
if not firebase_admin._apps:
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "serviceAccountKey.json")
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()
ref = db.collection('games')


def integer_to_string(number: int) -> str:
    """ converts an integer to a six-digit string i.e. 1 => 000001, 3 => 000003, 102345 => 102345"""
    return f"{number:06d}"

def increment_pin(number: int) -> int:
    """increments pin untill overflow, then resets to 0"""
    return 0 if number >= 999999 else number + 1


@firestore.transactional
def allocate_pin_transaction(transaction: firestore.Transaction) -> str:
    """
        Allocates a new unique pin for a game session.
        Steps involved:

        1. sets up a 'pin counter' object and names it as counter reference
        2. obtains the reference itself
        3. obtains the last snapshot if it exists (which is the pin)
        4. increments and sets the pin to a string
        5. sets the transaction as the pin counter object, the last value (which is the new value), and a merge command which enables merging
        6. return the new pin
    """
    
    counter_reference = db.collection("meta").document("pin-counter")
    snap = counter_reference.get(transaction=transaction)
    last = snap.get("last") if snap.exists else -1

    new_val = increment_pin(last)
    new_pin = integer_to_string(new_val)

    transaction.set(counter_reference, {"last": new_val}, merge=True)
    return new_pin

@firestore.transactional
def increment_choice_vote_transaction(transaction: firestore.Transaction, pin: str, scenario_id: int, choice_id: int) -> dict:
    """
        Increments the vote count for a specific choice within a scenario atomically.
        Steps involved:
        1. obtains the pin
        2. checks if the pin is valid or not
        3. converts the reference to a dictionary
        4. obtains the scenarios
        5. searches for the scenario id
        6. Increments the right choice
        7. update the scenario in the list
        8. update the document with the new scenarios list
        9. update tally as well
        10. return the pin, scenario id, tally and choices

    """
    doc_ref = ref.document(pin)
    snap = doc_ref.get(transaction=transaction)

    if not snap.exists:
        raise ValueError("Error: Invalid PIN!")
    
    data = snap.to_dict() or {}
    scenarios = data.get("scenarios", [])
    idx = next((i for i, s in enumerate(scenarios) if s.get("id") == scenario_id), None)

    if idx is None:
        raise ValueError(f"Scenario {scenario_id} not found.")

    scenario = scenarios[idx]

    # set found to false initially, since we haven't found a matching id yet
    found = False

    # for each choice, check if the id matches and increment votes accordingly
    for ch in scenario.get("choices", []):
        if ch.get("id") == choice_id:
            ch["votes"] = int(ch.get("votes", 0)) + 1
            found = True
            break
    if not found:
        raise ValueError(f"Choice {choice_id} not found in scenario {scenario_id}.")
    
    scenarios[idx] = scenario
    transaction.update(doc_ref, {"scenarios": scenarios})
    tally = {str(ch.get("id")): int(ch.get("votes", 0)) for ch in scenario.get("choices", [])}

    return {"pin": pin, "scenarioId": scenario_id, "votes": tally, "choices": scenario.get("choices", [])}

def increment_choice_vote(pin: str, scenario_id: int, choice_id: int) -> dict:
    """Increments the vote count for a specific choice within a scenario."""
    tx = db.transaction()
    # use the transaction to increment the choice vote
    return increment_choice_vote_transaction(tx, pin, scenario_id, choice_id)


def allocate_pin() -> str:
    """Allocates a new unique pin for a game session."""
    tx = db.transaction()
    return allocate_pin_transaction(tx)


def create_session(faction: str, year: int, status: str, pin: int, numberofplayers: int):
    """Creates a new game session with the given parameters."""
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



def join_session(pin: int):
    """Allows a player to join a game session using its pin."""
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
    """Retrieves a game session by its pin."""
    doc = ref.document(pin).get()
    if doc.exists:
        return doc.to_dict()
    return None


def get_player_count(pin: int):
    """Retrieves the number of players in a game session."""
    session = get_session_by_pin(pin)
    if not session:
        raise ValueError("Invalid PIN.")
    return session.get("numberofplayers", 0)

def update_game_state(pin: int, new_state: str):
    """Updates the game state for a session."""
    session = get_session_by_pin(pin)
    if not session:
        raise ValueError("Invalid PIN.")
    
    if new_state not in ["lobby", "in-progress", "finished"]:
        raise ValueError(f"Invalid game status: {new_state}")

    ref.document(pin).update({"status": new_state})
    return {"pin": pin, "status": new_state}


def pick_winner_from_choices(choices):
    """Picks the winning choice based on votes, with tie-breaking by lowest id."""
    return max(choices, key=lambda ch: (int(ch.get("votes", 0)), -int(ch.get("id", 0))))


def add_scenario(pin: int, scenario: dict):
    """Adds a scenario to a session."""
    session = get_session_by_pin(pin)
    if not session:
        raise ValueError("Invalid PIN.")
    
    scenario.setdefault("year", session.get("year"))

    # ensure votes field exists on each choice
    norm_choices = []
    for c in scenario.get("choices", []):
        norm_choices.append({
            "id": c.get("id"),
            "text": c.get("text"),
            "votes": int(c.get("votes", 0))  
        })
    
    # update scenario choices
    scenario["choices"] = norm_choices
    
    scenarios = session.get("scenarios", [])
    scenarios.append(scenario)

    ref.document(pin).update({"scenarios": scenarios})


def update_scenarios(pin: int, scenarios: list):
    """Updates the scenarios for a session."""
    ref.document(pin).update({"scenarios": scenarios})

def update_year(pin: int, new_year: int):
    """Updates the year for a session."""
    ref.document(pin).update({"year": new_year})

def vote_for_faction(pin: str, faction: str):
    """Records a vote for a faction in a session."""

    if faction not in ["rightists", "resourceists", "responsibilists"]:
        raise ValueError("Invalid faction.")
    
    doc_ref = ref.document(pin)
    snap = doc_ref.get()

    if not snap.exists:
        raise ValueError("Invalid PIN.")

    data = snap.to_dict() or {}

    total_players = int(data.get("numberofplayers", 0))
    voted_count = int(data.get("factionVotedCount", 0))

    # if all players have already voted, return the existing votes and set allVoted to true
    if total_players > 0 and voted_count >= total_players:
        return {
            "factionVotes": data.get("factionVotes", {}),
            "allVoted": True
        }

    doc_ref.update({
        f"factionVotes.{faction}": firestore.Increment(1),
        "factionVotedCount": firestore.Increment(1)
    })

    # re-fetch the document to get updated votes
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
    """Finalizes the faction vote for a session."""

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

    ref.document(pin).update({"faction": chosen_faction})

    return {
        "faction": chosen_faction,
        "factionVotes": faction_votes,
        "wasTie": len(winning_factions) > 1
    }


def get_faction_votes(pin: str):
    """Retrieves the faction votes for a session."""
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


def _normalize_choices_for_storage(raw_choices: list) -> list:
    """Normalizes raw choices into a standard format for storage."""

    norm = []
    # for each choice in the raw choices (up to 3):
    for idx, ch in enumerate((raw_choices or [])[:3], start=1):
        # obtain the choice id
        cid = ch.get("id", idx)

        if isinstance(cid, str) and cid.upper() in ("A", "B", "C"):
            cid = {"A": 1, "B": 2, "C": 3}[cid.upper()]
        # try to convert the cid to an integer, otherwise use the index
        try:
            cid = int(cid)
        except Exception:
            cid = idx

        # obtain the choice text
        ctext = ch.get("text") or ch.get("label") or f"Option {cid}"

        norm.append({
            "id": cid,
            "text": ctext,
            "votes": int(ch.get("votes", 0)),
        })

    # if empty, provide a fallback set
    if not norm:
        norm = [
            {"id": 1, "text": "Fallback choice A", "votes": 0},
            {"id": 2, "text": "Fallback choice B", "votes": 0},
            {"id": 3, "text": "Fallback choice C", "votes": 0},
        ]

    return norm


@firestore.transactional
def add_first_scenario_if_absent_txn(transaction: firestore.Transaction, pin: str, scenario: dict) -> dict:
    """Atomically adds the first scenario if none exist."""

    doc_ref = ref.document(pin)
    snap = doc_ref.get(transaction=transaction)

    if not snap.exists:
        raise ValueError("Invalid PIN.")

    data = snap.to_dict() or {}
    scenarios = data.get("scenarios", [])
    if scenarios:
        return scenarios[0]

    # obtains the year from the scenario or defaults to 2075
    year = int(data.get("year", 2075))

    text_in = scenario.get("text") or scenario.get("scenario_text") or ""
    choices_in = scenario.get("choices") or []
    if isinstance(text_in, str) and text_in.strip().startswith("{"):
        maybe = _extract_json_obj(text_in)
        if isinstance(maybe, dict):
            text_in = maybe.get("scenario_text") or maybe.get("text") or text_in
            if not choices_in:
                choices_in = maybe.get("choices") or []

    # Normalize choices and assemble the scenario we will write
    normalized_choices = _normalize_choices_for_storage(scenario.get("choices", []))

    # define the scenario to write
    scenario_to_write = {
        "id": 1,
        "text": scenario.get("text") or scenario.get("scenario_text") or "No scenario generated (fallback)",
        "choices": normalized_choices,
        "chosen": None,
        "year": year,
        "citations": scenario.get("citations", []),
    }

    # Append atomically
    new_scenarios = scenarios + [scenario_to_write]
    transaction.update(doc_ref, {"scenarios": new_scenarios})

    return scenario_to_write



def add_first_scenario_if_absent(pin: str, scenario: dict) -> dict:
    """Adds the first scenario if none exist."""
    tx = db.transaction()
    return add_first_scenario_if_absent_txn(tx, pin, scenario)

@firestore.transactional
def add_next_scenario_if_absent_txn(
    transaction: firestore.Transaction,
    pin: str,
    expected_new_id: int,
    candidate: dict,
    new_year: int,
) -> dict:

    """Atomically appends the next scenario with id=expected_new_id if missing.
    - Returns the existing scenario if it already exists (idempotent).
    - Validates that previous scenario is finalized (has "chosen").
    - Updates session.year together with the append.
    """
    doc_ref = ref.document(pin)
    snap = doc_ref.get(transaction=transaction)
    if not snap.exists:
        raise ValueError("Invalid PIN.")

    data = snap.to_dict() or {}
    scenarios = data.get("scenarios", [])

    # If a scebarui already exists, return it 
    existing = next((s for s in scenarios if int(s.get("id", 0)) == int(expected_new_id)), None)
    if existing:
        return existing

    # Must have a finalized previous scenario
    prev_id = expected_new_id - 1
    prev = next((s for s in scenarios if int(s.get("id", 0)) == prev_id), None)
    if not prev or prev.get("chosen") is None:
        raise ValueError("Previous scenario not finalized.")

    text_in = candidate.get("text") or candidate.get("scenario_text") or ""
    choices_in = candidate.get("choices") or []
    if isinstance(text_in, str) and text_in.strip().startswith("{"):
        maybe = _extract_json_obj(text_in)
        if isinstance(maybe, dict):
            text_in = maybe.get("scenario_text") or maybe.get("text") or text_in
            if not choices_in:
                choices_in = maybe.get("choices") or []

    # Normalize candidate
    choices = _normalize_choices_for_storage(candidate.get("choices", []))
    text = candidate.get("text") or candidate.get("scenario_text") or "No scenario generated (fallback)"

    # Define the scenario to write 
    scenario_to_write = {
        "id": int(expected_new_id),
        "text": text,
        "choices": choices,
        "chosen": None,
        "year": int(new_year),
        "citations": candidate.get("citations", []),
    }

    # Append & bump year atomically
    new_list = scenarios + [scenario_to_write]
    transaction.update(doc_ref, {"scenarios": new_list, "year": int(new_year)})

    return scenario_to_write

def add_next_scenario_if_absent(pin: str, expected_new_id: int, candidate: dict, new_year: int) -> dict:
    """Appends the next scenario with id=expected_new_id if missing."""
    tx = db.transaction()
    return add_next_scenario_if_absent_txn(tx, pin, expected_new_id, candidate, new_year)






