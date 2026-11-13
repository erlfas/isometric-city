# AGENTS.md — Lublin Anno Domini 1392

This guide provides high-signal navigation pointers and commands for coding agents working in this repository.

---

## 1. Quick Start & Environment

Setup: `scripts\setup_environment.ps1` (Windows) or `./scripts/setup_environment.sh` (Linux). Both install `node_modules`, enable the pre-commit hook, and print the tool paths below.

| Tool | Windows workstation (PowerShell 5.1) | Linux |
|---|---|---|
| `$BLENDER` | `C:\Program Files\Blender Foundation\Blender 5.3\blender.exe` (call with `&`) | `~/.local/bin/blender` (3.6 LTS; same geometry as 5.3) |
| `$PY` | Blender's bundled Python: `C:\Program Files\Blender Foundation\Blender 5.3\5.3\python\bin\python.exe` (no standalone Python) | `python3` |
| Node / npm | `C:\Program Files\nodejs` (prepend to `$env:Path` if a shell predates the install) | `node` |
| Browser for `shoot.mjs` | installed Edge (default) | set `PLAYWRIGHT_CHANNEL=chromium` |

Commands:
- **Typecheck**: `npm run check`. **Build**: `npm run build`.
- **Model check**: `$PY scripts/check_models.py` (roof winding, UVs, texture bindings ↔ manifest). Run it after every model build; the pre-commit hook and CI run it too.
- **Visual check**: with `npm run dev` running, `node scripts/shoot.mjs out.png "model=house_timber_log,0,14&pause&hour=12"` screenshots the n-th placed instance of a model. Hash syntax and `window.__lublin`: [`src/debug-hooks.ts`](src/debug-hooks.ts).
- **Runtime numbers** (draw calls, triangles, citizens per model, placed instances per building model, any `__lublin` expression): `node scripts/probe.mjs "<hash>" "__lublin.stats()"`. Before/after a performance change: `node scripts/perf.mjs` (fps + draw calls over three views; header says how to measure another commit).
- **Navigation** (walkable grid from the placed models, door anchors, routing): `node scripts/nav_check.mjs [out.png] [x0,z0,x1,z1]` draws the grid with doors/spots and routes 400 door pairs (fails if >2% unreachable). Live numbers: `__lublin.nav()`; watch someone: hash `hour=6.95&follow=walk` with `shoot.mjs --wait 8000`.
- **Audio mix** (you can't listen; this is the check): `node scripts/audio_levels.mjs [scene ...]` prints level per bus.
- **Doors in Blender**: `anchor_door(p, n, w, h=..., steps=(bm, stone_mat))` exports the door and, for a sill above 0.15 m, builds stone steps and their stair path.

---

## 2. Core Pipelines & Code Generators

| Task | Script / Entry Point | Output / Target | Command |
|---|---|---|---|
| **Building Models** | [`build_assets.py`](build_assets.py) | `public/models/*.glb` (31 models) | `$BLENDER --background --factory-startup --python build_assets.py [-- <glb names>]` (names = only those models; seconds instead of minutes) |
| **Character Models** | [`build_characters.py`](build_characters.py) + `characters/char_<trade>.py` (one kit per trade) | `public/models/char_*.glb` (14 kits; work loops in `src/engine/work-anims/`) | `$BLENDER --background --factory-startup --python build_characters.py [-- <glb names>]`. Kit format (parts, variants, palettes) and its runtime: header of [`src/engine/citizen-crowd.ts`](src/engine/citizen-crowd.ts). Inspect with `#pause&lineup=char_tanner,6[,work\|walk]`. |
| **Textures** | [`scripts/textures/build_textures.ps1`](scripts/textures/build_textures.ps1) | `public/textures/*.jpg` + `manifest.json` (19 families) | `powershell -ExecutionPolicy Bypass -File scripts\textures\build_textures.ps1` (needs git-ignored `texture_sources/`) |
| **Urban Parcellation** | [`generate_city_plan.py`](generate_city_plan.py) | `city_plan.json` (580 parcels, 0 overlaps) | `$PY generate_city_plan.py` |

---

## 3. Directory Navigation Map

- **3D Runtime Engine**:
  - [`src/engine/three-renderer.ts`](src/engine/three-renderer.ts): Three.js orthographic renderer, dynamic parcel dispatch, citizen archetype instancing, shadows. Buildings and props are drawn as one `BatchedMesh` per material ([`static-batches.ts`](src/engine/static-batches.ts)): place them with `put()`, not `scene.add(clone)`.
  - [`src/engine/simulation.ts`](src/engine/simulation.ts): 1,500-citizen schedule, routing (`nav-grid.ts`, doors from `building-anchors.ts`) and steering (time-to-collision avoidance, couples, gaits; tuning constants at the top), door queues. Walkers off view (camera ground rectangle from `renderer.groundView()` + 30 m) glide along their routes without avoidance. Live numbers: `__lublin.nav()` (`stuckNow`, `pairs`, `stepMs`, `gliding`, `doorsOpen`, `queueing`). Door leaves and night glow: `door-leaves.ts`; look at one with hash `door=house_baker,0` (held open).
  - [`src/engine/cutaway.ts`](src/engine/cutaway.ts): looking into buildings. The followed citizen's building (or one tapped / under the mouse while C is held) is hidden in the batches and redrawn as a copy whose roof and upper storeys dither out; back faces become inner walls and floor. Buildings between the camera and the followed citizen dither to ghosts. Hashes `cutaway=house_baker,0[,zoom,q,storey]` and `follow=inside`; tapping an open building again shows its upper storey.
  - [`src/engine/interiors.ts`](src/engine/interiors.ts): furnished interiors. Rooms, furniture, slots (sleep/seat/work/hearth) and ladders come from each building GLB's anchors (`anchor_room`, `furnish`, `fill_sleepers`, `anchor_ladder` in `build_assets.py`; prop sizes in its `PROPS` table, meshes in `interior_props.glb`). Routing inside = room-grid A* plus ladders; furniture is drawn only in the cutaway. Citizens inside take a slot by state (own bed at night), lie or sit (`Citizen.pose`), and light their windows at night while awake.
  - [`src/engine/life.ts`](src/engine/life.ts): citizen life (M7). Fixed blocks per role (guild hours, guard day/night watch, clergy, merchants, curfew at compline; households wake and sup together) plus needs (hunger, thirst, fatigue, social, piety) that pick free-time activities: meals at home or the fair, bread at a baker's window and water at the well (service lines in `simulation.ts`, carried home), church near the bells, tavern at a brewer's, the market, apprentices' errands, guards walking wall checkpoints. Acquaintances stop to chat (`onTalk`, lines in `chatter.ts`); lit hearths smoke (`chimney-smoke.ts`, flues = `anchor_chimney` or the ridge). Live numbers: `__lublin.sim.lifeStats()`; the inspector shows a citizen's day and needs.
  - [`src/engine/audio.ts`](src/engine/audio.ts): music (`music/`) and the synthesised positional soundscape (recipes in `sound-recipes.ts`). Which building a parcel is drawn as (shared by renderer and audio): `parcel-kind.ts`.
  - [`src/types.ts`](src/types.ts): TypeScript interfaces for `Parcel`, `Citizen`, `CityPlan`.
- **Reference Photos & Artwork**:
  - `reference_photos/<building_id>/`: Architectural 3-view sets (`front.jpg`, `side.jpg`, `back.jpg`).
  - `reference_photos/workers/`: 14 character 3-view turnaround model sheets (`*_turnaround.jpg`).
  - `concept_art/`: Panoramic district concept paintings and style guide.
- **Specifications & Post-Mortem Documentation**:
  - [`BUILDINGS_AND_WORKERS_CATALOG.md`](BUILDINGS_AND_WORKERS_CATALOG.md): Master building & worker specification.
  - [`KEY_FINDINGS.md`](KEY_FINDINGS.md): Critical post-mortem findings (Sections 1–19; §16 = textures & lighting, §17 = timber joints & workshop yards, §18 = characters, §19 = navigation, interiors & citizen life).
  - [`docs/material_board/`](docs/material_board/index.html), [`docs/texture_pilot/`](docs/texture_pilot/index.html): texture families, prompts, and the before/after sign-off.
  - [`docs/IMAGE_GENERATION_PROMPTS_AND_GALLERY.md`](docs/IMAGE_GENERATION_PROMPTS_AND_GALLERY.md): Exact prompts and visual gallery.
  - [`skills/`](skills/): Reusable procedural pipeline skills (`blender-procedural-asset-pipeline`, `blender-procedural-character-pipeline`, `procedural-model-creation-pipeline`).

---

## 4. Engineering Conventions

- **glTF / Three.js Coordinates**: Blender models must be exported with `export_yup=True` (+Y is up in Three.js).
- **Humanoid Character Proportions**: Standardized at $1.75\text{m}$ overall height with a $1:6.5$ RTS strategy game readability ratio. Kit triangle budgets are enforced by `check_models.py`.
- **Colours in Blender scripts are sRGB**: `create_mat` converts them to linear. Never write raw sRGB values into a Principled BSDF (everything renders washed out).
- **File Transfers**: Use Python `shutil.copyfile()` for atomic copying across workspace and artifact paths.
- **Textures bind by material name**: `src/engine/texture-library.ts` `BINDINGS` maps glTF material names to texture families. UVs are generated at export in metres (`add_world_uvs`); never scale a textured instance non-uniformly by large factors (it stretches the texture) - tile modules instead.
- **Lighting**: tune via `LIGHT_PRESETS` in `three-renderer.ts`; the sun is locked to the camera view. Keep shaded walls at 45–55% of lit (style guide §3).
