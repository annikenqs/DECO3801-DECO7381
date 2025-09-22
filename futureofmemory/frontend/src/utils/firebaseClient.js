// src/js/firebaseClient.js
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import { initializeFirestore, setLogLevel } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

// Optional: get detailed logs in DevTools
setLogLevel("debug");

const firebaseConfig = {
  apiKey: "AIzaSyAT5CrY-O8J93gyTBvyivm5HfWON2rpcXI",
  authDomain: "fomemory-891e3.firebaseapp.com",
  projectId: "fomemory-891e3",
  storageBucket: "fomemory-891e3.firebasestorage.app",
  messagingSenderId: "337146772437",
  appId: "1:337146772437:web:ef343c3cd9e038d7555b5c"
};


export const app = initializeApp(firebaseConfig);

// Use initializeFirestore to pass settings
export const db = initializeFirestore(app, {
  //experimentalAutoDetectLongPolling: true,     // try this first
  experimentalForceLongPolling: true,       // if still failing, switch to this
  ignoreUndefinedProperties: true,
});