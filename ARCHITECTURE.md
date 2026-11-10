# Lublin Anno Domini 1392: Medieval Isometric City Simulation
## Architectural Specification & Technical Implementation Report

Designed and engineered as a modular, high-performance simulation of medieval Lublin during its historic **Royal Fair of 1392**, granted under the charter of **King Władysław II Jagiełło**.

---

## 1. System Overview & Technology Stack

The system is constructed around a strict **three-tier decoupled data architecture**:

```mermaid
flowchart TD
    A["Offline Plan Generator<br/>(generate_city_plan.py)"] -->|Produces| B["Intermediate Representation IR<br/>(public/city_plan.json)"]
    B -->|Ingested by| C["Headless Blender Pipeline<br/>(build_assets.py)"]
    B -->|Ingested by| D["Custom WebGL Runtime Engine<br/>(Vite + TypeScript + WebGL)"]
    C -->|Compiles & Exports| E["Low-Poly GLTF / GLB Assets<br/>(with baked vertex colors & aging)"]
    D -->|Renders 60 FPS| F["Living Autonomous Simulation<br/>(580 Parcels & 1,500 Citizens)"]
```

- **Runtime & Bundler**: Vite + TypeScript (vanilla, zero heavy game engine dependencies; total client JS bundle is only **42 kB**).
- **Modeling & Asset Pipeline**: Headless Blender Python (`bpy` / `bmesh`) CLI scripts (`build_assets.py`) compiling parametric recipes into GLTF/GLB models with clean material slots.
- **Data Architecture**: Decoupled JSON Intermediate Representation (`city_plan.json`), consumed by both Blender asset builders and the web runtime.

---

## 2. Urban Morphology: Lublin 1392 Specification

The urban morphology accurately reconstructs the medieval topography and layout of Lublin around 1392:

### Topography & Boundaries
- **Geological Promontory**: ~8.84 hectares enclosed on an elevated loess spur protected by the Czechówka ravine to the north and Bystrzyca valley to the south.
- **Defensive Perimeter**: Brick and limestone curtain wall with **14 defensive towers** (Towers of the Goldsmiths, Butchers, Bakers, Weavers, etc.) and two primary fortified gateways:
  1. **Brama Krakowska (Kraków Gate)**: Southwestern gateway with octagonal brick tower, arched portal, and outer barbican forework over the moat.
  2. **Brama Grodzka (Grodzka Gate)**: Northeastern gateway leading to the bridge over the Czechówka ravine toward Castle Hill.
- **Castle Hill (Wzgórze Zamkowe)**:
  - Separate walled bailey across the wooden bridge.
  - **Donjon Keep**: Romanesque cylindrical limestone tower (13th c., 30m high, 3m thick walls) serving as the ultimate royal refuge.
  - **Kaplica Trójcy Świętej (Royal Holy Trinity Chapel)**: Two-tier Gothic brick church with stone buttresses and steep tiled roof, famed for its royal Ruthenian-Byzantine frescoes.
  - **Dwór Królewski (Royal Palace Hall)**: Gothic residential hall built by Casimir the Great and expanded under Jagiełło.
- **Civic Core (Rynek)**:
  - Central trapezoidal Market Square paved with cobblestones.
  - **Ratusz Miejski (Old Town Hall)**: Gothic brick council house with clock tower, ground floor arcades (*podcienia*), crenellated attic, and 4 corner turrets.
  - **Szmatruz (Royal Cloth & Bread Hall)**: 28m x 14m hall featuring 22 brick pillars, a covered central aisle, and 16 vendor stalls for Flemish broadcloth, Lublin linen, spices, and amber.
  - **Pręgierz (Pillory) & Municipal Stone Well**.
- **Kraków Suburb (Przedmieście Krakowskie)**:
  - Unfortified exterior quarter along the Kraków highway hosting timber yards, cooperages, sawpits, and the **Player's Master Workshop** (`p_001_player_workshop`).

### Parcellation & Street Frontages
- **580 Parcels**: Rigorously generated across 7 historical quarters (`market_square`, `bramowa_quarter`, `grodzka_quarter`, `dominican_quarter`, `north_wall`, `castle_hill`, `krakow_suburb`).
- **No Identical Consecutive Building Types**: The parcellation algorithm enforces that no adjacent parcel along a street or block shares the same architectural archetype.
- **Setbacks & Irregular Alleys**: Narrow lanes (Złota, Rybna, Archidiakońska, Kowalska) with irregular setbacks, active building sites with timber scaffolding (6% of plots), and yard clutter (firewood ricks, oak barrels, leaning ladders, wicker hoops, carts).

---

## 3. Parametric Structural Aging & Blender Pipeline

Implemented in [`build_assets.py`](file:///home/antigravity/erlfas/isometric-city/build_assets.py) using Blender's `bpy` and `bmesh` modules (and mirrored natively in the runtime geometry generator):

1. **Parabolic Roof Ridge Sagging**:
   Roof ridge vertices ($z > 0.65 \cdot h$) are displaced downward according to a parabolic function:
   $$\Delta z = -4 \cdot \text{ridgeSag} \cdot u \cdot (1 - u)$$
   where $u \in [0, 1]$ represents the normalized position along the roof length.
2. **Wall Lean & Shear**:
   Upper floor loop vertices undergo lateral shearing:
   $$\Delta x = \tan(\theta_{\text{lean}}) \cdot (z - z_{\text{foundation}})$$
3. **Vertex Color Baking (`Col` layer)**:
   - Foundation loess dirt and moss darkening on lower wall loops ($z < 1.8\text{m}$).
   - Wood graying desaturation on exposed timber posts and shingles.
   - Baked ambient occlusion under jettied overhangs and eaves.
4. **Clean Material Slots & Export**:
   - `Mat_Limestone`, `Mat_GothicBrick`, `Mat_HalfTimberWood`, `Mat_HalfTimberPlaster`, `Mat_RoofTile`, `Mat_RoofShingle`, `Mat_RoofThatch`, `Mat_WroughtIron`, `Mat_HeraldicGold`.
   - Batch exports to optimized `.glb` / `.gltf` assets.

---

## 4. Living Autonomous Simulation Engine

Implemented in [`src/engine/simulation.ts`](file:///home/antigravity/erlfas/isometric-city/src/engine/simulation.ts):

- **1,500 Persistent Citizens across ~400 Households**:
  - Unique ID, authentic 14th-century names (Polish, Ruthenian, German burgher naming traditions).
  - 18 Craft Guilds: Blacksmith, Baker, Shoemaker, Tailor, Furrier, Potter, Cooper, Weaver, Brewer, Carpenter, Roper, Goldsmith, Tanner, Mason, Wheelwright, Butcher, Armorer, Candlemaker.
  - Wealth Classes: Patrician, Burgher, Artisan, Plebeian, Foreign Fair Visitor.
  - Home parcel, bed assignment, workplace / stall ID, wallet (Kraków grosze), and carried commodities.
- **Clockwork Routines Driven by Civic Church Bells**:
  The simulation advances through the 8 canonical bell hours of medieval Lublin:
  * **05:00 Matins (Jutrznia / Dawn)**: Kindling peat hearths, opening wooden window shutters, morning prayers.
  * **07:00 Prime (Pryma / Guild Opening)**: Guild workshop doors unlock; smoke rises from bakeries and forges.
  * **09:00 Terce (Tercja / Royal Fair Opening)**: Arrival of Hungarian wine caravans at Kraków Gate; stalls open at the Market Square and Szmatruz.
  * **12:00 Sext (Seksta / Midday Bell)**: Senior Weavers' Alderman and Royal Bailiff conduct cloth inspection; tavern dinners.
  * **15:00 Nones (Nona / High Fair)**: Peak volume of trading; livestock, amber, and silk transactions; royal herald proclamations.
  * **18:00 Vespers (Nieszpory / Dusk)**: Stall shutters close; taverns fill with dice games and music; gate guards check night travelers.
  * **21:00 Compline (Kompleta / Curfew)**: Nine collegiate church bell strokes; Kraków and Grodzka Gates lowered with iron portcullises; watchmen begin lantern patrols.
  * **00:00 Deep Night (Głęboka Noc)**: Silent streets under moonlight; watchmen patrols checking merchant locks.

---

## 5. WebGL Isometric Engine & Performance Architecture

Implemented in [`src/engine/webgl-renderer.ts`](file:///home/antigravity/erlfas/isometric-city/src/engine/webgl-renderer.ts), [`src/engine/camera.ts`](file:///home/antigravity/erlfas/isometric-city/src/engine/camera.ts), and [`src/engine/spatial-hash.ts`](file:///home/antigravity/erlfas/isometric-city/src/engine/spatial-hash.ts):

- **Dimetric 2:1 Isometric Projection**:
  - Fixed isometric angle ($30^\circ$ pitch) matching classic dimetric games ($2:1$ pixel ratio).
  - 4-Quadrant View Rotation: Smooth $90^\circ$ animated rotations between SW, NW, NE, and SE viewpoints.
- **Single-Draw-Call Batched Geometry**:
  - The entire 580-parcel city, curtain walls, castle, and landmarks are compiled into a unified GPU vertex buffer with vertex colors and normals, rendering the entire city in a single draw call.
- **Zero-Allocation Scratch Buffers**:
  - All per-frame matrix operations, vector math, and spatial queries reuse pre-allocated typed arrays, eliminating garbage collection pauses.
- **Spatial Hash Grid ($O(1)$ Culling & Picking)**:
  - 24m $\times$ 24m spatial hash grid partitions all parcels and 1,500 dynamic citizens.
  - Viewport frustum culling only queries visible cells.
  - Immediate raycast picking for inspectable citizens and buildings.
- **Procedural Church Bell Synthesizer (Web Audio API)**:
  - Physical acoustic modeling using additive synthesis across the 7 inharmonic bell partials (Hum, Prime, Tierce, Quint, Nominal, Supernominal, Strike clang) with exponential damping.
