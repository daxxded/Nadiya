# Nadiya Simulator

This repository now contains a playable vertical slice prototype for **Nadiya Simulator**, a compact isometric life-sim that blends chaotic humor, grounded emotional beats, and locally hosted AI-driven dialogue. The original narrative and systems design remains available in [`docs/design.md`](docs/design.md).

The latest update turns the afternoon and evening sequences into a freely explorable apartment: wander between rooms via doors, trigger the fry shift from the kitchen, and open a phone UI complete with faux apps and a Discord-like chat for three friends.

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

### Controls
- **Movement (school & home)**: `WASD` or arrow keys for free gliding.
- **Interact / confirm**: `Space` or `Enter` to use doors, minigame stations, or UI selections.
- **Phone (exploration segments)**: press `P` to pull the phone out anywhere at home; use arrows or `Q/E` to switch friends inside Discord, type naturally, `Enter` to send, and `Esc`/`Backspace` to back out of apps.
- **Pause / Settings**: `Esc` toggles the overlay (adjust audio, text speed, and AI usage). Close the window or press `Ctrl+Esc` to quit.

## Gameplay Flow
Each day is split into the four planned segments plus an end-of-night rest phase:
1. **Morning – School**: dodge annoying classmates across an isometric hallway, then sit a German quiz whose rewards scale with performance.
2. **Afternoon – Home**: explore Nadiya's apartment, slip into the kitchen via door prompts, and start the fry minigame where you dodge oil splashes, juggle timing windows, and feed momentum into her stats.
3. **Evening – Phone**: roam the flat, crack open the in-game phone, and chat with three AI-driven friends on the Discord-style app. Relationship values, mood, and configuration knobs decide whether friends banter back or leave you on read.
4. **Night – Mom**: branching conversation that stitches scripted beats with local AI (or fallbacks) before sliding into the sleep summary screen.
5. **Sleep Transition**: fade overlay that tallies the day's events, applies balancing hooks from JSON, and resets the loop.

Player stats (mood, hunger, energy, German skill, and relationships) update in real time and influence modifiers on actions. Segment transitions now display summaries with fade effects, can skip ahead if the player is exhausted or spirals mood too low, and the HUD shows a live clock plus segment progress.

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
