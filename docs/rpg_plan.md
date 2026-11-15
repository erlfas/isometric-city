# Plan: The Scribe of Lublin (main character, dialogue, items, mystery)

This turns the city simulation into a story game. The player is **Jan of Sandomierz**, a scribe newly arrived in Lublin in 1392. He solves the death of his predecessor by walking the living town, talking to its people and collecting evidence.

- Story content: [`docs/story/case_drowned_scribe.md`](story/case_drowned_scribe.md) (the case document; accepted 2026-11-15).
- Status: **plan, not started** (2026-11-15).

---

## 1. Decisions (from the design grilling, 2026-11-14/15)

**Jan.** Jan of Sandomierz, about 25, trained at Prague. He has a dry, observant voice in his examine lines and no voice acting.
- He lodges in `p_001_player_workshop`; its residents and workers are moved out.
- He gets a new kit, `char_scribe`.
- He has no hunger or thirst meters; sleeping skips to the next dawn and autosaves.

**Controls.**
- Moving: click-to-move on the nav grid, with WASD as secondary.
- Left-click does the obvious action: walk, talk, pick up, open.
- Right-click examines.
- Touch: tap acts, long-press examines.

**Camera.** It stays on Jan. Panning is temporary and snaps back. The free camera, following, landmark jumps, time jumps and the needs/schedule inspector are gone from the player's screen and stay only as debug hashes. There is no sandbox mode.

**Citizens.** Tapping or clicking a citizen shows a card with their name and trade and a "Talk" button. It never shows their needs or schedule.

**Time.** One fixed speed (1 real s = 1 sim min). The clock pauses while a conversation, the satchel or the journal is open.

**Dialogue.** Hand-written in **Ink** and run by `inkjs`.
- The story has 8 named characters. Ambient citizens get a few generic lines by trade and time of day, plus rumour lines.
- When a conversation starts, Jan and the other person turn to face each other. The camera eases in over about 0.5 s to zoom ≈10, framing both full figures above the panel, and the town around is slightly dimmed. When it ends, the camera eases back.
- The panel at the bottom shows a portrait rendered automatically from the speaker's model (Jan and the speaker alternate), the speaker's name and trade, the line, and numbered choices (mouse or keys 1–9).
- "Show him something…" is a standing option in every story conversation.
- Body language: one shared talking loop, plus one-off gestures triggered from Ink tags (shrug, cross oneself, point, turn away, nod).

**Items.**
- About 18 hand-placed items. Hovering one outlines it and shows its name.
- Left-click: Jan walks over, bends or reaches (one ground animation, one table animation), and the icon flies to the satchel button. Jan says a one-line remark in a speech bubble.
- **Satchel.** A leather scribe's satchel, opened with the button bottom-left, I or Tab. It has unlimited slots. The selected item turns slowly in 3D with Jan's description beside it.
- **Using an item.** Choose it, and the cursor becomes the item. Hovering a target names the action ("Show florin to Sędziwój"), clicking does it, and right-click or Esc cancels. The target decides whether the item is used, given or shown.
- **Combining.** Drag one item onto another in the satchel. Combinations that need the world (drying the note) work by using the item on the fire or a candle.
- Puzzles are grounded in what was possible in 1392 and always hinted. There are no dead ends.
- Item props are built in `build_assets.py`, and icons are rendered from the same models.

**Journal.** Clues are written in automatically, with their source. The accusation is made before the council: who, how and why, plus evidence. There are three endings: justice / the councillor's word / the wrong man.

**Saving.** One slot in `localStorage`: story state, the clock, the day, Jan's position, the satchel and the journal. It autosaves on sleep and at story milestones. The title screen has Continue / New game. On load, the clock is set to the saved time (`setTime` re-seats everyone).

**Story controls.** The story can override a story character's routine and schedule timed events. The case runs over 3 days (day 2 funeral, day 3 fair and council), with no deadline after that.

**Language.** English for dialogue and UI, with authentic personal and place names.

### Defaults taken in this plan (change if wrong)

- **Keys:**
  - WASD moves Jan.
  - Arrow keys and drag pan the camera temporarily; it snaps back after 3 s or when Jan moves.
  - Q/E rotate.
  - Space pauses (no other menu).
  - I/Tab open the satchel; J opens the journal.
  - Esc cancels or closes; holding C peeks into buildings.
  - 1–9 pick dialogue choices.
  - The stale "[E]" hover hint is dropped.
- **Journal layout:** a two-page book.
  - Left page: *People*, one entry per character met, with what they claimed.
  - Right page: *Findings*, clue lines grouped by question (How did he die? Who did he meet? What was taken?).
  - A third tab, *The Case*, shows the accusation sheet, available at a council session.
- **Dialogue audio:** no voices or blips. Town sound ducks by 6 dB while the panel is open, and a page-turn sound plays on each line. The music bus is unchanged.
- **Title screen:** a painted concept-art panorama behind three buttons (Continue, New game, Credits).

---

## 2. Architecture

New code goes in `src/game/` and leaves the engine generic. The engine gains a few small public hooks.

| Module | Job |
|---|---|
| `src/game/player.ts` | Jan as a sim citizen with `controlled: true`. Click-to-move builds a `Dest` and calls a new public `sim.driveTo(id, dest)`. WASD sets the desired velocity in the sim's steering, with the nav grid as walls. `life.ts` skips controlled citizens. |
| `src/game/interact.ts` | Hover picking over citizens, items and inspectable objects (`Hotspot` list), cursor modes (normal / holding an item), action labels, walk-then-act queue. |
| `src/game/story.ts` | Owns the `inkjs` `Story`: variables shared with the game (`has_item`, `clue`, `day`, `hour`, flags), external functions (`give_item`, `take_item`, `add_clue`, `set_flag`, `override_routine`, `gesture`), and knot entry points per character. |
| `src/game/events.ts` | Timed and flag-triggered events from the case document §6 (E1–E7), run on the sim clock. |
| `src/game/inventory.ts` | Satchel contents, combine recipes, the item → Hotspot placement table. |
| `src/game/journal.ts` | Clues (`C1..C13`), people met, the proof-set check (case §5). |
| `src/game/save.ts` | Saves and loads one slot; the format has a version number. |
| `src/game/ui/*.ts` | DOM panels: dialogue, satchel (with a small Three.js viewport for the turning item), journal, citizen card, title screen, hint toasts. Plain DOM, like `inspector.ts`. |
| `src/game/portraits.ts` | Renders head-and-shoulders portraits and item icons offscreen once at load, cached as data URLs. |
| `story/*.ink` | One file per character plus `main.ink` (opening, endings, the council). Compiled to `public/story/main.json` by `scripts/build_story.mjs` (`inkjs/compiler`), which runs in `npm run dev` and `npm run build`. |

**Engine changes:**
- `simulation.ts`: `driveTo`, a `controlled` flag, desired velocity for WASD, routine overrides (`overrideBlock(id, block, until)`), gatherings (funeral, council).
- `three-renderer.ts`: replace `followingCitizen` with `focusCitizen` (always Jan), conversation framing (zoom/ease/dim), temporary pan.
- `cutaway.ts`: keys on Jan instead of the followed citizen.
- `citizen-crowd.ts`: per-citizen look override (the hero and the story cast), facing control.
- `life.ts`: skips controlled citizens and honours overrides.
- `main.ts`: removes follow, the inspector, landmark jumps and time jumps from the player's screen; `debug-hooks.ts` keeps them behind the hash.
- `audio.ts`: the dialogue duck.

---

## 3. Milestones

Each milestone ends playable and checked with `shoot.mjs`/`probe.mjs`, `npm run check` and `check_models.py`, then committed. M1–M3 plus the gate scene (E1) form the **vertical slice**: stop there and judge the feel of the game with the user before M4.

### M1 — Jan in town
- Jan exists as a controlled citizen (a scribe-looking variant of the merchant kit until M7), spawning at `gate_krakow` at matins on day 1.
- Click-to-move and WASD; the camera stays on Jan; temporary pan.
- The citizen card replaces following and the inspector. The developer controls move behind debug hashes, and peeking keys on Jan.
- `p_001_player_workshop` is emptied of its residents and workers (in the plan generator), and Jan's bed is his slot.
- Gates shut at compline, with a wicket that only dialogue opens. Jan can't leave the walls after curfew without it.
- **Checks:**
  - `nav_check` passes.
  - Click 20 random reachable points: Jan arrives at every one (scripted in `probe.mjs`).
  - Draw calls and fps within 3% of `faba1b4`.

### M2 — Dialogue
- `inkjs` plus the build script, the dialogue panel, the conversation camera, facing, the talk loop and gestures, auto-rendered portraits, the clock pause and the audio duck.
- Ambient-citizen generic replies.
- Content: E1, the gate guard's questioning, written in Ink as the test case.
- **Checks:** a screenshot of the panel mid-conversation; the story lint (§4) runs.

### M3 — Items
- Hotspots (items plus inspectable fixed objects), hover outline and label, pick-up animations and the fly-to-satchel effect.
- The satchel panel with a turning 3D view, cursor-as-item, use/give/show by target, combining.
- Item props I1–I18 built in `build_assets.py` (`items.glb`), with icons rendered from them.
- Content: the tutorial items I1, I2, I5, I13; the register examine (C1).
- **Vertical slice review with the user.**

### M4 — Journal, sleep, saving
- The journal book (People / Findings / The Case), clue logging with source, the proof-set check.
- Sleeping in Jan's bed skips to matins (a fade, `setTime`, and everyone re-seats).
- The save slot, autosave and the title screen.
- **Check:** save mid-day 1, reload, and the state is identical (scripted diff of the story and save state).

### M5 — Story controls
- Story cast cast from the plan (case §4) with renamed, fixed looks; routine overrides; flag-triggered events E3–E5; gatherings E2 (funeral) and E7 (council).
- The body as a prop and slot in the Fara; the priest as a minor speaking role.
- **Check:** each event fires at its time or flag in a scripted run (`probe.mjs` with the hash `story=flag1,flag2&hour=…`).

### M6 — The story
- All case content in Ink: the 8 characters, every clue route, the item reactions, the accusation and the 3 endings.
- Hand-placed items at their spots.
- **Checks:** the story lint passes; the scripted play-throughs (§4) reach each ending.

### M7 — Polish
- The `char_scribe` kit (dark robe, ink case, tablet at the belt, a distinctive hat), with a writing work loop for the journal moment.
- Tuning pass on walking speed, framing and hint frequency.
- KEY_FINDINGS section; AGENTS.md pointers; the catalog.

---

## 4. Automated checks

**Story lint** (`scripts/story_lint.mjs`, in the pre-commit hook and CI). It parses the compiled Ink and the case tables (§5 and §8 kept as JSON in `story/case.json`, the single source the lint and `journal.ts` both read), and checks that:
- every knot can be reached;
- every clue has at least 2 routes;
- every item the solution needs can be obtained and cannot be lost;
- each story character has a reaction to every key item (I2, I3, I7, I8, I10, I11, I12);
- every ending can be reached.

**Scripted play-throughs** (`scripts/playthrough.mjs`, Playwright like `shoot.mjs`). They drive Jan through `__lublin.game` hooks (`walkTo`, `talk`, `choose`, `use`, `sleep`):
1. The shortest *justice* route.
2. One route per other ending.

Each fails if Jan gets stuck (no progress in 120 s of sim time) or a step is refused. They run per milestone from M5 on, not in pre-commit (too slow).

---

## 5. Risks

- **Routing for one controlled citizen.** The waypoint graph is tuned for crowds; for click-to-move, short hops may need direct grid A*. Measure in M1.
- **Zoom ≈10 framing.** Kits are built for strategy-game distance. If full figures look crude at 10, frame at 14 and lean on the portraits.
- **Off-view gliding.** Story characters the player is watching must not glide; they are always in view of Jan's camera, but check E4 (the friary) from across the street.
- **Plan data.** It is muddled in places (carpenters work in a brewer's malthouse, `p_071`), so casting in M5 will repair the plan data for the chosen parcels instead of trusting it.
- **Saving is coarse.** Citizens re-seat on load, so a story character mid-walk jumps to their scheduled place. That's acceptable because saves happen at sleep and milestones.
