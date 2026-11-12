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
- **Runtime numbers** (draw calls, triangles, citizens per model, placed instances per building model, any `__lublin` expression): `node scripts/probe.mjs "<hash>" "__lublin.stats()"`.
- **Audio mix** (you can't listen; this is the check): `node scripts/audio_levels.mjs [scene ...]` prints level per bus.

---

## 2. Core Pipelines & Code Generators

| Task | Script / Entry Point | Output / Target | Command |
|---|---|---|---|
| **Building Models** | [`build_assets.py`](build_assets.py) | `public/models/*.glb` (31 models) | `$BLENDER --background --factory-startup --python build_assets.py [-- <glb names>]` (names = only those models; seconds instead of minutes) |
| **Character Models** | [`build_characters.py`](build_characters.py) | `public/models/char_*.glb` (14 models; tanner and blacksmith are kits) | `$BLENDER --background --factory-startup --python build_characters.py [-- <glb names>]`. Kit format (parts, variants, palettes) and its runtime: header of [`src/engine/citizen-crowd.ts`](src/engine/citizen-crowd.ts). Inspect with `#pause&lineup=char_tanner,6[,work\|walk]`. |
| **Textures** | [`scripts/textures/build_textures.ps1`](scripts/textures/build_textures.ps1) | `public/textures/*.jpg` + `manifest.json` (19 families) | `powershell -ExecutionPolicy Bypass -File scripts\textures\build_textures.ps1` (needs git-ignored `texture_sources/`) |
| **Urban Parcellation** | [`generate_city_plan.py`](generate_city_plan.py) | `city_plan.json` (580 parcels, 0 overlaps) | `$PY generate_city_plan.py` |

---

## 3. Directory Navigation Map

- **3D Runtime Engine**:
  - [`src/engine/three-renderer.ts`](src/engine/three-renderer.ts): Three.js orthographic renderer, dynamic parcel dispatch, citizen archetype instancing, shadows.
  - [`src/engine/simulation.ts`](src/engine/simulation.ts): 1,500-citizen clockwork schedule, spatial hash grid.
  - [`src/engine/audio.ts`](src/engine/audio.ts): music (`music/`) and the synthesised positional soundscape (recipes in `sound-recipes.ts`). Which building a parcel is drawn as (shared by renderer and audio): `parcel-kind.ts`.
  - [`src/types.ts`](src/types.ts): TypeScript interfaces for `Parcel`, `Citizen`, `CityPlan`.
- **Reference Photos & Artwork**:
  - `reference_photos/<building_id>/`: Architectural 3-view sets (`front.jpg`, `side.jpg`, `back.jpg`).
  - `reference_photos/workers/`: 14 character 3-view turnaround model sheets (`*_turnaround.jpg`).
  - `concept_art/`: Panoramic district concept paintings and style guide.
- **Specifications & Post-Mortem Documentation**:
  - [`BUILDINGS_AND_WORKERS_CATALOG.md`](BUILDINGS_AND_WORKERS_CATALOG.md): Master building & worker specification.
  - [`KEY_FINDINGS.md`](KEY_FINDINGS.md): Critical post-mortem findings (Sections 1–18; §16 = textures & lighting, §17 = timber joints & workshop yards, §18 = characters).
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
