# Comprehensive Improvement Plan: Medieval Buildings, Workshops & Workers
## Lublin Anno Domini 1392 — Visual & Procedural 3D Asset Evolution

### Executive Summary
Based on in-depth analysis of the 14th-century Central European concept art, historical reference photos, and the current codebase, this plan outlines the complete procedural differentiation, visual improvement, and engine integration for all 22 building archetypes and 18 worker roles.

Previously, specialized craft workshops (baker, tanner, brewer, potter, weaver, blacksmith) and industrial production sites (watermill, windmill, quarry, sawmill, harbor) reused generic residential houses (`house_half_timber`, `house_patrician_brick`, `house_timber_log`). Under this plan:
1. **Every building archetype receives a dedicated, visually distinct 3D procedural model** authored via Blender Python (`bpy` + `bmesh`) with authentic architectural features, exterior production workspaces, and animated props.
2. **Existing models are substantially improved** with authentic historical details: stepped crow-gables with pinnacles, cantilevered jetties with carved corbel brackets, ground-floor fold-down timber shutters, corner saddle-notches on log cabins, and detailed chimney masonry.
3. **The Master Markdown Catalog (`BUILDINGS_AND_WORKERS_CATALOG.md`) and JSON specification** are updated with distinct physical dimensions, story counts, visible outdoor equipment, and worker station offsets.
4. **All 3D assets are compiled to a single dedicated folder (`public/models/*.glb`)** ready for the Three.js isometric rendering engine.
5. **High-fidelity isometric reference photos** are generated and committed to `reference_photos/`.

---

## 1. Visual & Architectural Differentiation Matrix

The following table details the distinct visual signature, outdoor equipment, and historical worker pairing for each of the 22 archetypes:

| # | Archetype ID | Building Type | Architectural Motifs & Materials | Exterior Workspace & Props | Associated Worker & Activity |
|---|---|---|---|---|---|
| **1** | `bldg_town_hall_ratusz` | Old Town Hall | Gothic red brick, white plaster blind arcades (*blendówki*), 4 octagonal corner bartizans with copper spires, western crow-stepped gable, clock belfry | Grand two-flight external stone staircase with carved limestone balustrades; pillory (*pręgierz*) | `worker_burgomaster` & `worker_town_scribe`: presiding over market council |
| **2** | `bldg_szmatruz_cloth_hall` | Cloth Hall | Double row of 22 brick pillars, covered central market arcade, red pantile double pitch roof, attic cargo hatch | 16 open timber stall booths with trestle display counters loaded with broadcloth bolts, linen rolls, and bread loaves | `worker_draper_merchant` & `worker_bread_seller`: unrolling cloth bolts and selling loaves |
| **3** | `bldg_parish_church_fara` | Parish Church | Soaring nave, stepped Gothic brick buttresses with limestone weatherings, 46m western belfry tower with copper needle spire | Arched limestone portal porch, stone holy water stoup, wooden parish notice board, cemetery cross courtyard | `worker_parish_priest` & `worker_sexton_bellringer`: swinging censor and tolling bell |
| **4** | `bldg_monastery_cloister` | Dominican Cloister | Enclosed 4-sided brick quadrangle with pointed arched open cloister walks surrounding an inner quad | Geometric raised timber herb beds with lavender, sage, and chamomile; central carved stone fountain basin | `worker_monk_gardener` & `worker_monk_apothecary`: tending raised herb beds with hand-hoe |
| **5** | `bldg_castle_donjon` | Royal Keep / Bailey | Massive cylindrical limestone ashlar masonry (14m dia.), upper defensive brick tier with machicolations, conical roof | Timber draw-stair platform, bailey guardhouse with glowing fire brazier, outer curtain wall connection | `worker_royal_castellan` & `worker_castle_guard`: inspecting bailey defenses |
| **6** | `bldg_krakow_gate` | Kraków Gate | 4-tier gateway tower, square base transitioning to octagonal brick belfry, copper spire, stone carriage portal | Heavy iron portcullis slot, outer timber drawbridge over dry moat, wooden gatekeeper hoarding gallery | `worker_gate_captain` & `worker_guard_crossbow`: raising portcullis and inspecting wagons |
| **7** | `bldg_grodzka_gate` | Grodzka Gate | 3-tier rectangular brick gateway tower, hipped pantile roof, projecting machicolated parapet | Octagonal wooden royal toll-collector booth with balance scale, ledger desk, and iron tax box | `worker_royal_toll_collector` & `worker_city_bailiff`: collecting transit duty |
| **8** | `bldg_castle_archery_yard` | Archery Training Yard | Split-rail perimeter timber fence, open timber lean-to barracks shed, sand practice lane | 3 coiled straw archery targets on tripods at 10m/15m/20m; spinning quintain dummy; vertical crossbow rack | `worker_master_at_arms` & `worker_guard_crossbow`: cocking crossbow and shooting at targets |
| **9** | `bldg_riverside_watermill` | River Watermill | Timber structure on heavy oak stilts driven into riverbed, weatherboard upper story, mossy thatch roof | 12-paddle wooden undershot waterwheel (4.2m dia.), timber flume race, quayside pier with stacked burlap flour sacks and barrow | `worker_miller_master` & `worker_flour_porter`: inspecting hopper and carrying sacks to dock |
| **10** | `bldg_post_windmill` | Post Windmill (*Koźlak*) | Vertical weathered pine cladding rotating on heavy oak post (*kozioł*), gabled cap, access ladder | 4-blade canvas sails rotating in wind, massive diagonal tail-pole (*dyszel*) touching ground, grain staging wagon | `worker_windmiller`: adjusting canvas reefing on sails |
| **11** | `bldg_limestone_quarry` | Stepped Quarry Yard | Terraced limestone rock ledges with chisel scar channels and rock talus piles | Heavy timber A-frame jib crane derrick with stone counterweight box, masons' chisel trestles, rows of dressed square ashlar | `worker_quarryman_hewer` & `worker_stonemason`: hewing rock face and dressing blocks |
| **12** | `bldg_logging_camp_sawmill` | Sawmill & Logging Camp | Open-sided timber post-and-beam drying shelter, log bunkhouse with bark-shingle roof | Two-man pit-saw trestle (*trak*) over yellow sawdust pile, 3 peeled pine log ricks with vertical braces, chopping stumps | `worker_woodcutter` & `worker_pit_sawyer`: rhythmic two-man sawing of structural planks |
| **13** | `bldg_river_harbor_wharf` | River Harbor Wharves | Oak boardwalk wharves on stilts, timber retaining bulkhead, open customs lean-to shed | Moored 14m clinker-built wooden river cog, cylindrical treadwheel crane, stacks of wine/herring barrels and rope coils | `worker_harbor_master` & `worker_harbor_stevedore`: checking manifests and hoisting cargo |
| **14** | `bldg_blacksmith_workshop` | Blacksmith Forge | 2 stories: stone plinth with half-timber upper quarters, half-hipped shingle roof, tall soot-stained chimney | Projecting timber lean-to canopy sheltering masonry hearth with glowing orange coals; iron anvil on oak stump; water quench trough | `worker_blacksmith_master` & `worker_blacksmith_apprentice`: hammering glowing billet and quenching |
| **15** | `bldg_baker_house` | Baker's Bakery | Half-timbered frame with white plaster infill, steep clay pantile roof, hanging gilded pretzel sign | Domed outdoor brick baking oven built into wall under timber shelter, stacked split birch firewood cords, sacks of flour, bread peel | `worker_master_baker`: sliding sourdough bread loaves into oven on long peel |
| **16** | `bldg_brewer_malthouse` | Brewer's Malthouse | Sturdy brick ground floor, upper half-timber story with wooden ventilation louvers, copper mash paddle sign | Outdoor cask-washing yard with wooden soak troughs, pyramid of oak beer barrels, outdoor tavern drinking tables and benches | `worker_master_brewer` & `worker_cooper`: stirring mash paddle and driving iron cask hoops |
| **17** | `bldg_tanner_workshop` | Tanner's River Workshop | Open-sided timber drying galleries, steep thatch roof, hanging stretched ox hide sign | 4 sunken rectangular outdoor tanning vats with dark tannin liquor, wooden vertical stretching frames with pelts, fleshing beam | `worker_master_tanner`: scraping animal hair on fleshing beam with drawknife |
| **18** | `bldg_potter_workshop` | Potter's Kiln Yard | Rustic wattle-and-daub walls with loam plaster, thatch roof, hanging glazed amphora sign | Domed red-brick pottery kiln with arched stokehole and stone chimney, tiered outdoor display shelves with clay pots/jugs, kick-wheel | `worker_master_potter`: shaping clay amphora on foot-powered kick-wheel |
| **19** | `bldg_weaver_workshop` | Weaver's Clothier Hall | Half-timbered facade with St. Andrew's diagonal cross braces, attic dormer with hoist beam, shuttle sign | Outdoor horizontal yarn-stretching racks, steaming wooden dye vats with draped scarlet and indigo linen cloth on rails | `worker_master_weaver`: passing shuttle through loom and inspecting dyed fabrics |
| **20** | `bldg_patrician_brick_kamienica` | Patrician Brick Kamienica | Deep red Gothic brick facade, 5-tier crow-stepped gable crowned with white plaster pinnacles, arched portal | Vaulted cellar trapdoor on street pavement; enclosed rear stone courtyard with flagstones, garden planter, and wellhead | `worker_patrician_merchant`: managing trade ledgers and inspecting cargo |
| **21** | `bldg_half_timber_jettied_house` | Burgher Jettied House | 3 stories with 2 projecting cantilevered jetties, carved wooden corbel brackets, pantile roof with dormer | Ground-floor fold-down timber shop counter shutters, firewood rick stacked against wall, rain barrel under downspout | `worker_burgher_guildsman` & `worker_housewife`: tending shop window counter |
| **22** | `bldg_rural_thatched_log_cabin` | Peasant Log Cottage | Dark pine logs with corner saddle-notches, thick straw thatch roof with cross-timbers (*kozły*), small shutters | Rustic wattle hurdle fence enclosing cabbage and turnip garden rows, firewood rick, wicker chicken coop | `worker_peasant_farmer`: tending garden patch and stacking firewood |

---

## 2. Procedural Blender Python Pipeline Architecture

### Unified Script Architecture (`build_assets.py`)
All models are procedurally synthesized using Blender 3.6 LTS in headless background mode:
```bash
/home/antigravity/blender/blender --background --python build_assets.py
```

### Material RNA Retention Pattern
To avoid `ReferenceError: StructRNA of type Material has been removed` when generating 30 models in sequence:
- Materials are created once in a global palette dictionary `get_materials()`.
- Between models, only scene objects and meshes are pruned via `clear_scene()`.
- Material references remain alive and are appended to the mesh before GLB export.

### Dedicated Model Export Table
Each building archetype corresponds 1:1 with an exported GLB file inside `public/models/`:
- `public/models/town_hall.glb`
- `public/models/szmatruz.glb`
- `public/models/church_gothic.glb`
- `public/models/monastery_cloister.glb`
- `public/models/castle_donjon.glb`
- `public/models/gate_krakow.glb`
- `public/models/gate_grodzka.glb`
- `public/models/archery_yard.glb`
- `public/models/watermill.glb`
- `public/models/windmill.glb`
- `public/models/stone_quarry.glb`
- `public/models/logging_camp.glb`
- `public/models/river_harbor.glb`
- `public/models/blacksmith_workshop.glb`
- `public/models/house_baker.glb`
- `public/models/house_brewer.glb`
- `public/models/house_tanner.glb`
- `public/models/house_potter.glb`
- `public/models/house_weaver.glb`
- `public/models/house_patrician_brick.glb`
- `public/models/house_half_timber.glb`
- `public/models/house_timber_log.glb`
- Plus infrastructure: `curtain_wall.glb`, `curtain_tower.glb`, `shed_timber.glb`, `town_well.glb`, `market_cart.glb`, `market_stall_*.glb`, `tree_oak.glb`.

---

## 3. Worker Attire, Equipment & Looped Outdoor Activities

Every worker archetype is modeled with historical 14th-century garments and assigned a specific exterior workstation with looped animations:

1. **`worker_master_baker`**: White linen tunic, canvas apron, linen coif. Holding a long wooden bread peel shovel. Looped activity: sliding sourdough loaves into the domed outdoor brick oven.
2. **`worker_master_tanner`**: Heavy waterproof oiled rawhide apron, thick leather armguards. Holding a two-handled curved fleshing knife. Looped activity: scraping hair and membrane off a hide draped over the wooden fleshing beam.
3. **`worker_master_brewer`**: Stained brown leather bib apron, woolen cap. Holding a long copper mash paddle. Looped activity: stirring malt mash in a cauldron and checking cask bung-holes.
4. **`worker_cooper`**: Canvas work smock, leather tool belt. Holding a curved drawknife. Looped activity: shaving barrel staves and hammering iron hoops around beer casks on a low wooden bench.
5. **`worker_blacksmith_master`**: Heavy leather smithing apron, rolled cotte sleeves, off-white coif, heat-resistant leather gloves. Holding cross-peen forging hammer and tongs holding glowing orange billet. Looped activity: rhythmic 3-strike hammer sequence on anvil followed by water quench.
6. **`worker_master_potter`**: Clay-stained linen smock, bare arms. Sitting at the outdoor wooden bench with foot-operated kick-wheel. Looped activity: spinning clay vessel, smoothing rim with wooden rib, placing finished amphora on drying rack.
7. **`worker_master_weaver`**: Fine wool burgher cotte, leather turnshoes. Holding a polished cherrywood weaving shuttle. Looped activity: passing shuttle through the warp threads on outdoor drying rack and checking dye vats.
8. **`worker_miller_master` & `worker_flour_porter`**: Flour-dusted apron and burlap head-cowl. Carrying 50kg grain sacks from the watermill quayside pier onto hand barrows.
9. **`worker_windmiller`**: Heavy woolen smock and peaked cap. Turning the hand winch on the tail-pole (*dyszel*) to orient the windmill into the prevailing wind.
10. **`worker_stonemason` & `worker_quarryman`**: Rough linen tunics, leather belts with tool holsters. Hewing limestone rock ledges with iron pickaxes and dressing square ashlar blocks with mallets and chisels beside the timber crane.
11. **`worker_pit_sawyer` & `worker_woodcutter`**: Woolen hose, hoods, leather wrist braces. Operating the two-man pit saw (*trak*) over the sawdust pit, cutting tree trunks into lumber planks.

---

## 4. Execution & Rollout Steps

1. **Phase 1: Procedural Asset Authoring (`build_assets.py`)**:
   - Write comprehensive mathematical `bmesh` builders for all 22 buildings.
   - Enhance existing models (`house_half_timber`, `house_patrician_brick`, `house_timber_log`, `town_hall`, `szmatruz`).
   - Implement new models (`house_baker`, `house_brewer`, `house_tanner`, `house_potter`, `house_weaver`, `blacksmith_workshop`, `watermill`, `windmill`, `stone_quarry`, `logging_camp`, `river_harbor`, `gate_krakow`, `gate_grodzka`, `monastery_cloister`, `archery_yard`).
2. **Phase 2: Blender Headless Compilation**:
   - Run Blender CLI to compile all 22+ models into `public/models/*.glb`.
   - Verify file existence and non-trivial file sizes (>8KB each).
3. **Phase 3: Catalog Synchronization**:
   - Update `BUILDINGS_AND_WORKERS_CATALOG.md` with differentiated descriptions, props, and worker stations.
   - Synchronize `buildings_and_workers_catalog.json`.
4. **Phase 4: Reference Photo Staging**:
   - Commit generated concept art reference photos into `reference_photos/`.
5. **Phase 5: Three.js Simulation Integration**:
   - Update `src/engine/three-renderer.ts` to load all newly generated GLB models.
   - Update parcel mapping so artisan and production parcels spawn their exact designated 3D model instead of generic houses.
   - Verify TypeScript compilation (`npm run build`).
6. **Phase 6: Git Commit**:
   - Commit all updated assets, scripts, catalog files, and reference photos to the repository.
