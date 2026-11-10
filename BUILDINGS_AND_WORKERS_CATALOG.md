# Master Catalog: Medieval Buildings, Workspaces & Workers
## Lublin Anno Domini 1392 — Visual & Procedural 3D Asset Specification
**Project Aesthetic:** Late-1990s / Early-2000s Pre-Rendered Isometric PC Strategy Game (*Stronghold*, *Knights and Merchants*, *Patrician III*)  
**Architecture Style:** Central European Brick Gothic (*Backsteingotik*), Little Poland Timber Vernacular (*Domy Zrębowe*), and Half-Timbered Tenements (*Szachulec*)  
**Coordinate Conventions:** Blender (Z-up, metric meters, front = -Y) $\rightarrow$ glTF / Three.js (Y-up, metric meters, front = +Z)

---

## Table of Contents
1. [Catalog Architecture & Standards](#1-catalog-architecture--standards)
2. [Complete Building Archetypes (22 Buildings)](#2-complete-building-archetypes)
   - [Civic & Religious Architecture (1–4)](#civic--religious-architecture)
   - [Fortified Military Architecture (5–8)](#fortified-military-architecture)
   - [Industrial & Resource Production Complexes (9–14)](#industrial--resource-production-complexes)
   - [Artisan Guild Workshops (15–19)](#artisan-guild-workshops)
   - [Vernacular & Residential Housing (20–22)](#vernacular--residential-housing)
3. [Living Guild Workers & Artisans (18 Workers)](#3-living-guild-workers--artisans)
4. [Procedural Blender Python (`bmesh`) Construction Recipes](#4-procedural-blender-python-bmesh-construction-recipes)
5. [Procedural Texture Atlas UV Map Coordinates](#5-procedural-texture-atlas-uv-map-coordinates)

---

## 1. Catalog Architecture & Standards

### Metric Units & Scaling
- **Grid Scale:** $1.0\text{ unit} = 1.0\text{ meter}$.
- **Human Proportions:** Late-1990s PC strategy game readability ratio ($1:6.5$ head-to-body), height $= 1.75\text{m}$, shoulder width $= 0.55\text{m}$.
- **Doorway Clearances:** Height $= 2.1\text{m}$ to $2.4\text{m}$ ($1.2\times$ to $1.4\times$ human height) to maintain historical realism without RTS miniature distortion.
- **Wall Thickness:** Limestone plinth: $0.6\text{m}$–$0.8\text{m}$; Brick walls: $0.4\text{m}$–$0.6\text{m}$; Timber log walls: $0.25\text{m}$–$0.35\text{m}$.

### Material Palette & Shader Slot Index
All models bind to the unified 2048x2048 texture atlas through standard material slots:
- Slot 0: `mat_brick_gothic` (`#8C3B2B` terracotta red brick with `#DFDBD2` white lime mortar)
- Slot 1: `mat_timber_dark` (`#4A3B2C` dark weathered pine/oak structural framing)
- Slot 2: `mat_timber_plank` (`#7A6A53` warm pine planks, door shutters, floorboards)
- Slot 3: `mat_roof_tile_red` (`#B55338` fluted clay pantiles)
- Slot 4: `mat_roof_thatch` (`#9E8656` sun-bleached straw thatch with mossy eaves)
- Slot 5: `mat_roof_shingle` (`#5C5348` weathered oak/pine wooden shakes)
- Slot 6: `mat_stone_limestone` (`#B8B09E` chalky loess limestone ashlar blocks)
- Slot 7: `mat_plaster_white` (`#DFDBD2` white lime plaster tracery & *blendówki*)
- Slot 8: `mat_copper_patina` (`#3D7A68` verdigris oxidized copper spires)
- Slot 9: `mat_iron_wrought` (`#26262B` dark wrought iron hardware & tools)
- Slot 10: `mat_canvas_awning` (Striped market fabrics: red/white, blue/white, yellow/white)

---

## 2. Complete Building Archetypes

### Civic & Religious Architecture

#### 1. Old Town Hall (*Ratusz Miejski*)
- **ID:** `bldg_town_hall_ratusz`
- **Location:** Rynek (Market Square centroid: `(0, 0, 0)`).
- **Dimensions:** $18.0\text{m (W)} \times 24.0\text{m (D)} \times 28.5\text{m (Total H to Spire Apex)}$.
- **Stories:** 3 stories + vaulted cellar + 5-tier clock belfry tower.
- **Architectural Motifs:** Polish Gothic brick masonry; white plaster blind arcades (*blendówki*); 4 corner octagonal bartizans/turrets with verdigris copper spires; western stepped gable with pinnacles; ground-floor open vaulted loggia (*podcienia*).
- **Exterior Workspace / Station:** Grand external two-flight stone staircase with carved limestone balustrade facing the market square.
- **Associated Workers:** `worker_burgomaster`, `worker_town_scribe`.
- **Blender Generator:** `build_town_hall()` $\rightarrow$ `public/models/town_hall.glb`.

#### 2. Szmatruz (Royal Cloth & Bread Hall)
- **ID:** `bldg_szmatruz_cloth_hall`
- **Location:** Eastern Rynek flank (`(22, 0, -18)`).
- **Dimensions:** $14.0\text{m (W)} \times 28.0\text{m (D)} \times 11.5\text{m (H)}$.
- **Stories:** 1.5 stories (ground open arcade + attic fabric storage).
- **Architectural Motifs:** 22 rectangular brick pillars with limestone capitals; central covered market arcade aisle; red tile double-pitched gable roof.
- **Exterior Workspace / Station:** 16 open timber stall booths with trestle display counters loaded with broadcloth bolts, linen rolls, and round sourdough loaves.
- **Associated Workers:** `worker_draper_merchant`, `worker_bread_seller`.
- **Blender Generator:** `build_szmatruz()` $\rightarrow$ `public/models/szmatruz.glb`.

#### 3. Collegiate Parish Church (*Kościół św. Michała - Fara*)
- **ID:** `bldg_parish_church_fara`
- **Location:** Fara Quarter promontory overlooking the river (`(130, 0, 20)`).
- **Dimensions:** $16.0\text{m (W)} \times 32.0\text{m (D)} \times 46.0\text{m (Total Spire H)}$.
- **Stories:** Soaring single nave + side aisles + western belfry tower.
- **Architectural Motifs:** Stepped Gothic brick buttresses with stone weathering slopes; towering 60° clay-tiled roof; crow-stepped apse; western tower topped with octagonal belfry and copper needle spire.
- **Exterior Workspace / Station:** Arched stone portal porch with stone holy water stoup, wooden notice board, and cemetery cross courtyard.
- **Associated Workers:** `worker_parish_priest`, `worker_sexton_bellringer`.
- **Blender Generator:** `build_church_gothic()` $\rightarrow$ `public/models/church_gothic.glb`.

#### 4. Dominican Monastery & Cloister Garden
- **ID:** `bldg_monastery_cloister`
- **Location:** Dominican Friary Quarter.
- **Dimensions:** $26.0\text{m (W)} \times 26.0\text{m (D)} \times 14.0\text{m (H)}$ enclosing a $14.0\text{m} \times 14.0\text{m}$ inner quadrangle.
- **Stories:** 2 stories with perimeter vaulted cloister walk.
- **Architectural Motifs:** Quadrangle layout with pointed brick open-arcaded walkways surrounding an inner tranquil quad; red tile hip roof; stepped gable dormitory.
- **Exterior Workspace / Station:** Central cloister herb garden: 8 geometric raised timber planting beds cultivated with medicinal herbs (sage, thyme, lavender, chamomile), central stone fountain basin.
- **Associated Workers:** `worker_monk_gardener`, `worker_monk_apothecary`.
- **Blender Generator:** `build_monastery_cloister()` $\rightarrow$ `public/models/monastery_cloister.glb`.

---

### Fortified Military Architecture

#### 5. Romanesque Donjon Keep & Royal Bailey
- **ID:** `bldg_castle_donjon`
- **Location:** Wzgórze Zamkowe (Castle Hill high plateau: `(275, 0, 75)`).
- **Dimensions:** $14.0\text{m (Diameter)} \times 24.0\text{m (Cylinder H)} \times 30.0\text{m (Total H to Conical Roof)}$.
- **Stories:** 4 defensive levels with 3.2m thick limestone walls.
- **Architectural Motifs:** Massive cylindrical limestone ashlar masonry; upper brick defensive tier with machicolations; conical red tile roof; narrow arrow slit loops.
- **Exterior Workspace / Station:** Raised wooden draw-stair platform and bailey guardhouse with brazier fire basket.
- **Associated Workers:** `worker_royal_castellan`, `worker_castle_guard`.
- **Blender Generator:** `build_castle_donjon()` $\rightarrow$ `public/models/castle_donjon.glb`.

#### 6. Kraków Gate & Barbican Drawbridge (*Brama Krakowska*)
- **ID:** `bldg_krakow_gate`
- **Location:** Southwestern defensive curtain perimeter (`(-160, 0, 0)`).
- **Dimensions:** $11.0\text{m (W)} \times 13.0\text{m (D)} \times 24.0\text{m (H)}$.
- **Stories:** 4-tier gateway tower (square base transitioning into octagonal brick belfry).
- **Architectural Motifs:** Arched stone carriage portal with portcullis slot; copper-clad pyramidal spire; outer timber drawbridge spanning the dry moat.
- **Exterior Workspace / Station:** Raised gatekeeper wooden hoarding gallery overlooking the Kraków highway approach.
- **Associated Workers:** `worker_gate_captain`, `worker_guard_crossbow`.
- **Blender Generator:** `build_krakow_gate()` $\rightarrow$ `public/models/gate_krakow.glb`.

#### 7. Grodzka Gate & Czechówka Crossing (*Brama Grodzka*)
- **ID:** `bldg_grodzka_gate`
- **Location:** Northeastern perimeter opening toward Castle Hill (`(175, 0, 15)`).
- **Dimensions:** $9.5\text{m (W)} \times 11.0\text{m (D)} \times 18.0\text{m (H)}$.
- **Stories:** 3-tier rectangular brick gateway.
- **Architectural Motifs:** Heavy oak portcullis; hipped clay tile roof; machicolated overhanging parapet; flanking wall connections.
- **Exterior Workspace / Station:** Octagonal wooden royal toll-collector booth with balance scales, ledger desk, and iron toll box.
- **Associated Workers:** `worker_royal_toll_collector`, `worker_city_bailiff`.
- **Blender Generator:** `build_grodzka_gate()` $\rightarrow$ `public/models/gate_grodzka.glb`.

#### 8. Castle Archery & Training Yard
- **ID:** `bldg_castle_archery_yard`
- **Location:** Northern bailey of Castle Hill.
- **Dimensions:** $14.0\text{m (W)} \times 22.0\text{m (D)} \times 4.2\text{m (H)}$.
- **Architectural Motifs:** Split-rail timber boundary fence; open timber lean-to barracks shed; sand practice lane.
- **Exterior Workspace / Station:** 3 circular coiled straw archery targets on wooden tripods at 10m, 15m, and 20m; vertical weapon rack with crossbows and spears; padded spinning quintain dummy.
- **Associated Workers:** `worker_master_at_arms`, `worker_guard_crossbow`.
- **Blender Generator:** `build_archery_yard()` $\rightarrow$ `public/models/archery_yard.glb`.

---

### Industrial & Resource Production Complexes

#### 9. Riverside Watermill (*Młyn Wodny*)
- **ID:** `bldg_riverside_watermill`
- **Location:** Czechówka riverbank adjacent to Grodzka bridge.
- **Dimensions:** $9.0\text{m (W)} \times 12.0\text{m (D)} \times 8.5\text{m (H)}$.
- **Stories:** 2 stories (timber structure built on heavy oak stilts driven into the riverbed).
- **Architectural Motifs:** Interlocking dark pine log walls; weatherboard upper gable; steep straw thatch roof with mossy eaves; wooden mill race flume.
- **Exterior Workspace / Station:** 
  - **Undershot Waterwheel:** 12-paddle wooden wheel ($4.2\text{m}$ diameter, $1.2\text{m}$ wide) continuously rotating at $0.8\text{ rad/s}$ with foaming water splash particles.
  - **Quayside Pier:** Heavy timber deck loaded with stacked burlap flour sacks, wooden grain bins, and two-wheeled hand barrows.
- **Associated Workers:** `worker_miller_master`, `worker_flour_porter`.
- **Blender Generator:** `build_watermill()` $\rightarrow$ `public/models/watermill.glb`.

#### 10. Hilltop Post Windmill (*Wiatrak Koźlak*)
- **ID:** `bldg_post_windmill`
- **Location:** Prominent elevated loess knoll west of Kraków Gate.
- **Dimensions:** $6.5\text{m (W)} \times 6.5\text{m (D)} \times 13.0\text{m (H to Hub)}$; sail span $= 16.0\text{m}$.
- **Stories:** 3 interior mill lofts rotating on a central oak post (*kozioł*).
- **Architectural Motifs:** Vertical weathered pine weatherboarding; gabled timber cap; massive diagonal tail-pole (*dyszel*) touching the ground to orient the mill into the wind; ladder access stair.
- **Exterior Workspace / Station:** 
  - **4-Blade Canvas Sails:** Rotating continuously at $0.4\text{ rad/s}$.
  - **Grain Staging Yard:** Split-rail fenced paddock with horse-drawn grain wagon, grain sacks, and stone boundary markers.
- **Associated Workers:** `worker_windmiller`.
- **Blender Generator:** `build_windmill()` $\rightarrow$ `public/models/windmill.glb`.

#### 11. Stepped Limestone Quarry & Stonemasons' Yard
- **ID:** `bldg_limestone_quarry`
- **Location:** Southern loess cliff outcrop overlooking Bystrzyca valley.
- **Dimensions:** $24.0\text{m (W)} \times 28.0\text{m (D)} \times 9.0\text{m (Pit Depth)}$.
- **Stories:** 3 terraced excavation rock ledges.
- **Architectural Motifs:** Jagged stepped limestone rock walls; chisel scar channels; rock rubble talus mounds.
- **Exterior Workspace / Station:** 
  - **Timber Derrick / Jib Crane:** Heavy timber A-frame with stone counterweight box, rope pulley tackle, and suspended limestone ashlar block.
  - **Masons' Trestles:** Outdoor wooden benches with stone mallets, iron chisels, and rows of finished square building blocks.
- **Associated Workers:** `worker_quarryman_hewer`, `worker_stonemason`.
- **Blender Generator:** `build_stone_quarry()` $\rightarrow$ `public/models/stone_quarry.glb`.

#### 12. Logging Camp & Pit Sawmill (*Trak Ciesielski*)
- **ID:** `bldg_logging_camp_sawmill`
- **Location:** Northern wooded slope outside the defensive perimeter.
- **Dimensions:** $18.0\text{m (W)} \times 22.0\text{m (D)} \times 5.5\text{m (H)}$.
- **Architectural Motifs:** Open-sided timber post-and-beam drying shed; woodcutters' log bunkhouse with bark-shingle roof.
- **Exterior Workspace / Station:** 
  - **Two-Man Pit-Saw Trestle (*Trak*):** Elevated wooden framework ($1.8\text{m}$ high) where top sawyer and pit sawyer cut logs into structural planks over a pile of yellow sawdust.
  - **Log Ricks:** 3 massive stacks of peeled pine tree trunks ($6\text{m}$ long) braced with vertical oak stakes.
  - Chopping blocks with embedded felling axes, sawbucks, and horse-drawn log skids.
- **Associated Workers:** `worker_woodcutter`, `worker_pit_sawyer`.
- **Blender Generator:** `build_logging_camp()` $\rightarrow$ `public/models/logging_camp.glb`.

#### 13. Riverside Harbor Wharves & Trade Basin
- **ID:** `bldg_river_harbor_wharf`
- **Location:** Bystrzyca river basin landing.
- **Dimensions:** $28.0\text{m (W)} \times 16.0\text{m (D)} \times 9.0\text{m (H)}$.
- **Architectural Motifs:** Oak boardwalk wharves on stilts; timber retaining bulkhead; open customs lean-to shed.
- **Exterior Workspace / Station:** 
  - **Treadwheel Harbor Crane:** Cylindrical shingled wooden housing with projecting crane arm and rope sling.
  - **Moored River Cog:** $14\text{m}$ wooden clinker-built merchant cog with single mast, yardarm, and high sterncastle moored to oak bollards.
  - Cargo piles: Herring and wine barrels, grain sacks, bundles of iron bars, drying fish racks.
- **Associated Workers:** `worker_harbor_master`, `worker_harbor_stevedore`, `worker_cog_captain`.
- **Blender Generator:** `build_river_harbor()` $\rightarrow$ `public/models/river_harbor.glb`.

#### 14. Blacksmith's Workshop & Open Forge Yard
- **ID:** `bldg_blacksmith_workshop`
- **Location:** Suburb or Grodzka craft quarter.
- **Dimensions:** $8.4\text{m (W)} \times 11.2\text{m (D)} \times 8.6\text{m (H)}$.
- **Stories:** 2 stories (ground floor workshop + upper artisan living quarters).
- **Architectural Motifs:** Stone foundation plinth; heavy timber-frame walls with red brick infill; half-hipped wooden shingle roof; brick chimney stack with soot stains.
- **Exterior Workspace / Station:** 
  - **Open Lean-to Forge Canopy:** Projecting timber shed protecting an outdoor masonry furnace with glowing embers (pulsating `#ff6611` light emitter).
  - Heavy cast iron anvil mounted on an oak tree trunk stump.
  - Oak water-quenching trough with steam decal trigger.
  - Timber weapon rack holding forged halberd blades, axe heads, and horseshoe billets.
- **Associated Workers:** `worker_blacksmith_master`, `worker_blacksmith_apprentice`.
- **Blender Generator:** `build_blacksmith_workshop()` $\rightarrow$ `public/models/blacksmith_workshop.glb`.

---

### Artisan Guild Workshops

#### 15. Baker's House & Masonry Oven (*Piekarnia*)
- **ID:** `bldg_baker_house`
- **Location:** Rynek or craft quarter street frontage (`(-40, 0, 15)`).
- **Dimensions:** $7.5\text{m (W)} \times 10.5\text{m (D)} \times 7.8\text{m (H)}$.
- **Stories:** 2 stories (ground floor bakery and retail window + upper residential quarters).
- **Architectural Motifs:** Sturdy limestone plinth base; cream lime plaster and dark timber-frame upper story; high-pitched $52^\circ$ red clay pantile roof; front facade features an arched wooden customer window with fold-down display shelf for fresh sourdough loaves; hanging guild sign: *Gilded Pretzel on Forged Iron Scrollwork*.
- **Exterior Workspace / Station (Flank Yard):** 
  - **Outdoor Domed Bread Oven:** $3.2\text{m} \times 3.5\text{m}$ limestone foundation supporting a semi-spherical red-brick baking dome with arched stokehole emitting warm orange glow (`#ff6611`); $4.2\text{m}$ high soot-stained masonry chimney stack.
  - **Timber Lean-To Canopy:** Open post-and-beam protective cedar shelter shielding the oven from rain.
  - **Equipment & Props:** Long ash wood bread peel shovel leaning against wall; $1.8\text{m} \times 1.2\text{m}$ stacked cords of split birch firewood; 3 stacked burlap sacks of stone-ground rye and wheat flour (`#C7BD9C`).
- **Associated Workers:** `worker_master_baker` (white linen tunic, canvas apron, holding bread peel shovel, sliding loaves into oven).
- **Blender Generator:** `build_baker_house()` $\rightarrow$ `public/models/house_baker.glb`.
- **Reference Image:** `reference_photos/baker_house.jpg`.

#### 16. Brewer's Malthouse & Cask Yard (*Browar*)
- **ID:** `bldg_brewer_malthouse`
- **Location:** Artisan & Brewery Quarter (`(-85, 0, -35)`).
- **Dimensions:** $9.5\text{m (W)} \times 14.0\text{m (D)} \times 9.2\text{m (H)}$.
- **Stories:** 2 stories + ventilated drying attic.
- **Architectural Motifs:** Massive Gothic red-brick ground floor ($0.6\text{m}$ walls) with arched wagon portal; timber-frame upper story fitted with horizontal wooden louvers (*żaluzje słodowe*) to vent warm moisture during barley germination and malt drying; weathered oak shingle roof; hanging guild sign: *Polished Copper Mash Paddle & Tankard*.
- **Exterior Workspace / Station (Cask Yard):**
  - **Barrel-Washing Station:** 2 heavy wooden soaking troughs ($3.6\text{m} \times 1.4\text{m}$) with oak spigots and stone drainage channel.
  - **Pyramid Cask Stack:** 6 oak beer barrels with wrought iron hoops stacked in a 3-2-1 pyramid ($2.3\text{m}$ high).
  - **Outdoor Tavern Hospitality:** 2 heavy oak trestle tables with matching benches where townsfolk gather to sample spiced ale and rye beer.
  - **Coopering Bench:** Low oak shaving horse with curved drawknives and spare iron hoops.
- **Associated Workers:** `worker_master_brewer` (leather bib apron, stirring boiling mash with copper paddle), `worker_cooper` (shaving staves on bench).
- **Blender Generator:** `build_brewer_malthouse()` $\rightarrow$ `public/models/house_brewer.glb`.
- **Reference Image:** `reference_photos/brewer_malthouse.jpg`.

#### 17. Tanner's Riverside Workshop (*Garbarnia*)
- **ID:** `bldg_tanner_workshop`
- **Location:** Downstream Czechówka riverbank (`(120, 0, -85)`).
- **Dimensions:** $8.0\text{m (W)} \times 12.5\text{m (D)} \times 7.5\text{m (H)}$.
- **Stories:** 1.5 stories (low timber log ground workshop + open slatted hide-drying loft).
- **Architectural Motifs:** Dark weathered pine timber logs with moss chinking; open-sided upper drying gallery allowing river breezes to cure hides without direct sunlight; sagging sun-bleached straw thatch roof with mossy eaves; hanging guild sign: *Stretched Tawny Ox Hide*.
- **Exterior Workspace / Station (Tanning Yard):**
  - **Sunken Tanning Vats:** 4 rectangular wooden vats ($2.4\text{m} \times 1.8\text{m}$) dug into the riverbank ground, filled with dark brown oak-bark tannin liquor (`#38291f`).
  - **Vertical Hide Drying Frames:** 2 tall wooden timber trestle frames ($3.2\text{m}$ high) with rawhide thongs stretching cow and deer pelts to dry.
  - **Fleshing Station:** Low tilted wooden fleshing beam (*stół kuśnierski*) with two-handled curved scraper knife for removing fat and hair.
  - **Pelt Stacks:** Neatly bound stacks of salted raw skins and cured leather hides awaiting transport to cobblers.
- **Associated Workers:** `worker_master_tanner` (waterproof oiled rawhide apron, scraping pelts on fleshing beam).
- **Blender Generator:** `build_tanner_workshop()` $\rightarrow$ `public/models/house_tanner.glb`.
- **Reference Image:** `reference_photos/tanner_workshop.jpg`.

#### 18. Potter's Shed & Kiln Yard (*Garncarnia*)
- **ID:** `bldg_potter_workshop`
- **Location:** Clay loam terrace outside Kraków Gate (`(-125, 0, 45)`).
- **Dimensions:** $7.2\text{m (W)} \times 9.8\text{m (D)} \times 6.8\text{m (H)}$.
- **Stories:** 1 story + thatched attic.
- **Architectural Motifs:** Rustic wattle-and-daub cottage with cream loam plaster and exposed corner posts; steep weathered thatch roof; hanging guild sign: *Terracotta Glazed Amphora*.
- **Exterior Workspace / Station (Kiln Yard):**
  - **Domed Updraft Pottery Kiln:** Circular red-brick firing kiln ($2.8\text{m}$ diameter, $3.2\text{m}$ high) with stone base, arched stokehole glowing with orange firing embers (`#ff5500`), and tall square stone flue chimney ($4.0\text{m}$ high) emitting faint heat haze.
  - **Potter's Kick-Wheel Table:** Outdoor wooden potting bench with foot-operated flywheel, water pot, and wooden shaping ribs.
  - **Tiered Drying Racks:** 3-tier open timber shelving unit ($3.6\text{m}$ long) displaying rows of terracotta clay jugs, amphorae, cooking pots, and scalloped roof ridge tiles.
  - **Clay Staging:** Mounds of grey river clay wrapped in damp burlap beside split pine firewood stacks.
- **Associated Workers:** `worker_master_potter` (clay-stained smock, throwing pots on kick-wheel).
- **Blender Generator:** `build_potter_workshop()` $\rightarrow$ `public/models/house_potter.glb`.
- **Reference Image:** `reference_photos/potter_workshop.jpg`.

#### 19. Weaver's Half-Timber Workshop (*Warsztat Tkacki*)
- **ID:** `bldg_weaver_workshop`
- **Location:** Bramowa textile quarter (`(-30, 0, -45)`).
- **Dimensions:** $8.0\text{m (W)} \times 11.0\text{m (D)} \times 8.2\text{m (H)}$.
- **Stories:** 2 stories + high attic loom loft.
- **Architectural Motifs:** Elaborate half-timbered facade with diagonal St. Andrew's cross braces (*krzyże św. Andrzeja*) and white lime plaster daub; high $52^\circ$ red tile gable roof; projecting attic dormer with wooden hoist beam, rope pulley, and burlap wool bale; hanging guild sign: *Carved Weaving Shuttle & Spindle*.
- **Exterior Workspace / Station (Clothiers & Dye Yard):**
  - **Circular Stone Dyeing Vats:** 2 masonry dye cauldrons ($1.8\text{m}$ diameter) set in limestone rims, filled with steaming liquid dyes (one deep indigo blue `#2e4085`, one rich madder scarlet `#962828`).
  - **Drying Rail Framework:** Long horizontal oak poles ($4.8\text{m}$ long) where vibrant dyed lengths of wool and linen broadcloth hang waving in the breeze.
  - **Yarn Warping Frame:** Outdoor vertical wooden peg frame for measuring and winding warp threads.
  - **Clothier's Handcart:** Wooden two-wheeled cart loaded with rolled bolts of finished woven broadcloth.
- **Associated Workers:** `worker_master_weaver` (burgher cotte, holding polished shuttle, inspecting dyed cloth).
- **Blender Generator:** `build_weaver_workshop()` $\rightarrow$ `public/models/house_weaver.glb`.
- **Reference Image:** `reference_photos/weaver_workshop.jpg`.

---

### Vernacular & Residential Housing

#### 20. Patrician Stepped Brick Kamienica
- **ID:** `bldg_patrician_brick_kamienica`
- **Dimensions:** $9.0\text{m (W)} \times 14.0\text{m (D)} \times 15.5\text{m (H)}$.
- **Stories:** 3 stories + high attic.
- **Architectural Motifs:** Deep red Gothic brick facade; 5-tier crow-stepped gable crowned with white plaster pinnacles; arched stone entrance portal; vaulted cellar trapdoor on street pavement.
- **Backyard Doodads:** Enclosed stone courtyard with paved flagstones, ornamental flower planter, small carriage shed, and stone wellhead.
- **Associated Workers:** `worker_patrician_merchant`.
- **Blender Generator:** `build_house_patrician_brick()` $\rightarrow$ `public/models/house_patrician_brick.glb`.

#### 21. Merchant Half-Timbered Jettied Tenement (*Kamienica Szachulcowa*)
- **ID:** `bldg_half_timber_jettied_house`
- **Dimensions:** $8.0\text{m (W)} \times 12.0\text{m (D)} \times 13.5\text{m (H)}$.
- **Stories:** 3 stories (2 overhanging jetty levels with carved wooden corbels).
- **Architectural Motifs:** Dark oak framing beams with cream lime plaster infill; steep clay pantile roof with gabled dormer; ground-floor fold-down timber shop shutters.
- **Backyard Doodads:** Split-rail fence, firewood rick stacked against wall, rain barrel under downspout, wooden handcart.
- **Associated Workers:** `worker_burgher_guildsman`, `worker_housewife`.
- **Blender Generator:** `build_house_half_timber()` $\rightarrow$ `public/models/house_half_timber.glb`.

#### 22. Rural Interlocking Log Cottage (*Dom Zrębowy*)
- **ID:** `bldg_rural_thatched_log_cabin`
- **Dimensions:** $6.5\text{m (W)} \times 8.5\text{m (D)} \times 6.2\text{m (H)}$.
- **Stories:** 1 story + thatched loft.
- **Architectural Motifs:** Dark weathered pine logs with corner saddle-notches and moss chinking; low overhanging eaves; thick straw thatch roof held by cross-timbers (*kozły*).
- **Backyard Doodads:** Rustic wattle hurdle fence enclosing a vegetable plot with cabbage rows, firewood cord, wicker chicken coop.
- **Associated Workers:** `worker_peasant_farmer`.
- **Blender Generator:** `build_house_timber_log()` $\rightarrow$ `public/models/house_timber_log.glb`.

---

## 3. Living Guild Workers & Artisans

All 18 worker archetypes are modeled at $1.75\text{m}$ scale with distinct 14th-century costumes, held tool props, and looped outdoor animations.

```
+------------------------------------------------------------------------------------------------------------------+
|                                    WORKER ROSTER: ATTIRE, PROPS & ACTIVITIES                                      |
+----+----------------------------+-----------------------+------------------------+-------------------------------+
| #  | Worker Archetype ID        | Costume & Palette     | Held Tool Props        | Looped Outdoor Activity       |
+----+----------------------------+-----------------------+------------------------+-------------------------------+
| 1  | worker_blacksmith_master   | Leather apron, coif   | Cross-peen hammer      | Hammering iron on anvil       |
| 2  | worker_blacksmith_striker  | Barehead, rolled cotte| Heavy sledgehammer     | 2-handed overhead anvil smash |
| 3  | worker_woodcutter          | Dark wool hose, hood  | Double-bit broad axe   | Chopping fallen tree trunk    |
| 4  | worker_pit_sawyer          | Linen shirt, trousers | Two-man pit saw handle | Rhythmic pushing/pulling saw  |
| 5  | worker_quarryman_hewer     | Rough tunic, gloves   | Heavy iron pickaxe     | Hewing limestone rock face    |
| 6  | worker_stonemason          | Leather belt, pouch   | Stone mallet & chisel  | Dressing square ashlar block  |
| 7  | worker_miller_master       | Flour-dusted apron    | Wooden flour scoop     | Inspecting grain hopper       |
| 8  | worker_flour_porter        | Burlap head-cowl      | 50kg grain sack        | Carrying sack from mill dock  |
| 9  | worker_windmiller          | Woolen cap, smock     | Rope winch crank       | Adjusting sail lattice        |
| 10 | worker_master_baker        | White linen tunic     | Long wooden bread peel | Sliding sourdough into oven   |
| 11 | worker_master_brewer       | Stained leather apron | Copper mash paddle     | Stirring boiling brew cauldron|
| 12 | worker_cooper              | Work smock, tool belt | Curved drawknife       | Shaving barrel staves on bench|
| 13 | worker_master_tanner       | Thick waterproof hide | Fleshing curved knife  | Scraping hair off stretched skin|
| 14 | worker_master_potter       | Clay-spattered tunic  | Wooden shaping rib     | Shaping wet amphora on wheel  |
| 15 | worker_master_weaver       | Burgher tunic, shoes  | Threaded loom shuttle  | Passing shuttle through warp  |
| 16 | worker_monk_gardener       | Brown cowl & cord     | Timber garden hoe      | Tending lavender & sage beds  |
| 17 | worker_guard_crossbow      | Sallet helm, gambeson | Cocked iron crossbow   | Alert scanning patrol step    |
| 18 | worker_farmer_scyther      | Straw hat, loose linen| Curved harvest scythe  | Broad sweeping harvest stroke |
+----+----------------------------+-----------------------+------------------------+-------------------------------+
```

### Detailed Worker Profiles (Examples)

#### `worker_blacksmith_master`
- **Associated Building:** `bldg_blacksmith_workshop`
- **Attire:** Dark brown leather apron (`#2a1e14`) over an unbleached linen tunic (`#DFDBD2`), charcoal hose (`#26262B`), off-white linen coif tied under the chin, heavy heat-resistant leather gloves.
- **Props:** Right hand: Iron cross-peen hammer; Left hand: Forged blacksmith tongs holding an orange-hot iron billet.
- **Station Offset:** $(X: +2.8\text{m}, Z: -1.2\text{m})$ relative to workshop origin (facing anvil).
- **Animation Cycle (5.7s):**
  - $0.0\text{s} - 3.2\text{s}$: 3 rhythmic hammer strikes onto anvil with synchronized spark particle trigger.
  - $3.2\text{s} - 4.5\text{s}$: Lifts billet, inspects alignment against light.
  - $4.5\text{s} - 5.7\text{s}$: Plunges iron into water trough with steam puff trigger.

#### `worker_farmer_scyther`
- **Associated Building:** `bldg_rural_thatched_log_cabin` / Wheat Fields
- **Attire:** Wide-brimmed woven straw hat (`#9E8656`), loose natural linen shirt with unbuttoned collar, rolled-up trousers, bare feet or simple rawhide moccasins.
- **Props:** Two-handed bent ash snath with curved steel harvest scythe blade.
- **Station Offset:** Located along the wheat field swaths outside Kraków Gate.
- **Animation Cycle (4.2s):**
  - Smooth $120^\circ$ torso rotation swinging scythe through wheat stalks at ground level, stepping forward half a pace, resetting posture.

#### `worker_monk_gardener`
- **Associated Building:** `bldg_monastery_cloister`
- **Attire:** Dominican rough woolen habit (white tunic under dark brown hooded scapular), knotted white rope cincture cord at waist, leather sandals.
- **Props:** Right hand: Small wooden hand-hoe; Left hand: Wicker harvest basket.
- **Station Offset:** Inside the cloister garden beside the sage and lavender raised beds.
- **Animation Cycle (6.0s):**
  - Kneels beside raised wooden planter, hoes soil between plant stems, places trimmed herb cuttings into basket, stands and inspects bed.

---

## 4. Procedural Blender Python (`bmesh`) Construction Recipes

All models are compiled via `build_assets.py` using pure mathematical `bmesh` geometry primitives without external DCC dependencies.

### Reusable Macro Primitives

#### Stepped Gable Generator (*Szczyt Schodkowy*)
```python
def add_stepped_gable(bm, cx, cy, base_z, width, depth, step_count, step_height, mat_wall, mat_pin):
    """Constructs an authentic Central European Brick Gothic crow-stepped gable with pinnacles."""
    for s in range(step_count):
        step_w = width * (1.0 - (s / step_count))
        step_z = base_z + s * step_height
        # Step masonry box
        add_box(bm, cx, cy, step_z + step_height * 0.5, step_w, depth, step_height, mat_idx=mat_wall)
        # White plaster pinnacles on left and right step ends
        for sx in [-step_w * 0.5 + 0.25, step_w * 0.5 - 0.25]:
            add_box(bm, cx + sx, cy, step_z + step_height + 0.4, 0.4, depth + 0.1, 0.8, mat_idx=mat_pin)
```

#### Cantilevered Jetty Overhang Generator (*Nadwieszenie Szachulcowe*)
```python
def add_jetty_overhang(bm, cx, cy, base_z, w, d, h, overhang_dist, mat_plaster, mat_timber):
    """Constructs a jettied second floor projecting forward with carved wooden support corbels."""
    # Main cantilevered box
    add_box(bm, cx, cy - overhang_dist * 0.5, base_z + h * 0.5, w, d + overhang_dist, h, mat_idx=mat_plaster)
    # Exposed timber framing (corner posts & horizontal sill plate)
    for px in [-w * 0.5 + 0.1, w * 0.5 - 0.1]:
        add_box(bm, cx + px, cy - overhang_dist * 0.5, base_z + h * 0.5, 0.2, d + overhang_dist, h, mat_idx=mat_timber)
    # Carved wooden corbels under the overhang
    corbel_spacing = w / 4.0
    for i in range(5):
        kx = -w * 0.5 + i * corbel_spacing
        add_box(bm, cx + kx, cy - overhang_dist - 0.15, base_z - 0.3, 0.25, 0.45, 0.6, mat_idx=mat_timber)
```

#### Undershot Mill Waterwheel Generator
```python
def add_waterwheel(bm, cx, cy, cz, radius, width, paddle_count, mat_wood, mat_iron):
    """Constructs an authentic 14th-century wooden mill waterwheel with hub, spokes, and paddles."""
    # Central oak axle and iron collar
    add_cylinder(bm, cx, cy, cz, radius=0.35, length=width + 0.4, axis='X', mat_idx=mat_wood)
    # Wheel rims and radiating spokes
    for side in [-width * 0.5, width * 0.5]:
        for p in range(paddle_count):
            angle = (p / paddle_count) * math.pi * 2
            dx = 0
            dy = math.cos(angle) * (radius * 0.5)
            dz = math.sin(angle) * (radius * 0.5)
            # Spoke strut
            add_box_oriented(bm, cx + side, cy + dy, cz + dz, 0.12, radius, 0.12, rot_x=angle, mat_idx=mat_wood)
    # Flat wooden paddles around perimeter
    for p in range(paddle_count):
        angle = (p / paddle_count) * math.pi * 2
        py = math.cos(angle) * radius
        pz = math.sin(angle) * radius
        add_box_oriented(bm, cx, cy + py, cz + pz, width, 0.08, 0.65, rot_x=angle, mat_idx=mat_wood)
```

---

## 5. Procedural Texture Atlas UV Map Coordinates

To ensure zero texture-switching draw calls, all 22 buildings and 18 workers sample from a single shared $2048 \times 2048$ texture atlas divided into an $8 \times 8$ tile matrix ($256 \times 256\text{px}$ per sub-tile, or $512 \times 512\text{px}$ for primary materials):

```
+-------------------------------------------------------------------------------+
|                      TEXTURE ATLAS UV QUADRANT ALLOCATION                     |
+-------------------+-------------------+-------------------+-------------------+
| Tile [0,0] (U: 0.0-0.25, V: 0.75-1.0) | Tile [1,0] (U: 0.25-0.5, V: 0.75-1.0) |
| Polish Gothic Red Brick (Mortar Bond) | Interlocking Dark Pine Logs & Chinking|
+---------------------------------------+---------------------------------------+
| Tile [0,1] (U: 0.0-0.25, V: 0.50-0.75)| Tile [1,1] (U: 0.25-0.5, V: 0.50-0.75)|
| Half-Timber Oak & Lime Plaster Daub   | Red Clay Scalloped Pantile Shingles   |
+---------------------------------------+---------------------------------------+
| Tile [0,2] (U: 0.0-0.25, V: 0.25-0.50)| Tile [1,2] (U: 0.25-0.5, V: 0.25-0.50)|
| Fibrous Layered Sun-Bleached Thatch   | Loess Limestone Ashlar Masonry        |
+---------------------------------------+---------------------------------------+
| Tile [0,3] (U: 0.0-0.25, V: 0.00-0.25)| Tile [1,3] (U: 0.25-0.5, V: 0.00-0.25)|
| Weathered Pine Shakes & Door Planks   | Worker Costumes, Aprons & Leather     |
+---------------------------------------+---------------------------------------+
```

Procedural mesh generators assign normalized UV coordinates mapping directly to these texture quadrants, guaranteeing razor-sharp pixel clarity and zero texture swimming under orthographic camera projection.
