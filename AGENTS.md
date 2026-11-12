# AGENTS.md — Lublin Anno Domini 1392

This guide provides high-signal navigation pointers and commands for coding agents working in this repository.

---

## 1. Quick Start & Environment

- **Initial Setup**: Run `./scripts/setup_environment.sh` (installs `node_modules` and verifies Blender 3.6 LTS).
- **Typecheck**: `npm run check` (runs `tsc --noEmit` without bundling).
- **Build**: `npm run build` (typechecks and bundles Vite client).
- **Blender Binary Path**: `/home/antigravity/blender/blender` (or `~/.local/bin/blender`).
  - *Never* run unbounded `find /` across the filesystem.
- **Windows workstation**: Blender 5.3 at `C:\Program Files\Blender Foundation\Blender 5.3\blender.exe` (verified to produce identical geometry/materials to the 3.6 builds).
  - Build: `& "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" --background --factory-startup --python build_assets.py` — append `-- house_half_timber town_hall` (GLB names) to build only those models.
- **Visual check**: with `npm run dev` running, `node scripts/shoot.mjs out.png "model=house_timber_log,0,14&pause&hour=12"` screenshots the n-th placed instance of a model. Hash syntax and `window.__lublin`: [`src/debug-hooks.ts`](src/debug-hooks.ts).
  - No standalone Python; use Blender's bundled interpreter: `C:\Program Files\Blender Foundation\Blender 5.3\5.3\python\bin\python.exe`.

---

## 2. Core Pipelines & Code Generators

| Task | Script / Entry Point | Output / Target | Command |
|---|---|---|---|
| **Building Models** | [`build_assets.py`](build_assets.py) | `public/models/*.glb` (31 models) | `/home/antigravity/blender/blender --background --python build_assets.py` |
| **Character Models** | [`build_characters.py`](build_characters.py) | `public/models/characters/*.glb` (14 models) | `/home/antigravity/blender/blender --background --python build_characters.py` |
| **Textures** | [`scripts/textures/build_textures.ps1`](scripts/textures/build_textures.ps1) | `public/textures/*.jpg` + `manifest.json` (19 families) | `powershell -ExecutionPolicy Bypass -File scripts\textures\build_textures.ps1` (needs git-ignored `texture_sources/`) |
| **Urban Parcellation** | [`generate_city_plan.py`](generate_city_plan.py) | `city_plan.json` (580 parcels, 0 overlaps) | `python3 generate_city_plan.py` |

---

## 3. Directory Navigation Map

- **3D Runtime Engine**:
  - [`src/engine/three-renderer.ts`](src/engine/three-renderer.ts): Three.js orthographic renderer, dynamic parcel dispatch, citizen archetype instancing, shadows.
  - [`src/engine/simulation.ts`](src/engine/simulation.ts): 1,500-citizen clockwork schedule, spatial hash grid.
  - [`src/types.ts`](src/types.ts): TypeScript interfaces for `Parcel`, `Citizen`, `CityPlan`.
- **Reference Photos & Artwork**:
  - `reference_photos/<building_id>/`: Architectural 3-view sets (`front.jpg`, `side.jpg`, `back.jpg`).
  - `reference_photos/workers/`: 14 character 3-view turnaround model sheets (`*_turnaround.jpg`).
  - `concept_art/`: Panoramic district concept paintings and style guide.
- **Specifications & Post-Mortem Documentation**:
  - [`BUILDINGS_AND_WORKERS_CATALOG.md`](BUILDINGS_AND_WORKERS_CATALOG.md): Master building & worker specification.
  - [`KEY_FINDINGS.md`](KEY_FINDINGS.md): Critical post-mortem findings (Sections 1–16; §16 = textures & lighting).
  - [`docs/material_board/`](docs/material_board/index.html), [`docs/texture_pilot/`](docs/texture_pilot/index.html): texture families, prompts, and the before/after sign-off.
  - [`docs/IMAGE_GENERATION_PROMPTS_AND_GALLERY.md`](docs/IMAGE_GENERATION_PROMPTS_AND_GALLERY.md): Exact prompts and visual gallery.
  - [`skills/`](skills/): Reusable procedural pipeline skills (`blender-procedural-asset-pipeline`, `blender-procedural-character-pipeline`, `procedural-model-creation-pipeline`).

---

## 4. Engineering Conventions

- **glTF / Three.js Coordinates**: Blender models must be exported with `export_yup=True` (+Y is up in Three.js).
- **Humanoid Character Proportions**: Standardized at $1.75\text{m}$ overall height with a $1:6.5$ RTS strategy game readability ratio. Triangle budget: $140 - 220$ polygons per character.
- **File Transfers**: Use Python `shutil.copyfile()` for atomic copying across workspace and artifact paths.
- **Textures bind by material name**: `src/engine/texture-library.ts` `BINDINGS` maps glTF material names to texture families. UVs are generated at export in metres (`add_world_uvs`); never scale a textured instance non-uniformly by large factors (it stretches the texture) - tile modules instead.
- **Lighting**: tune via `LIGHT_PRESETS` in `three-renderer.ts`; the sun is locked to the camera view. Keep shaded walls at 45–55% of lit (style guide §3).
