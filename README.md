# Nadiya Simulator

This repository now contains a playable vertical slice prototype for **Nadiya Simulator**, a compact isometric life-sim that blends chaotic humor, grounded emotional beats, and locally hosted AI-driven dialogue. The original narrative and systems design remains available in [`docs/design.md`](docs/design.md).

The latest update expands both ends of the day: mornings now play out in real time with an explorable school exterior, hallway roam, and escalating German class, while afternoons feature a livelier apartment complete with a roaming mom NPC, door prompts, and a phone you can pop out anywhere for Discord-style chats. A 10-second tram ride bridges every home↔school jump, and the HUD clock doubles as a skip button when you need to fast-forward a segment.

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
- **Skip segment**: click the ⏭ icon next to the HUD clock to jump to the next scheduled beat (useful if you don’t want to wait out the real-time school timings).
- **Pause / Settings**: `Esc` toggles the overlay (adjust audio, text speed, and AI usage). Close the window or press `Ctrl+Esc` to quit.

## Gameplay Flow
Each day is split into the four planned segments plus an end-of-night rest phase:
1. **Morning – School**: arrive at 8:15, spend 15 real minutes chatting outside with AI and canned classmates, survive a five-minute hallway roam (complete with a vending machine that spends Nadiya’s €10 starting cash), then tackle an increasingly tough German quiz after a short teacher intro. Click the clock skip if you’re ready to jump straight to class.
2. **Afternoon – Home**: explore Nadiya's enlarged apartment, wander multiple rooms via enterable doors, and start the fry minigame where you dodge oil splashes, juggle timing windows, and feed momentum into her stats. Mom now physically roams the living room and can be approached for AI-driven conversation at any time.
3. **Evening – Phone**: roam the flat, crack open the in-game phone, and chat with three AI-driven friends on the Discord-style app. Relationship values, mood, and configuration knobs decide whether friends banter back or leave you on read.
4. **Night – Mom**: branching conversation that stitches scripted beats with local AI (or fallbacks) before sliding into the sleep summary screen.
5. **Sleep Transition**: fade overlay that tallies the day's events, applies balancing hooks from JSON, and resets the loop.

Player stats (mood, hunger, energy, German skill, money, and relationships) update in real time and influence modifiers on actions. Segment transitions now include tram cutscenes, respect the real-world clock windows configured in JSON, and the HUD shows a live clock with a clickable skip icon alongside automatic overlap detection that flashes a warning panel if UI elements accidentally collide.

## Configuration & Data

- `data/balance.json` – tunable numbers for stat deltas, timers, quiz rewards, and event thresholds.
- `data/ai/settings.json` – toggle local model integration and point at a running Ollama/LM Studio endpoint; defaults to deterministic stubs when disabled.
- `data/dialogue/bank.json` – lightweight branching dialogue nodes used to seed scripted beats before AI responses.

Edit these files to rebalance without touching code. The game hot-loads them on boot and caches in memory.

## Repository Structure
- `docs/design.md` – Full game design document.
- `src/game` – Playable prototype code (scenes, minigames, UI, state management, AI integration).
- `requirements.txt` – Python dependency list.

Future iterations can swap the stubbed AI calls with a local model server via the plumbing provided in `game.ai.local_client`.
