# Nadiya Simulator Design Document

## 1. Working Title

"Nadiya Simulator" — an isometric, AI-assisted narrative life-sim that balances chaotic humor, light emotional undertones, and fully local/offline systems.

## 2. Core Vision

Guide Nadiya through a repeating day cycle that blends:

- **Fry-cooking chaos** in a compact kitchen.
- **Social and academic absurdity** at a language school.
- **AI-driven home life** with her mother.
- **Text-based interactions** with friends.

The overall tone stays comedic and weird, while AI-powered dialogue injects authentic emotional realism. All systems remain lightweight, deterministic where it matters, and rely on locally hosted AI for the key characters.

## 3. Player Perspective & Visual Style

- **Perspective:** Fixed-camera 2D isometric (2.5D) presentation.
- **Art Style:**
  - Pixel art at 320×180 base resolution, scaled cleanly.
  - Isometric tiles sized 32×32 or 48×48.
  - Warm neutral palette with accented colors for fries, UI, and emotional cues.
  - Simple shading to imply volume; no complex lighting.
- **Key Locations:**
  1. **Kitchen:** Fryer, counter, sink, table, clutter. Interaction zones for cooking, eating, reflection.
  2. **School:** Hallway and classroom with NPC classmates on isometric paths and a teacher NPC. Trigger zones for tests, dodge segments, dialogue.
  3. **Home:** Living room (mom’s presence) plus Nadiya’s bedroom (sleep, PC, chat) connected by a short corridor. Compact spaces keep traversal minimal.

## 4. Core Loop

Each in-game day flows through discrete segments:

1. **Morning – School**
   - Navigate the hallway, avoid certain classmates, and optionally take micro language challenges.
   - Outcomes adjust mood, energy, and German skill XP.
2. **Afternoon – Fries / Tasks**
   - Play the fry-cooking minigame: dodge oil, time fries.
   - Success improves hunger and mood; mistakes affect mood and add flavor text.
3. **Evening – Social Chat**
   - Use the PC to text friends via AI-driven or scripted conversations.
   - Influences mood and relationship flags.
4. **Night – Mom Events**
   - Interact with Mom, whose demeanor varies (neutral, tired, drunk and oversharing).
   - AI-driven dialogue delivers lore and emotional beats, impacting mood and long-term flags.
5. **Sleep**
   - Restores energy based on prior actions and may trigger symbolic dream snippets.

The day repeats with incremental variations and evolving states.

## 5. Player Stats & Systems

Track the following global stats:

- **Mood:** 0–100
- **Hunger:** 0–100
- **Energy:** 0–100
- **German Skill:** Level with XP
- **Relationship – Mom:** 0–100
- **Relationship – Friends:** 0–100 per friend
- **Flags / Events:** Booleans and enums for narrative state, unlocks, trauma stories, etc.

Balancing guidelines:

- Low hunger penalizes mood and energy.
- Low energy slows movement and shrinks minigame success windows.
- High mood widens success windows and prompts more playful AI responses.
- Relationship scores steer AI personas and available responses.
- AI prompting is parameterized by these values to keep behavior predictable.

## 6. Minigames & Mechanics

### 6.1 Fry Cooking – "Oil Hell"

- **View:** Zoomed-in isometric kitchen.
- **Mechanics:**
  - Control Nadiya on a small grid while the fryer emits oil splashes on diagonals.
  - Time fry interactions (drop, flip, pull) using a single interaction key within precise windows.
  - Deterministic patterns with slight randomness maintain replayability.
- **Outcomes:**
  - Perfect timing boosts hunger and mood, awarding score.
  - Over/undercooking reduces gains, prompting Nadiya comments.
  - Multiple oil hits reduce mood and add cosmetic injuries and dialogue variations.

### 6.2 School – "Dodge + Test"

1. **Hallway Dodge**
   - Isometric lane with moving NPCs; annoying ones are visually marked.
   - Collisions trigger brief dialogues and mood penalties; clean runs grant mood boosts.
2. **German Test**
   - Quick quizzes (3–5 questions) on translations or word order.
   - Difficulty scales with German skill.
   - Passing improves German skill and mood; failing harms mood and triggers teasing.

### 6.3 Friends Chat

- **UI:** Retro chat overlay with manual player input.
- **Responses:** Either limited local AI (for core friends) or a weighted template system.
- **Constraints:** Each friend has defined personality, tone, and topic boundaries. Context includes recent messages and relevant game state.

### 6.4 Mom Events

- **Trigger:** Night segment interactions in the living room.
- **Modes:**
  - Normal: brief supportive or neutral remarks.
  - Drunk: longer, introspective monologues.
- **AI Integration:**
  - Prompts include persona descriptions and state flags (e.g., `mom_drunk`, relationship score).
  - Outputs are filtered, length-capped, and presented via dialogue choices for Nadiya.

## 7. UI & UX Specification

- **HUD:**
  - Bottom-left bars for mood, hunger, energy with icons.
  - Top-center time-of-day indicator.
  - Top-right day counter.
  - Minimal footprint outside cutscenes.
- **Dialogue:**
  - Bottom panel text box with portrait, name, and typewriter effect.
  - Quick comments through speech bubbles.
  - Choices presented as simple lists when applicable.
- **Isometric Navigation:**
  - WASD/arrow keys mapped to isometric axes.
  - Single interaction key (E/Space).
  - Interactables highlighted with outlines or icons when in range.

## 8. Technical Architecture

- **Engine:** Godot 4.x using TileMap and scene systems.
- **Language:** GDScript or C# (developer preference).
- **AI Backend:** Local server (Ollama, LM Studio) exposing `POST /generate` with prompt, system message, and metadata. Use small instruction-tuned models (2–7B parameters).

### 8.1 Core Modules

- **GameStateManager:** Maintains stats, flags, relationships, current day segment; handles JSON save/load.
- **SceneController:** Orchestrates transitions (school → kitchen → PC → living room → sleep) and triggers minigames or AI events.
- **CharacterController:** Provides isometric movement, collision, and simple state machine (idle/move/interact).
- **UIManager:** Manages HUD, dialogue boxes, chat windows, and safely displays AI responses.
- **Minigame Controllers:** Separate controllers for fry cooking, school hallway, German tests. Each emits outcomes back to `GameStateManager`.
- **AIManager:** Wraps communication with the local model server, handles prompt templates, token limits, and post-filtering.

## 9. AI Design

### 9.1 Prompt Strategy

- Use strict system prompts for stability.
- Example (Mom):
  - **System:** Defines persona, state (sober/drunk), tone, and content boundaries.
  - **Context:** Day number, Nadiya’s mood, recent events, relationship score, and previous dialogue.
  - **User:** Nadiya’s latest input or scene trigger.
- Generate concise (1–3 sentence) responses formatted for dialogue.
- Apply similar templates for friends, with tailored personalities.

### 9.2 Safety & Control

- Apply hard filters for disallowed content.
- Truncate rambling outputs.
- Fall back to canned lines if AI output misbehaves.

### 9.3 Performance

- Only query AI during key events (mom scenes, chat messages).
- Maintain compact context caches.
- Run models at low temperature for consistent tone.

## 10. Content Tone & Boundaries

- Dark, absurd humor framed as mutual and friendly.
- Handle sensitive themes carefully and avoid glorifying harmful behavior.
- Keep dialogue personal, slightly broken, but human.

## 11. Extensibility

Design the codebase for expansion with:

- Additional locations (tram, supermarket).
- More stats (stress, comfort).
- Extra AI NPCs as performance allows.
- Moddable dialogues and assets exposed via JSON and sprite directories.

