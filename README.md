# Nadiya Simulator

This repository now contains a playable vertical slice prototype for **Nadiya Simulator**, a compact isometric life-sim that blends chaotic humor, grounded emotional beats, and locally hosted AI-driven dialogue. The original narrative and systems design remains available in [`docs/design.md`](docs/design.md).

The latest update stretches the day in both directions. Dawn now unfolds inside Nadiya’s apartment: wake at 06:40, sprint through shower/clothes/bag prep, and only then head out. The camera tracks her across every room and into the new bathroom while floating thought bubbles blurt the intrusive “im hungry”/“i hate people” musings you asked for. After a 10-second tram commute the school exterior, hallway, and classroom phases render on a scrolling isometric canvas with the same self-talk system and a vending machine that finally respects her €10 starting cash. The HUD clock remains clickable when you want to skip the real-time schedule, and all doors and transitions now require an explicit Enter press. Home itself was furnished with isometric couches, plants, wardrobes, and kitchen counters; Nadiya now swaps between walk cycles and an eating pose when she raids the counter snack stash.

## Getting Started

### Prerequisites
- Python 3.11+
- `pygame` (install via `pip install -r requirements.txt`)

### Running the Prototype
```bash
python game.py
```

The helper script ensures the `src` directory is discoverable before delegating to the real entrypoint. If you prefer to call the
package directly (e.g., for tooling), the following remains available:

```bash
PYTHONPATH=src python -m game.main
```

Add `--headless` to either command if you need to run in environments without a display (renders nothing but exercises the loop).

- **Movement (school & home)**: `WASD` or arrow keys for free gliding.
- **Interact / confirm**: `Space` or `Enter` to use doors, talk to NPCs, or trigger UI selections.
- **Phone (exploration segments)**: press `P` anywhere outside of menus to open/close the phone; inside the Discord app use arrows or `Q/E` to switch friends, type naturally, `Enter` to send, and `Esc`/`Backspace` to back out of apps.
- **Dialogues**: `Esc`, `Q`, `X`, or `Tab` will close any open conversation panel once you’re done reading.
- **Objective overlay**: tap `H` to toggle the “What to do” helper panel if you need a reminder of the current goals.
- **Skip segment**: click the ⏭ icon next to the HUD clock to jump to the next scheduled beat (useful if you don’t want to wait out the real-time school timings).
- **Pause / Settings**: `Esc` toggles the overlay (adjust audio, text speed, and AI usage). Close the window (Alt+F4) if you really need to exit; the game no longer binds a quit shortcut to `Esc` so dialogue dismissal stays safe.

## Gameplay Flow
Each day now hits every beat from dawn prep to midnight wind-down:
1. **Dawn – Routine** (06:40 → 07:30): wake in the bedroom, hit the bathroom for a quick shower, pick an outfit, pack the bag, and only then take the hall exit. Skip the checklist and Nadiya refuses to leave.
2. **Commute – Tram** (07:30 → 08:15): a 10-second tram cutscene advances the clock while you enjoy the skyline.
3. **Morning – School** (08:15 → 09:15): roam the exterior for 15 real seconds per in-game minute, chat with classmates (AI-enabled ones marked), dodge hallway chaos, grab vending snacks with real money, then sit for a difficulty-scaling German quiz after a short teacher monologue.
4. **Afternoon – Home**: explore the larger apartment, fry potatoes in the minigame, or interact with the roaming mom NPC for AI-guided conversation.
5. **Evening – Phone**: open the Discord-inspired phone overlay anywhere in the flat, type freely with `P`, and juggle three friend chats that react to stats and relationship scores.
6. **Night – Mom**: evening living-room scenes mix scripted beats with AI (or fallback) dialogue before bed.
7. **Sleep Transition**: fade overlay that tallies the day, applies balance tweaks, and pushes the loop to the next dawn.

Player stats (mood, hunger, energy, German skill, money, and relationships) update in real time and influence modifiers on actions. Segment transitions now include tram cutscenes, respect the real-world clock windows configured in JSON, and the HUD shows a live clock with a clickable skip icon. Press `H` any time you feel lost to reopen the contextual objective list.

## Configuration & Data

- `data/balance.json` – tunable numbers for stat deltas, timers, quiz rewards, the new `"home"` snack bonuses, and event thresholds.
- `data/ai/settings.json` – toggle AI integration. Set `"provider"` to `"pollinations"`, `"huggingface"`, `"openrouter"`, `"koboldcpp"`, or `"generic"`, point `"endpoint"` to the free service you prefer, and drop the API key name in `"api_key_env"`. When disabled the dialogue falls back to deterministic canned lines.
- `data/dialogue/bank.json` – lightweight branching dialogue nodes used to seed scripted beats before AI responses.

Edit these files to rebalance without touching code. The game hot-loads them on boot and caches in memory.

## Repository Structure
- `docs/design.md` – Full game design document.
- `src/game` – Playable prototype code (scenes, minigames, UI, state management, AI integration).
- `requirements.txt` – Python dependency list.

Future iterations can swap the stubbed AI calls with a local model server via the plumbing provided in `game.ai.local_client`.
