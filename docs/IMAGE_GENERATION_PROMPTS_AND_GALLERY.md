# Visual Asset Gallery & AI Image Generation Prompts
## Lublin Anno Domini 1392 — 2D Concept Art & 3D Modeling Reference Archive

**Artistic Direction:** Late-1990s / Early-2000s Pre-Rendered Isometric PC Strategy Game (*Stronghold*, *Knights and Merchants*, *Patrician III*, *The Guild / Europa 1400*)  
**Projection Standard:** True Orthographic (Dimetric $30^\circ$ pitch / True Isometric $35.264^\circ$, $45^\circ$ base yaw, zero perspective convergence)  
**Palette Standard:** Earthy, weathered materials (Backsteingotik red brick `#8C3B2B`, aged oak framing `#4A3B2C`, sun-bleached thatch `#9E8656`, loess limestone `#B8B09E`, oxidized copper `#3D7A68`, olive grasslands `#556236`, dry mud roads `#7A6A53`).

---

## Table of Contents
1. [Master Prompt Engineering Standards](#1-master-prompt-engineering-standards)
2. [Artisan Guild Workshop Multi-View Reference Photos](#2-artisan-guild-workshop-multi-view-reference-photos-reference_photos)
   - [Baker's House & Masonry Oven (3-View Set)](#bakers-house--masonry-oven-3-view-set)
   - [Tanner's Riverside Workshop](#tanners-riverside-workshop)
   - [Brewer's Malthouse & Cask Yard](#brewers-malthouse--cask-yard)
   - [Blacksmith's Workshop & Open Forge (3-View Set)](#blacksmiths-workshop--open-forge-3-view-set)
   - [Potter's Shed & Kiln Yard](#potters-shed--kiln-yard)
   - [Weaver's Half-Timber Workshop](#weavers-half-timber-workshop)
   - [Riverside Watermill](#riverside-watermill)
3. [Worker & Citizen 3-View Turnaround Sheets](#3-worker--citizen-3-view-turnaround-sheets-reference_photosworkers)
   - [Master Blacksmith Turnaround](#master-blacksmith-turnaround)
   - [Artisan Baker Turnaround](#artisan-baker-turnaround)
   - [Master Tanner Turnaround](#master-tanner-turnaround)
4. [Macro City District & Regional Concept Art](#4-macro-city-district--regional-concept-art-concept_art)
   - [Artisan and Brewery District](#artisan-and-brewery-district)
   - [Brick Monastery with a Cloister Garden](#brick-monastery-with-a-cloister-garden)
   - [Fortified Castle Courtyard & Bailey](#fortified-castle-courtyard--bailey)
   - [Fortified River Crossing with Watermill](#fortified-river-crossing-with-watermill)
   - [Hillside Iron Mine & Smelting Camp](#hillside-iron-mine--smelting-camp)
   - [Riverside Harbor Wharves](#riverside-harbor-wharves)
   - [Rural Farming Village & Post Windmill](#rural-farming-village--post-windmill)
   - [Stone Quarry & Logging Camp](#stone-quarry--logging-camp)
   - [Tournament Fairground Outside City Walls](#tournament-fairground-outside-city-walls)
5. [In-Engine Screenshots & Visual Deliverables](#5-in-engine-screenshots--visual-deliverables)
6. [Summary Matrix: Image to 3D Model Mapping](#6-summary-matrix-image-to-3d-model-mapping)

---

## 1. Master Prompt Engineering Standards

All reference images and concept art are generated using a disciplined prompt structure ensuring visual continuity across workshops and districts:

```
[CAMERA & ENGINE AESTHETIC]
"2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites,"

[SUBJECT & WORKSPACE DETAILS]
"[SPECIFIC BUILDING TYPE/WORKSHOP], [PRIMARY EXTERIOR MACHINERY & WORKSPACE], [OUTDOOR EQUIPMENT & PROPS],"

[ARCHITECTURAL STYLE & GEOGRAPHY]
"Central European Brick Gothic and timber vernacular architecture, [ROOF & WALL MATERIALS],"

[PALETTE, LIGHTING & PROJECTION CONSTRAINTS]
"muted earthy color palette, crisp surface textures, hard directional drop shadows, orthographic projection, no UI"
```

---

## 2. Artisan Guild Workshop Reference Photos (`reference_photos/`)

These images provide direct visual blueprints for procedural Blender modeling (`build_assets.py`) and master catalog descriptions (`BUILDINGS_AND_WORKERS_CATALOG.md`).

---

### Baker's House & Masonry Oven (3-View Set)

#### Front / Primary Street Entrance:
![Baker's House Front Entrance](../reference_photos/baker_house/front.jpg)

#### Side Profile Elevation (Flour Chute & Firewood Shed):
![Baker's House Side Elevation](../reference_photos/baker_house/side.jpg)

#### Rear Yard Elevation (Domed Stone Bake-Oven & Ash Shovels):
![Baker's House Rear Yard Oven](../reference_photos/baker_house/back.jpg)

- **Directory:** [`reference_photos/baker_house/`](../reference_photos/baker_house/)
  - `front.jpg`: Isometric front facade with pretzel guild sign and entrance portal.
  - `side.jpg`: Side profile showing steep $50^\circ$ roof, side firewood shelter, and flour chute.
  - `back.jpg`: Rear yard with massive domed stone bread oven, brick chimney, bread peel, and firewood cords.
- **Associated 3D Model:** [`public/models/baker_house.glb`](../public/models/baker_house.glb)
- **Associated Worker:** `worker_baker` ([Turnaround Reference](#artisan-baker-turnaround))
- **Key Generation Prompts:**
  - *Front View (16:9):*
    ```text
    2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, medieval baker's house and bakery workshop, outdoor domed brick bread oven with smoking stone chimney, stacked birch firewood cords, wooden peel shovel, sacks of flour, gilded pretzel guild sign, timber-framed plaster walls, clay pantile roof, muted earthy color palette, crisp surface textures, hard directional drop shadows, orthographic projection, no UI
    ```
  - *Side Profile View — Harmonized (1:1):*
    ```text
    2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, side profile view of medieval baker's house, steep 50-degree gable roof with red terracotta clay pantiles matching front facade, half-timbered upper floor with cream plaster and dark oak beams, limestone ashlar base, outdoor domed red-brick bread baking oven with tall smoking stone chimney projecting on the flank, protective timber lean-to canopy over oven, stacked birch firewood logs, flour delivery chute, Central European Brick Gothic, muted earthy palette, hard directional drop shadows, orthographic projection, no UI
    ```
  - *Rear Yard View (1:1):*
    ```text
    2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, rear yard view of medieval baker house, large domed stone bread baking oven with smoking brick chimney built into the back wall, wooden ash shovels, bread peel leaning against oven, stacked cords of firewood, flour barrels, small vegetable garden, wattle fence, Central European timber and stone architecture, muted earthy palette, hard directional drop shadows, orthographic projection, no UI
    ```
> [!NOTE]
> **Architectural Consistency Judge (ACJ) Audit: Remediated & Harmonized**  
> The initial side profile generation displayed grey cedar wood shingles and an isolated firewood shed. The Judge rejected this due to material and machinery discontinuity with `front.jpg`. A targeted remediation was generated anchoring the red terracotta clay pantile roof, cream half-timbering, limestone ashlar plinth, and the domed brick baking oven complex with its tall smoking chimney on the right flank under a protective lean-to canopy. All features now align 100% with `baker_house.glb` in Blender.

---

### Tanner's Riverside Workshop

![Tanner's Riverside Workshop](../reference_photos/tanner_workshop.jpg)

- **File Path:** [`reference_photos/tanner_workshop.jpg`](../reference_photos/tanner_workshop.jpg)
- **Associated 3D Model:** [`public/models/house_tanner.glb`](../public/models/house_tanner.glb)
- **Associated Worker:** `worker_master_tanner`
- **Aspect Ratio:** `16:9`
- **Generation Prompt:**
  ```text
  2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, medieval tanner's workshop along riverbank, outdoor wooden hide soaking vats with dark tannin liquid, large wooden drying racks with stretched animal skins and hides, fleshing beam with scraping knife, stacks of pelts, rustic timber and thatch workshop building, muted earthy color palette, crisp surface textures, hard directional drop shadows, orthographic projection, no UI
  ```
- **Architectural & Workspace Key Features:**
  - Rustic weathered log cabin with open-sided upper slatted drying gallery for river breeze circulation.
  - Sagging straw thatch roof with mossy eaves.
  - 4 sunken rectangular wooden tanning vats dug into the riverbank ground, filled with dark brown oak-bark tannin liquor.
  - 2 tall timber vertical trestle frames holding stretched rawhide pelts.
  - Low tilted wooden fleshing beam (*stół kuśnierski*) with two-handled curved scraping drawknife.
  - Piles of salted raw pelts and finished cured leather hides.
  - Hanging tavern guild sign: stretched ox hide.

---

### Brewer's Malthouse & Cask Yard

![Brewer's Malthouse & Cask Yard](../reference_photos/brewer_malthouse.jpg)

- **File Path:** [`reference_photos/brewer_malthouse.jpg`](../reference_photos/brewer_malthouse.jpg)
- **Associated 3D Model:** [`public/models/house_brewer.glb`](../public/models/house_brewer.glb)
- **Associated Workers:** `worker_master_brewer`, `worker_cooper`
- **Aspect Ratio:** `16:9`
- **Generation Prompt:**
  ```text
  2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, medieval brewer malthouse and tavern brewery, sturdy stone plinth with half-timbered upper floor with wooden ventilation louvers, copper brew kettle mash paddle guild sign, outdoor yard filled with wooden beer casks and barrels stacked in pyramids, soaking wash troughs, outdoor wooden tavern bench, warm earthy tones, crisp surface textures, hard directional drop shadows, orthographic projection, no UI
  ```
- **Architectural & Workspace Key Features:**
  - Massive Gothic brick ground floor with arched wagon portal.
  - Half-timbered upper story fitted with horizontal wooden louvers (*żaluzje słodowe*) for venting grain moisture during barley malting.
  - Weathered oak wooden shingle roof.
  - Cask-washing yard with 2 long wooden water-soak troughs with stone drainage.
  - Pyramid stack of 6 oak beer casks bound with iron hoops.
  - Outdoor tavern hospitality area with 2 heavy oak trestle tables and drinking benches.
  - Hanging guild sign: polished copper mash paddle and tankard.

---

### Blacksmith's Workshop & Open Forge (3-View Set)

#### Front / Primary Forge Canopy:
![Blacksmith's Workshop Front Entrance](../reference_photos/blacksmith_workshop/front.jpg)

#### Side Profile Elevation (Coal Storage Bunker & Quench Trough):
![Blacksmith's Workshop Side Elevation](../reference_photos/blacksmith_workshop/side.jpg)

#### Rear Storage Yard (Bloomery Smelting Furnace & Iron Racks):
![Blacksmith's Workshop Rear Yard](../reference_photos/blacksmith_workshop/back.jpg)

- **Directory:** [`reference_photos/blacksmith_workshop/`](../reference_photos/blacksmith_workshop/)
  - `front.jpg`: Primary open forge with anvil, glowing hearth, weapon rack, and timber canopy.
  - `side.jpg`: Side profile showing coal and charcoal storage shed, water trough, and brick chimney stack.
  - `back.jpg`: Rear storage yard with brick bloomery furnace, raw iron billets, scrap metal pile, and slag.
- **Associated 3D Model:** [`public/models/blacksmith_workshop.glb`](../public/models/blacksmith_workshop.glb)
- **Associated Workers:** `worker_blacksmith` ([Turnaround Reference](#master-blacksmith-turnaround))
- **Key Generation Prompts:**
  - *Front View (16:9):*
    ```text
    2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, medieval blacksmith workshop, outdoor covered timber shed with open masonry hearth forge and glowing hot orange embers, thick smoke from stone chimney, heavy iron anvil on oak tree stump, water quenching wooden trough with rising steam, weapon rack with iron axe heads and swords, stacks of coal and iron ingots, muted earthy color palette, crisp surface textures, hard directional drop shadows, orthographic projection, no UI
    ```
  - *Side Profile View (1:1):*
    ```text
    2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, side profile elevation view of medieval blacksmith forge, timber lean-to canopy supported by heavy oak posts, covered coal and charcoal storage bin with dark coal heap, water quench trough, iron tool racks, Central European brick and timber vernacular, hard directional drop shadows, orthographic projection, no UI
    ```
  - *Rear Yard View (1:1):*
    ```text
    2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, rear storage yard view of medieval blacksmith forge, brick bloomery smelting furnace with glowing smoke, stacked pig iron ingots, racks of raw iron bars, scrap metal scrapheap, coal cart, low timber fence, dirt ground with soot patches, orthographic projection, no UI
    ```

---

### Potter's Shed & Kiln Yard

![Potter's Shed & Kiln Yard](../reference_photos/potter_workshop.jpg)

- **File Path:** [`reference_photos/potter_workshop.jpg`](../reference_photos/potter_workshop.jpg)
- **Associated 3D Model:** [`public/models/house_potter.glb`](../public/models/house_potter.glb)
- **Associated Worker:** `worker_master_potter`
- **Aspect Ratio:** `16:9`
- **Generation Prompt:**
  ```text
  2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, medieval potter workshop and kiln yard, outdoor domed red brick pottery kiln with stone chimney and glowing stokehole, multi-tiered wooden shelves holding rows of terracotta clay pots, jugs, amphorae, and bowls, outdoor wooden potter bench with foot kick wheel, mounds of grey clay and water buckets, rustic wattle-and-daub cottage with weathered thatched roof, warm earthy color palette, crisp surface textures, hard directional drop shadows, orthographic projection, no UI
  ```
- **Architectural & Workspace Key Features:**
  - Wattle-and-daub cottage with cream loam plaster and low weathered thatched roof.
  - Circular red-brick updraft pottery kiln ($2.8\text{m}$ dia.) with arched glowing stokehole and stone flue chimney.
  - Outdoor wooden potting bench equipped with foot-operated kick-wheel and water buckets.
  - 3-tier wooden open drying rack displaying terracotta amphorae, clay jugs, bowls, and ridge tiles.
  - Raw clay mounds and firewood stacks.
  - Hanging guild sign: glazed terracotta amphora.

---

### Weaver's Half-Timber Workshop

![Weaver's Half-Timber Workshop](../reference_photos/weaver_workshop.jpg)

- **File Path:** [`reference_photos/weaver_workshop.jpg`](../reference_photos/weaver_workshop.jpg)
- **Associated 3D Model:** [`public/models/house_weaver.glb`](../public/models/house_weaver.glb)
- **Associated Worker:** `worker_master_weaver`
- **Aspect Ratio:** `16:9`
- **Generation Prompt:**
  ```text
  2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, medieval weaver workshop and clothiers yard, handsome half-timbered building with St. Andrews diagonal cross braces, attic dormer with hoist pulley beam, outdoor wooden yarn stretching frames, steaming dye vats with draped dyed wool and linen fabrics in vibrant red and indigo blue drying on timber rails, bolts of woven broadcloth, warm earthy color palette, crisp surface textures, hard directional drop shadows, orthographic projection, no UI
  ```
- **Architectural & Workspace Key Features:**
  - Half-timbered structure with diagonal St. Andrew's cross braces (*krzyże św. Andrzeja*) and white lime plaster.
  - Attic dormer with projecting hoist beam, rope pulley, and suspended wool sack.
  - 2 circular stone dye cauldrons filled with steaming indigo blue and madder scarlet liquid dyes.
  - Long horizontal wooden rail racks with draped dyed wool and linen cloth drying in the breeze.
  - Vertical wooden yarn-stretching peg frame.
  - Clothier's handcart loaded with rolled broadcloth bolts.
  - Hanging guild sign: carved weaving shuttle and spindle.

---

### Riverside Watermill

![Riverside Watermill](../reference_photos/watermill.jpg)

- **File Path:** [`reference_photos/watermill.jpg`](../reference_photos/watermill.jpg)
- **Associated 3D Model:** [`public/models/watermill.glb`](../public/models/watermill.glb)
- **Associated Workers:** `worker_miller_master`, `worker_flour_porter`
- **Aspect Ratio:** `16:9`
- **Generation Prompt:**
  ```text
  2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, medieval watermill on riverbank, timber building on heavy oak stilts over the water, large rotating wooden undershot waterwheel with splashing water, timber flume race, riverside wooden pier with stacked burlap flour sacks and barrels, muted earthy color palette, crisp surface textures, hard directional drop shadows, orthographic projection, no UI
  ```
- **Architectural & Workspace Key Features:**
  - 2-story timber log mill cabin elevated on heavy oak stilts driven into the riverbed.
  - Undershot wooden waterwheel ($4.2\text{m}$ diameter) with 12 flat paddle blades and foaming splash effects.
  - Elevated timber flume race channeling river current onto the wheel paddles.
  - Quayside wooden boardwalk pier extending over water with stacked flour sacks and wooden hand barrow.
  - Sagging straw thatch roof with mossy eaves.

---

## 3. Worker & Citizen 3-View Turnaround Sheets (`reference_photos/workers/`)

These multi-view character turnaround model sheets provide exact orthographic silhouettes, historical costume details, work aprons, and tool specifications for procedural character creation and rigging in Blender.

---

### Master Blacksmith Turnaround

![Master Blacksmith 3-View Turnaround](../reference_photos/workers/worker_blacksmith_turnaround.jpg)

- **File Path:** [`reference_photos/workers/worker_blacksmith_turnaround.jpg`](../reference_photos/workers/worker_blacksmith_turnaround.jpg)
- **Associated 3D Model:** [`public/models/worker_blacksmith.glb`](../public/models/worker_blacksmith.glb)
- **Aspect Ratio:** `16:9`
- **Views Included:** Front View, Profile Side View, Rear View
- **Generation Prompt:**
  ```text
  Orthographic 3-view character model sheet showing front view, side profile view, and rear view side-by-side, 14th-century medieval master blacksmith, wearing heavy stained leather apron over brown woolen tunic, rolled-up linen sleeves, sturdy leather boots, holding iron tongs and blacksmith hammer, leather belt with pouch, neutral solid beige parchment background, crisp silhouette, studio lighting, late 1990s PC strategy game sprite reference, no UI
  ```
- **Costume & Equipment Details:**
  - Heavy soot-stained cowhide apron with forged steel buckles and rear tie straps.
  - Brown woolen tunic with rolled-up natural linen undergarment sleeves.
  - Double-wrapped leather tool belt supporting small utility knife sheath and coin purse.
  - Held craft tools: long-handled iron forging tongs with red-hot heated billet tip, and heavy steel cross-peen hammer.
  - Reinforced knee-high leather work boots.

---

### Artisan Baker Turnaround

![Artisan Baker 3-View Turnaround](../reference_photos/workers/worker_baker_turnaround.jpg)

- **File Path:** [`reference_photos/workers/worker_baker_turnaround.jpg`](../reference_photos/workers/worker_baker_turnaround.jpg)
- **Associated 3D Model:** [`public/models/worker_baker.glb`](../public/models/worker_baker.glb)
- **Aspect Ratio:** `16:9`
- **Views Included:** Front View, Profile Side View, Rear View
- **Generation Prompt:**
  ```text
  Orthographic 3-view character model sheet showing front view, side profile view, and rear view side-by-side, 14th-century medieval artisan baker, white linen apron dusted with white flour over simple undyed woolen tunic, rolled-up sleeves, holding long wooden bread peel shovel, canvas baker cap, leather turnshoes, neutral solid beige parchment background, crisp silhouette, studio lighting, late 1990s PC strategy game sprite reference, no UI
  ```
- **Costume & Equipment Details:**
  - Bleached linen baker's apron heavily dusted with rye and wheat flour.
  - Puffed canvas chef's baker cap (*barett*) covering dark curls.
  - Undyed homespun woolen tunic with cord waist cinch.
  - Held craft tool: full-length $1.8\text{m}$ wooden bread peel paddle shovel.
  - Soft cowhide turnshoes.

---

### Master Tanner Turnaround

![Master Tanner 3-View Turnaround](../reference_photos/workers/worker_tanner_turnaround.jpg)

- **File Path:** [`reference_photos/workers/worker_tanner_turnaround.jpg`](../reference_photos/workers/worker_tanner_turnaround.jpg)
- **Associated 3D Model:** [`public/models/worker_tanner.glb`](../public/models/worker_tanner.glb)
- **Aspect Ratio:** `16:9`
- **Views Included:** Front View, Profile Side View, Rear View
- **Generation Prompt:**
  ```text
  Orthographic 3-view character model sheet showing front view, side profile view, and rear view side-by-side, 14th-century medieval tanner worker, heavy dark oiled leather apron stained with tanbark, thick rubberized water-resistant leather work boots, rolled-up woolen sleeves, holding a curved two-handed iron fleshing knife, cloth coif head covering, neutral solid beige parchment background, crisp silhouette, studio lighting, late 1990s PC strategy game sprite reference, no UI
  ```
- **Costume & Equipment Details:**
  - Water-resistant oiled leather apron stained with oak tanbark and lime solution.
  - Linen coif tied under the chin to keep hair free of chemical baths.
  - Thick, greased high water boots for wading into sunken lime vats.
  - Held craft tool: curved two-handled iron fleshing drawknife for scraping hides across the wooden beam.

---

## 4. Macro City District & Regional Concept Art (`concept_art/`)

These panoramic concept artworks define the regional geography, atmospheric lighting, and architectural hierarchy of Lublin Anno Domini 1392.

---

### Artisan and Brewery District

![Artisan and Brewery District](../concept_art/artisan%20and%20brewery%20district.jpg)

- **File Path:** [`concept_art/artisan and brewery district.jpg`](../concept_art/artisan%20and%20brewery%20district.jpg)
- **Districts Covered:** Bramowa Quarter, Craft Enclaves, Suburbs
- **Key Features:** Central double-chimney brick firing kiln, half-timbered brewery malthouses, outdoor pottery shelves, log cabins, dirt roads, cart traffic, and active craftsmen.
- **Generation Prompt:**
  ```text
  2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, artisan and brewery district, masonry firing kiln with smoking double chimneys, half-timbered brewery malthouse, outdoor pottery drying shelves, beer barrels, log cabins, Central European architecture, muted earthy color palette, olive green grass, worn dirt roads, tiny medieval townsfolk, hard directional drop shadows, orthographic projection, no UI
  ```

---

### Brick Monastery with a Cloister Garden

![Brick Monastery with a Cloister Garden](../concept_art/brick_monastery_with_a_cloister_garden.jpg)

- **File Path:** [`concept_art/brick_monastery_with_a_cloister_garden.jpg`](../concept_art/brick_monastery_with_a_cloister_garden.jpg)
- **Associated 3D Model:** [`public/models/monastery_cloister.glb`](../public/models/monastery_cloister.glb)
- **Key Features:** Dominican Friary quadrangle, pointed brick arcaded cloister walks, enclosed quad with geometric raised herbal beds, central stone fountain basin, monks in white and brown habits.
- **Generation Prompt:**
  ```text
  2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, brick monastery with a cloister garden, Gothic brick quadrangle, pointed arcades, geometric raised medicinal herb planting beds, stone fountain basin, monks in robes, Central European Brick Gothic, muted earthy color palette, orthographic projection, no UI
  ```

---

### Fortified Castle Courtyard & Bailey

![Fortified Castle Courtyard](../concept_art/fortified_castle_courtyard.jpg)

- **File Path:** [`concept_art/fortified_castle_courtyard.jpg`](../concept_art/fortified_castle_courtyard.jpg)
- **Associated 3D Model:** [`public/models/castle_donjon.glb`](../public/models/castle_donjon.glb), [`public/models/archery_yard.glb`](../public/models/archery_yard.glb)
- **Key Features:** Wzgórze Zamkowe plateau, cylindrical limestone donjon keep, brick battlements with machicolations, timber hoardings, bailey guards, cobblestones, and outer curtain walls.
- **Generation Prompt:**
  ```text
  2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, fortified castle courtyard and bailey on elevated hill, Romanesque limestone donjon keep, brick battlements with machicolations, timber hoardings, knights and guards with spears, cobblestones, orthographic projection, no UI
  ```

---

### Fortified River Crossing with Watermill

![Fortified River Crossing with a Watermill](../concept_art/fortified_river_crossing_with_a_watermill.jpg)

- **File Path:** [`concept_art/fortified_river_crossing_with_a_watermill.jpg`](../concept_art/fortified_river_crossing_with_a_watermill.jpg)
- **Associated 3D Models:** [`public/models/watermill.glb`](../public/models/watermill.glb), [`public/models/gate_grodzka.glb`](../public/models/gate_grodzka.glb)
- **Key Features:** Fortified multi-arch brick and stone bridge spanning the Czechówka river, twin gatehouse towers with crenellations, horse carts crossing, and riverbank watermill with active waterwheel.
- **Generation Prompt:**
  ```text
  2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, fortified river crossing with a watermill, arched brick and stone bridge with fortified gate towers, horse-drawn carts crossing river, wooden watermill on river stilts with large undershot paddle waterwheel, flour sacks on dock, orthographic projection, no UI
  ```

---

### Hillside Iron Mine & Smelting Camp

![Hillside Iron Mine and Smelting Camp](../concept_art/hillside%20iron%20mine%20and%20smelting%20camp.jpg)

- **File Path:** [`concept_art/hillside iron mine and smelting camp.jpg`](../concept_art/hillside%20iron%20mine%20and%20smelting%20camp.jpg)
- **Associated 3D Model:** [`public/models/blacksmith_workshop.glb`](../public/models/blacksmith_workshop.glb)
- **Key Features:** Timber-shored mine adits cut into loess terrace, bloomery smelting furnace with glowing taphole, miners with pickaxes and ore barrows, coal ricks, and log bunkhouses.
- **Generation Prompt:**
  ```text
  2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, hillside iron mine and smelting camp, timber adit mine entrances into loess cliff, bloomery smelting furnace with glowing ore and stone chimneys, miners with pickaxes and ore carts, coal heaps, timber cabins, orthographic projection, no UI
  ```

---

### Riverside Harbor Wharves

![Riverside Harbor Wharves](../concept_art/riverside_harbor.jpg)

- **File Path:** [`concept_art/riverside_harbor.jpg`](../concept_art/riverside_harbor.jpg)
- **Associated 3D Model:** [`public/models/river_harbor.glb`](../public/models/river_harbor.glb)
- **Key Features:** Oak boardwalk wharves on pilings along the Bystrzyca river, moored 14m clinker-built wooden cog ships, cylindrical treadwheel crane, cargo barrels, grain sacks, stevedores, and town hall in background.
- **Generation Prompt:**
  ```text
  2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, riverside harbor and merchant wharves, wooden piers and bulkheads on riverbank, clinker-built wooden cog ships moored to bollards, cylindrical wooden treadwheel crane, cargo barrels and grain sacks, merchants and stevedores, Gothic brick town hall in background, orthographic projection, no UI
  ```

---

### Rural Farming Village & Post Windmill

![Rural Farming Village](../concept_art/rural_farming_village.jpg)

- **File Path:** [`concept_art/rural_farming_village.jpg`](../concept_art/rural_farming_village.jpg)
- **Associated 3D Models:** [`public/models/windmill.glb`](../public/models/windmill.glb), [`public/models/house_timber_log.glb`](../public/models/house_timber_log.glb)
- **Key Features:** Golden ripe wheat fields swaths with scything peasants, hilltop post windmill with 4-blade canvas sails, thatched log cottages with fenced cabbage gardens, dirt cart crossroads.
- **Generation Prompt:**
  ```text
  2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, rural farming village outside fortified city, golden wheat fields with peasants harvesting with curved scythes, hilltop wooden post windmill with 4-blade canvas sails, rustic thatched log cottages with fenced vegetable gardens, dirt crossroads with ox carts, orthographic projection, no UI
  ```

---

### Stone Quarry & Logging Camp

![Stone Quarry and Logging Camp](../concept_art/stone_quarry_and_logging_camp.jpg)

- **File Path:** [`concept_art/stone_quarry_and_logging_camp.jpg`](../concept_art/stone_quarry_and_logging_camp.jpg)
- **Associated 3D Models:** [`public/models/stone_quarry.glb`](../public/models/stone_quarry.glb), [`public/models/logging_camp.glb`](../public/models/logging_camp.glb)
- **Key Features:** Terraced limestone rock quarry pit with heavy timber A-frame jib crane hoisting ashlar blocks, adjacent logging camp with elevated two-man pit-saw trestle over sawdust pit, log stacks, woodcutters.
- **Generation Prompt:**
  ```text
  2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, stone quarry and logging camp, terraced limestone quarry pit with timber A-frame derrick crane hoisting cut ashlar blocks, stonemasons dressing stone, adjacent logging camp with two-man pit-saw trestle over sawdust pit, pine log ricks, woodcutters with broadaxes, orthographic projection, no UI
  ```

---

### Tournament Fairground Outside City Walls

![Tournament Fairground Outside City Walls](../concept_art/tournament%20fairground%20outside%20the%20city%20walls.jpg)

- **File Path:** [`concept_art/tournament fairground outside the city walls.jpg`](../concept_art/tournament%20fairground%20outside%20the%20city%20walls.jpg)
- **Associated 3D Models:** [`public/models/curtain_wall.glb`](../public/models/curtain_wall.glb), [`public/models/curtain_tower.glb`](../public/models/curtain_tower.glb)
- **Key Features:** Striped heraldic tournament pavilions, jousting tilt rail lane, armored knights on warhorses, viewing stands, city curtain walls and brick gate towers in background.
- **Generation Prompt:**
  ```text
  2D isometric medieval city-builder game screenshot, late 1990s PC strategy game aesthetic, pre-rendered 3D sprites, tournament fairground outside the city walls, royal pavilion tents with heraldic striped canopies, jousting tilt rail lane with armored knights on caparisoned warhorses, royal viewing stand, cheering burghers, fortified curtain wall and towers in background, orthographic projection, no UI
  ```

---

## 5. In-Engine Screenshots & Visual Deliverables

### Final High-Resolution Simulation View
![Final Simulation Screenshot](../public/screenshot_final.png)
- **File Path:** [`public/screenshot_final.png`](../public/screenshot_final.png)
- **Resolution:** $1920 \times 1080$
- **Engine:** Three.js Orthographic Isometric Pipeline, PCF Soft Shadows (`shadowMap.bias = -0.0003`), Procedural Cobblestone Ground Canvas.
- **Active Entities:** 580 Non-Overlapping Parcels, 31 Blender GLB Assets, 1,500 Living Citizens with clockwork bell schedules.

---

## 6. Summary Matrix: Image to 3D Model Mapping

| # | Image File | Category | Associated 3D GLB Asset | Associated Worker / Activity |
|---|---|---|---|---|
| 1 | `reference_photos/baker_house/front.jpg` | Workshop 3-View Set (Front) | `public/models/baker_house.glb` | `worker_baker` (sliding bread into oven) |
| 2 | `reference_photos/baker_house/side.jpg` | Workshop 3-View Set (Side Profile) | `public/models/baker_house.glb` | `worker_baker` (firewood & flour delivery) |
| 3 | `reference_photos/baker_house/back.jpg` | Workshop 3-View Set (Rear Yard) | `public/models/baker_house.glb` | `worker_baker` (stokehole & ash cleanup) |
| 4 | `reference_photos/blacksmith_workshop/front.jpg` | Workshop 3-View Set (Front) | `public/models/blacksmith_workshop.glb` | `worker_blacksmith` (forging on anvil) |
| 5 | `reference_photos/blacksmith_workshop/side.jpg` | Workshop 3-View Set (Side Profile) | `public/models/blacksmith_workshop.glb` | `worker_blacksmith` (coal bunker & quench trough) |
| 6 | `reference_photos/blacksmith_workshop/back.jpg` | Workshop 3-View Set (Rear Yard) | `public/models/blacksmith_workshop.glb` | `worker_blacksmith` (bloomery smelting & iron racks) |
| 7 | `reference_photos/tanner_workshop/front.jpg` | Workshop Reference (Primary) | `public/models/tanner_workshop.glb` | `worker_tanner` (scraping hide on fleshing beam) |
| 8 | `reference_photos/brewer_malthouse/front.jpg` | Workshop Reference (Primary) | `public/models/brewer_malthouse.glb` | `worker_brewer` & cooper |
| 9 | `reference_photos/potter_workshop/front.jpg` | Workshop Reference (Primary) | `public/models/potter_workshop.glb` | `worker_potter` (throwing clay amphora) |
| 10 | `reference_photos/weaver_workshop/front.jpg` | Workshop Reference (Primary) | `public/models/weaver_workshop.glb` | `worker_weaver` (operating loom & dyeing) |
| 11 | `reference_photos/watermill/front.jpg` | Workshop Reference (Primary) | `public/models/watermill.glb` | `worker_miller` & flour porters |
| 12 | `reference_photos/workers/worker_blacksmith_turnaround.jpg` | Character 3-View Turnaround | `public/models/worker_blacksmith.glb` | Master Blacksmith (leather apron, tongs, hammer) |
| 13 | `reference_photos/workers/worker_baker_turnaround.jpg` | Character 3-View Turnaround | `public/models/worker_baker.glb` | Artisan Baker (flour-dusted apron, bread peel) |
| 14 | `reference_photos/workers/worker_tanner_turnaround.jpg` | Character 3-View Turnaround | `public/models/worker_tanner.glb` | Master Tanner (oiled apron, fleshing drawknife) |
| 15 | `concept_art/artisan and brewery district.jpg` | District Concept Art | Multiple Craft Workshops | Artisans, potters, brewers |
| 16 | `concept_art/brick_monastery_with_a_cloister_garden.jpg` | Civic/Religious Concept Art | `public/models/monastery_cloister.glb` | Monks, gardeners, herbalists |
| 17 | `concept_art/fortified_castle_courtyard.jpg` | Fortification Concept Art | `public/models/castle_donjon.glb` | Castellan, guards, knights |
| 18 | `concept_art/fortified_river_crossing_with_a_watermill.jpg` | Regional Concept Art | `public/models/watermill.glb`, `gate_grodzka.glb` | Millers, carters, gate bailiffs |
| 19 | `concept_art/hillside iron mine and smelting camp.jpg` | Industrial Concept Art | `public/models/blacksmith_workshop.glb` | Miners, smelters, charcoal burners |
| 20 | `concept_art/riverside_harbor.jpg` | Commercial Concept Art | `public/models/river_harbor.glb` | Harbor master, stevedores |
| 21 | `concept_art/rural_farming_village.jpg` | Regional Concept Art | `public/models/windmill.glb`, `house_timber_log.glb` | Farmers, scythers, windmiller |
| 22 | `concept_art/stone_quarry_and_logging_camp.jpg` | Industrial Concept Art | `public/models/stone_quarry.glb`, `logging_camp.glb` | Quarrymen, hewers, pit sawyers |
| 23 | `concept_art/tournament fairground outside the city walls.jpg` | Military Concept Art | `public/models/curtain_wall.glb`, `curtain_tower.glb` | Knights, heralds, spectators |
