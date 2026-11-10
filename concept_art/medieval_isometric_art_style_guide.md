# Art Direction & Visual Style Guide
**Project Aesthetic:** Late-1990s / Early-2000s Pre-Rendered Isometric Medieval City-Builder  
**Visual Touchstones:** *Stronghold (2001)*, *Knights and Merchants (1998)*, *Patrician III (2003)*, *The Guild / Europa 1400 (2002)*

---

## 1. Vision Statement
The visual style captures the grounded, historical charm of turn-of-the-millennium PC strategy and economic simulation games. Rather than using stylized cartoon proportions or modern hyper-realistic PBR (Physically Based Rendering) lighting, the art relies on **crisp, tactile textures, high-contrast directional shadows, and an earthy, weathered color palette**. Every asset should read clearly from a bird's-eye view while feeling lived-in and historically authentic to 14th–15th century Central and Eastern Europe.

---

## 2. Camera & Projection Specifications
Consistency in camera setup is critical when rendering 3D models into 2D sprites (or setting up a 3D orthographic viewport).

* **Projection Type:** Orthographic (zero perspective distortion; parallel lines never converge).
* **Camera Pitch (Elevation Angle):** $30^\circ$ (classic 2:1 dimetric pixel art ratio) to $35.264^\circ$ (true isometric). Standardizing at **$30^\circ$** is recommended for clean tile alignment.
* **Camera Yaw (Rotation):** Standard $45^\circ$ base angle, with buildings rendered at $15^\circ$, $30^\circ$, or $45^\circ$ increments to allow for organic, non-grid-locked town layouts.
* **Scale & Proportions:**
  * **Human Units:** Slightly exaggerated head and shoulder proportions ($1:6.5$ head-to-body ratio) with saturated clothing accents so villagers remain readable at small pixel sizes.
  * **Buildings vs. Units:** Doors should be roughly $1.2\times$ to $1.5\times$ the height of a human sprite—realistic enough to feel grounded, avoiding the "miniature toy house" look of some RTS games.

---

## 3. Lighting & Rendering Pipeline
To achieve the classic pre-rendered look in modern 3D software (Blender, 3ds Max, Maya) or a real-time engine (Unity, Godot, Unreal):

* **Primary Key Light (Sun):**
  * **Angle:** Top-left or Top-right at a $45^\circ$ downward pitch. All sprites must share the exact same light angle.
  * **Color:** Warm, slightly desaturated sunlight (`#FFF8E7`).
  * **Shadows:** Crisp, uniform drop shadows with minimal penumbra (softness). In 2D sprite workflows, render shadows onto a separate alpha pass at $50\%$–$60\%$ opacity (`#1A1815`).
* **Ambient / Fill Light:**
  * Keep ambient occlusion subtle. Avoid modern "soft GI" (Global Illumination) that washes out texture details.
  * Unlit/shadowed sides of buildings should retain clear texture visibility at roughly $45\%$–$55\%$ brightness of the lit side.
* **Anti-Aliasing & Filtering:**
  * Render sprites with sharp sampling (e.g., Mitchell-Netravali or Catmull-Rom filter) so roof tiles, timber planks, and brick mortar lines remain crisp rather than blurry.
  * Avoid post-processing bloom, depth-of-field, chromatic aberration, or heavy vignette effects.

---

## 4. Color Palette & Materiality
The palette is divided into **Muted Vernacular/Terrain** (80% of the screen) and **High-Status Civic/Religious Accents** (20% of the screen). This contrast allows the player to immediately read town hierarchy at a glance.

### Terrain & Nature (Earthy & Desaturated)
* **Grasslands:** Olive and moss greens (`#556236`, `#687342`, `#414B29`) — strictly avoid neon or oversaturated emerald greens.
* **Dirt Roads & Plazas:** Worn, dusty taupe and dry mud browns (`#7A6A53`, `#8C7B65`, `#5E503F`).
* **Foliage:** Dense, slightly clumped leaf canopies with dark under-shading (`#3B4D24` to `#6E853E`).

### Peasant & Vernacular Architecture (Wood & Thatch)
* **Log Walls:** Dark, weathered pine and oak (`#4A3B2C`, `#5C4938`).
* **Thatch & Shingle Roofs:** Sun-bleached straw ochre, weathered gray-brown shakes, and mossy timber (`#9E8656`, `#73685B`, `#615445`).

### Civic, Military & Religious Architecture (Brick Gothic)
* **Red Brick:** Rich terracotta and fired clay (`#8C3B2B`, `#A34836`, `#6E2B1E`).
* **Roof Tiles:** Warm clay orange-red (`#B55338`, `#99422B`).
* **Lime Plaster Tracery:** Recessed Gothic arches and clock faces in off-white/cream (`#DFDBD2`, `#C7C1B6`) to provide high-contrast architectural detailing.

---

## 5. Architectural & Environmental Motifs

### Central/Eastern European "Brick Gothic" (*Backsteingotik*)
* **Key Features:** Crow-stepped gables (stair-stepped roof edges), tall narrow pointed-arch windows, fortified red-brick curtain walls with crenellations, and square watchtowers with hipped tile roofs.
* **Usage:** Town halls, churches, monasteries, guildhalls, city gates, and castles.

### Rural Slavonic / Germanic Timber Vernacular
* **Key Features:** Horizontal interlocking log construction (chinked with moss or clay), steep $45^\circ$–$55^\circ$ pitched roofs, overhanging eaves, and small wooden shutters.
* **Usage:** Peasant housing, granaries, windmills, sawmills, and storehouses.

### Environmental Clutter (Doodads)
To prevent the ground plane from looking sterile, surround buildings with small functional props:
* Wooden barrels, stacked firewood piles, hay bales, handcarts, timber sawhorses, market stalls with striped canvas awnings (red/white, blue/white, yellow/green), and stone-rimmed wells.

---

## 6. Gameplay Readability & UI Conventions

* **Building Occlusion (Ghosting):** Tall foreground structures (churches, walls, high gables) should dynamically fade to **$40\%$–$50\%$ opacity** when units walk behind them or when the cursor hovers over occluded tiles.
* **Terrain Blending:** Dirt roads and plazas should use soft alpha-masked splatmaps to blend organically into grass, avoiding harsh geometric tile seams.
* **Activity Indicators:** Production buildings should feature visible external workspaces (e.g., a blacksmith's glowing outdoor forge, a quarry's wooden crane, or a carpenter's sawhorse yard) so players can see animated villagers working outside.

---

## 7. Reference Prompt Template (For Concept Art & Asset Ideation)
When generating concept art or placeholder views using AI tools, use the following structure:

> **Prompt Structure:**  
> `2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, [SPECIFIC SCENE/BUILDING], Central European Brick Gothic and rustic log cabin architecture, muted earthy color palette, olive green grass, worn dirt roads, tiny medieval townsfolk and wooden carts, crisp surface textures, hard directional drop shadows, orthographic projection, no UI.`