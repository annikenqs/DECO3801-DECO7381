// Game helpers using Firestore (CDN modules)
import { db } from "./firebaseClient.js";
import {
  doc,
  getDoc,
  runTransaction,
  updateDoc,
  deleteField,

} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

// sets the game status, taking in the game pin and the status string
export async function setGameStatus(pin, status) {
  // creates a reference to the game document at /games/{pin}
  const ref = doc(db, "games", pin);

  // updates the 'status' field in Firebase (with the in-game status) 
  await updateDoc(ref, { status, updatedAt: Date.now() });
}

// sets the worldview
export async function setWorldview(pin, worldview) {

  const ref = doc(db, "games", pin);

  // updates the 'worldview' field in Firebase (with the in-game worldview)
  await updateDoc(ref, { worldview, updatedAt: Date.now() });
}

export async function setTurnPrompt(pin, prompt) {
  const ref = doc(db, "games", pin);

  // updates the turn prompt in Firebase (i.e. the scenario prompt) with the in-game prompt
  await updateDoc(ref, { "turn.prompt": prompt, updatedAt: Date.now() });
}

export async function addPlayer(pin, playerId, name) {
  const ref = doc(db, "games", pin);

  // updates the players in firebase with the new player's ID and their name
  await updateDoc(ref, {
    [`players.${playerId}`]: { name },
    updatedAt: Date.now(),
  });
}

export async function removePlayer(pin, playerId) {
  const ref = doc(db, "games", pin);

  // removes the player in firebase 
  await updateDoc(ref, {
    [`players.${playerId}`]: deleteField(),
    updatedAt: Date.now(),
  });
}

// vote with transaction to prevent double voting
export async function castVote(pin, playerId, optionId) {

  // point to /games/{pin}
  const ref = doc(db, "games", pin);

  // uses Firebase's runTransaction function - prevents double voting
  await runTransaction(db, async (tx) => {

    // takes in the document at /games/{pin}
    // serialises the document's current fields and values
    const snap = await tx.get(ref);

    // if it doesn't exist, then a game hasn't been created
    if (!snap.exists()) throw new Error("Game not found");

    // grab the JS object in snap
    const game = snap.data();

    // if a player has already voted (i.e. if playerId exists in voters), then do nothing
    if (Array.isArray(game.turn?.voters) && game.turn.voters.includes(playerId)) {
      return;
    }

    // builds the question's answers (i.e the options) based on the options in firebase-demo.html
    const options = (game.turn?.options || []).map((o) =>
      o.id === optionId ? { ...o, votes: (o.votes || 0) + 1 } : o
    );

    // determines all voters based on the voters list 
    const voters = [...(game.turn?.voters || []), playerId];

    // updates options and voters
    tx.update(ref, {
      "turn.options": options,
      "turn.voters": voters,
      updatedAt: Date.now(),
    });
  });
}

// generates a random pin 
const generatePin = () => String(Math.floor(100000 + Math.random() * 900000));

// creates a new game session
export async function createGameSession({ worldview = null, turn } = {}) {
  
  // use a turn object if provided, otherwise build an empty turn with the current year and everything else as blank
  const initialTurn = turn ?? {
    year: new Date().getFullYear(),
    prompt: "",
    options: [],
    voters: [],
    state: "voting",
  };

  // use Firebase's runTransaction function
  return await runTransaction(db, async (tx) => {

    // try five times:
    for (let i = 0; i < 5; i++) {

      // generate a random six-digit pin
      const pin = generatePin();
      // point to /games/{pin}
      const ref = doc(db, "games", pin);
      // takes in the document's current fields and values
      const snap = await tx.get(ref);

      // if it doesn't exist: create one
      // create one with all requisite context
      if (!snap.exists()) {
        const now = Date.now();
        tx.set(ref, {
          status: "lobby",
          pin,
          worldview,
          players: {},
          turn: Array.isArray(initialTurn.options)
            ? {
                ...initialTurn,
                options: initialTurn.options.map((o) => ({
                  id: o.id,
                  text: o.text,
                  votes: o.votes ?? 0,
                })),
              }
            : initialTurn,
          createdAt: now,
          updatedAt: now,
        });
        return { pin };
      }
    }
    // if an identical pin is somehow generated 5x in a row, abort
    throw new Error("PIN collision. Please try again.");
  });
}

// tries to load a game document with a pin
export async function getGameByPin(pin) {
  // try to find one
  const snap = await getDoc(doc(db, "games", pin));
  // if so, returns an object w pin + all requisite game data
  // otherwise gives null (i.e. it doesnt exist)
  return snap.exists() ? { id: snap.id, ...snap.data() } : null;
}
