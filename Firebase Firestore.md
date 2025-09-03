### Firebase Firestore Database Structure

Our database model is designed with a hierarchical, nested structure, organizing data around the core concept of a game session (Session). This approach clearly isolates each individual gameplay experience, ensuring data independence and query efficiency. The database primarily consists of two top-level collections: users and sessions.

#### 1. users Collection

- Purpose and Role:
  The users collection serves as the user hub for the entire application. Its core purpose is to store and manage the account information of all participants. Each document represents an individual user. This collection is the foundation for user registration, login, and identity verification.
- Document Structure (/users/{userId}):
  - nickname (String): The user's public display name.
  - password (String): Stores the hashed value of the user's password, used for authentication during login.
  - createdAt (Timestamp): Records the creation time of the user's account.

#### 2. sessions Collection

- Purpose and Role:
  The sessions collection is the most critical part of the project. It records each independent game process, whether in single-player or multi-player mode. Each document represents a complete simulation experience from start to finish. All data related to a specific game's state and history is organized under a document in this collection and its subcollections.
- Document Structure (/sessions/{sessionId}):
  - mode (String): Marks the session as either "single_player" or "multi_player".
  - status (String): Describes the current phase of the session, such as "lobby" (waiting for players to join), "in_progress" (game is active), or "finished" (game has ended).
  - participantIds (Array): An array storing the userIds of all players participating in this session.
  - currentYear (Number): A state pointer that tracks the current simulated year of the game (e.g., 2075, 2076...).
  - worldState (Map): The core state machine of the game. It is an object containing multiple quantitative metrics (e.g., publicTrust, techRegulation). The values of these metrics change dynamically based on player decisions and directly influence the content of subsequent AI-generated events.

#### Subcollections: Dynamic Data Expansion

To clearly organize the dynamic data within a session, we nest two key subcollections under each session document: events and decisions.

- events Subcollection (/sessions/{sessionId}/events/{year}):
  - Purpose and Role: This collection serves as the game's narrative log, storing all events that have occurred, organized by year. Each document represents a key event and the choices available to players for that year.
  - Document Structure:
    - description (String): The AI-generated descriptive text for the event.
    - options (Array of Maps): An array of option objects. Each option object contains:
      - text (String): The descriptive text for the option.
      - worldStateChange (Map): The core game mechanic. This is a hidden instruction set that precisely defines how the various metrics in the worldState should change if a player selects this option (e.g., {"publicTrust": -10}).
- decisions Subcollection (/sessions/{sessionId}/decisions/{decisionId}):
  - Purpose and Role: This collection is a log of player actions, recording every specific decision made. It is crucial for tracking game history, analyzing player behavior, and implementing the voting mechanism in multi-player games.
  - Document Structure:
    - userId (String): The ID of the player who made this decision.
    - year (Number): The year in which the decision was made.
    - chosenOptionId (String): An identifier for the option chosen by the player (e.g., "A", "B").

### Logical Relationships Between Collections

1. users and sessions Connection:
   - The participantIds array in a sessions document directly references the document IDs (userId) from the users collection. This establishes a clear "who participated in which game" relationship.
2. sessions and its Subcollections Connection:
   - As subcollections of sessions, events and decisions are inherently tied to their parent session document. This forms a natural parent-child relationship, representing "which events and decisions belong to which game session."
3. events and decisions Connection:
   - The year field in a decisions document corresponds to the document ID (the year) in the events subcollection. This creates an explicit link, indicating "which decision was made for which event."
4. decisions and users Connection:
   - The userId field in a decisions document directly references a document ID in the users collection, indicating "which player made this decision."
