#!/usr/bin/env python3
"""
Medieval City Plan Generator: Lublin (Anno Domini 1392)
Outputs decoupled JSON Intermediate Representation (IR) containing:
- Topography & Promontory Perimeter (~8.8 hectares)
- Curtain Wall with 14 defensive towers & 2 fortified gates (Kraków Gate & Grodzka Gate)
- Castle Hill bailey (Romanesque Donjon keep, Gothic Royal Chapel, Palace Hall)
- Civic Core (Market Square, Old Town Hall, Szmatruz cloth hall)
- Kraków Suburb with timber yards & player's workshop
- 580 Parcels with 25 house types, 3 shed types, 18 hung trade signs, aging parameters
- 1,500 Living Autonomous Citizens across ~400 households with clockwork schedules
"""

import json
import math
import random
import os
import sys

# Seed for reproducible historical layout
random.seed(1392)

DISTRICTS = {
    "market_square": "Rynek (Market Square)",
    "bramowa_quarter": "Bramowa Quarter",
    "grodzka_quarter": "Grodzka Quarter",
    "dominican_quarter": "Dominican Friary Quarter",
    "fara_quarter": "St. Michael Parish Quarter",
    "north_wall": "North Curtin Wall Alley",
    "south_wall": "South Curtin Wall Alley",
    "castle_hill": "Wzgórze Zamkowe (Castle Hill)",
    "krakow_suburb": "Przedmieście Krakowskie (Kraków Suburb)"
}

HOUSE_TYPES = [
    "kamienica_patrician_gothic_stepped",
    "kamienica_patrician_stone_arches",
    "kamienica_patrician_renaissance_attic",
    "merchant_fachwerk_jettied_triple",
    "merchant_fachwerk_jettied_double",
    "merchant_arched_storefront_brick",
    "artisan_half_timber_workshop",
    "artisan_narrow_gable_gothic",
    "artisan_rowhouse_loam_plaster",
    "baker_brick_oven_chimney",
    "blacksmith_open_forge_timber",
    "brewer_spacious_malthouse",
    "tanner_riverfront_timber_drying",
    "cooper_yard_dwelling",
    "weaver_loom_hall_half_timber",
    "potter_kiln_shed_house",
    "shoemaker_corner_tenement",
    "furrier_attic_dormer_house",
    "timber_shingle_cottage_large",
    "timber_shingle_cottage_small",
    "thatched_plebeian_wattle_daub",
    "thatched_plebeian_timber_cruck",
    "loess_foundation_steep_thatch",
    "two_family_timber_longhouse",
    "gatekeeper_watch_house"
]

SHED_TYPES = [
    "shed_lean_to_timber",
    "shed_open_post_drying_shelter",
    "shed_wattle_daub_tools"
]

CRAFTS = [
    {"id": "blacksmith", "name": "Blacksmith", "sign": "Golden Horseshoe", "guild": "Smiths & Armorers Guild", "wealth": "artisan"},
    {"id": "baker", "name": "Baker", "sign": "Gilded Pretzel", "guild": "Bakers Fraternity", "wealth": "burgher"},
    {"id": "shoemaker", "name": "Shoemaker", "sign": "Pointed Poulaine Boot", "guild": "Cobblers Guild", "wealth": "artisan"},
    {"id": "tailor", "name": "Tailor", "sign": "Iron Shears & Needle", "guild": "Tailors Guild", "wealth": "burgher"},
    {"id": "furrier", "name": "Furrier", "sign": "Ermine & Sable Pelt", "guild": "Furriers Confraternity", "wealth": "patrician"},
    {"id": "potter", "name": "Potter", "sign": "Glazed Clay Amphora", "guild": "Potters Guild", "wealth": "artisan"},
    {"id": "cooper", "name": "Cooper", "sign": "Oak Wine Cask with Iron Hoops", "guild": "Coopers Guild", "wealth": "artisan"},
    {"id": "weaver", "name": "Weaver", "sign": "Weaving Shuttle & Spindle", "guild": "Weavers Guild", "wealth": "artisan"},
    {"id": "brewer", "name": "Brewer", "sign": "Copper Mash Paddle & Tankard", "guild": "Brewers Confraternity", "wealth": "patrician"},
    {"id": "carpenter", "name": "Carpenter", "sign": "Broad Axe & Framing Square", "guild": "Carpenters Guild", "wealth": "artisan"},
    {"id": "roper", "name": "Roper", "sign": "Braided Hemp Coil", "guild": "Ropers Guild", "wealth": "plebeian"},
    {"id": "goldsmith", "name": "Goldsmith", "sign": "Chased Chalice & Scales", "guild": "Goldsmiths Guild", "wealth": "patrician"},
    {"id": "tanner", "name": "Tanner", "sign": "Stretched Ox Hide", "guild": "Tanners Guild", "wealth": "artisan"},
    {"id": "mason", "name": "Stone Mason", "sign": "Mallet, Chisel & Trowel", "guild": "Masons Confraternity", "wealth": "burgher"},
    {"id": "wheelwright", "name": "Wheelwright", "sign": "Spoked Cart Wheel", "guild": "Wheelwrights Guild", "wealth": "artisan"},
    {"id": "butcher", "name": "Butcher", "sign": "Bull's Head & Cleaver", "guild": "Butchers Guild", "wealth": "burgher"},
    {"id": "armorer", "name": "Armorer", "sign": "Sallet Helm & Crossbow", "guild": "Armorers Guild", "wealth": "patrician"},
    {"id": "candlemaker", "name": "Candlemaker", "sign": "Dipped Beeswax Candle", "guild": "Chandlers Guild", "wealth": "artisan"}
]

FIRST_NAMES_MALE = [
    "Jan", "Stanisław", "Mikołaj", "Piotr", "Wojciech", "Jakub", "Maciej", "Andrzej",
    "Tomasz", "Paweł", "Michał", "Bartłomiej", "Marcin", "Grzegorz", "Hanusz", "Dobiesław",
    "Sędziwój", "Przecław", "Klemens", "Wawrzyniec", "Biernacik", "Jodok", "Gunter", "Lutko"
]

FIRST_NAMES_FEMALE = [
    "Jadwiga", "Anna", "Katarzyna", "Małgorzata", "Dorota", "Barbara", "Elżbieta", "Agnieszka",
    "Zofia", "Helena", "Świętochna", "Polska", "Bogumiła", "Ofka", "Beata", "Wichna"
]

SURNAMES_OR_EPITHETS = [
    "z Lublina", "Kowal", "Sukiennik", "Szmatruz", "Złotnik", "Kołodziej", "Piwowar", "Garbacz",
    "Bednarz", "Szewc", "Mularz", "Krawiec", "Cieśla", "Rzeźnik", "Miecznik", "Kozioł",
    "Włodarz", "Wójtowicz", "Białobłocki", "Czapla", "Grodzki", "z Chodla", "Kmieć", "Kramarz",
    "von Thorn", "von Breslau", "z Kazimierza", "Węgrzyn", "Ruś", "Litwin"
]

def generate_lublin_city_plan():
    print("[CityPlanGenerator] Synthesizing Lublin 1392 morphology & agent schedules...")

    # 1. Topography & Promontory Dimensions
    # Lublin Old Town lies on a spur (approx. 400m long SW-NE, 220m wide NW-SE).
    # Origin (0,0) is centered on the Market Square (Rynek).
    # SW direction (-X, -Z) goes towards Kraków Gate and Kraków Suburb.
    # NE direction (+X, +Z) goes towards Grodzka Gate and Castle Hill across the moat.
    
    # 2. Curtain Wall & Towers
    # 14 Towers + 2 Gates
    wall_points = [
        # Kraków Gate at SW
        {"id": "gate_krakow", "type": "gate", "name": "Brama Krakowska (Kraków Gate)", "x": -160, "z": -80, "angle": 210, "height": 26},
        # South wall moving east
        {"id": "tower_01", "type": "tower", "name": "Tower of the Dominican Friars", "x": -125, "z": -120, "angle": 180, "height": 18},
        {"id": "tower_02", "type": "tower", "name": "Tower of the Shoemakers", "x": -80, "z": -140, "angle": 160, "height": 18},
        {"id": "tower_03", "type": "tower", "name": "Tower of the Bakers", "x": -30, "z": -145, "angle": 140, "height": 18},
        {"id": "tower_04", "type": "tower", "name": "Tower of the Butchers", "x": 25, "z": -140, "angle": 120, "height": 18},
        {"id": "tower_05", "type": "tower", "name": "Tower of the Tailors", "x": 80, "z": -120, "angle": 100, "height": 18},
        {"id": "tower_06", "type": "tower", "name": "Tower of the Goldsmiths", "x": 135, "z": -80, "angle": 80, "height": 18},
        {"id": "tower_07", "type": "tower", "name": "Half-Bastion of the Fara", "x": 170, "z": -35, "angle": 60, "height": 18},
        # Grodzka Gate at NE (leading to Castle Hill)
        {"id": "gate_grodzka", "type": "gate", "name": "Brama Grodzka (Grodzka Gate)", "x": 190, "z": 20, "angle": 35, "height": 24},
        # North wall moving west
        {"id": "tower_08", "type": "tower", "name": "Tower of the Coopers", "x": 160, "z": 70, "angle": 15, "height": 18},
        {"id": "tower_09", "type": "tower", "name": "Tower of the Blacksmiths", "x": 110, "z": 105, "angle": -15, "height": 18},
        {"id": "tower_10", "type": "tower", "name": "Tower of the Weavers", "x": 55, "z": 120, "angle": -45, "height": 18},
        {"id": "tower_11", "type": "tower", "name": "Tower of the Furriers", "x": 0, "z": 115, "angle": -75, "height": 18},
        {"id": "tower_12", "type": "tower", "name": "Tower of the Potters", "x": -55, "z": 95, "angle": -105, "height": 18},
        {"id": "tower_13", "type": "tower", "name": "Tower of the Tanners", "x": -105, "z": 60, "angle": -135, "height": 18},
        {"id": "tower_14", "type": "tower", "name": "Watch Bastion of the Starost", "x": -140, "z": -15, "angle": -165, "height": 18}
    ]

    # Castle Hill Elements (Across Czechówka ravine, connected by bridge)
    castle_elements = [
        {
            "id": "castle_donjon",
            "type": "landmark",
            "name": "Donżon (Romanesque Round Keep)",
            "x": 275,
            "z": 75,
            "width": 16,
            "depth": 16,
            "height": 30,
            "description": "Limestone cylinder keep built in 13th c., 3m thick walls, refuge tower."
        },
        {
            "id": "castle_chapel",
            "type": "landmark",
            "name": "Kaplica Trójcy Świętej (Royal Holy Trinity Chapel)",
            "x": 260,
            "z": 115,
            "width": 14,
            "depth": 24,
            "height": 22,
            "description": "Two-tier Gothic brick chapel commissioned by Casimir the Great / Jagiełło with Ruthenian-Byzantine frescoes."
        },
        {
            "id": "castle_palace",
            "type": "landmark",
            "name": "Dwór Królewski (Royal Palace Hall)",
            "x": 295,
            "z": 110,
            "width": 16,
            "depth": 30,
            "height": 19,
            "description": "Gothic royal residential hall hosting King Jagiełło and royal court during the 1392 Fair."
        },
        {
            "id": "castle_bridge",
            "type": "infrastructure",
            "name": "Most Zamkowy (Castle Moat Bridge)",
            "startX": 195, "startZ": 22,
            "endX": 245, "endZ": 55,
            "width": 6
        }
    ]

    # Civic Landmarks inside Old Town Core
    civic_landmarks = [
        {
            "id": "town_hall",
            "type": "landmark",
            "name": "Ratusz Miejski (Old Town Hall)",
            "x": 0,
            "z": 0,
            "width": 24,
            "depth": 18,
            "height": 32,
            "description": "Gothic brick town hall with clock tower, ground floor council arcades, battlemented attic and 4 corner turrets."
        },
        {
            "id": "szmatruz",
            "type": "landmark",
            "name": "Szmatruz (Royal Cloth & Bread Hall)",
            "x": 22,
            "z": -20,
            "width": 28,
            "depth": 14,
            "height": 15,
            "description": "Cloth hall with 22 brick pillars, covered central aisle, 16 royal fair vendor stalls."
        },
        {
            "id": "parish_fara",
            "type": "landmark",
            "name": "Kościół św. Michała Archanioła (Collegiate Parish Church)",
            "x": 130,
            "z": 20,
            "width": 22,
            "depth": 36,
            "height": 42,
            "description": "Magnificent Gothic collegiate church towering over the promontory with 60-meter spire."
        },
        {
            "id": "dominican_monastery",
            "type": "landmark",
            "name": "Klasztor Dominikanów (Dominican Friary & Basilica)",
            "x": -60,
            "z": -90,
            "width": 26,
            "depth": 40,
            "height": 30,
            "description": "Founded in 1342 by Casimir the Great, sanctuary of the True Cross Relic."
        },
        {
            "id": "town_pillory",
            "type": "civic_object",
            "name": "Pręgierz Miejski (Town Pillory & Well)",
            "x": -15,
            "z": 12,
            "width": 4,
            "depth": 4,
            "height": 6
        }
    ]

    # Street Network Graph (Vectors & Waypoints)
    street_nodes = [
        # Kraków Gate Entrance
        {"id": "st_krakow_gate", "x": -160, "z": -80},
        {"id": "st_bramowa_mid", "x": -100, "z": -50},
        {"id": "st_rynek_sw", "x": -40, "z": -25},
        # Market Square Corners
        {"id": "st_rynek_nw", "x": -35, "z": 25},
        {"id": "st_rynek_ne", "x": 35, "z": 25},
        {"id": "st_rynek_se", "x": 35, "z": -25},
        {"id": "st_rynek_center", "x": 0, "z": -2},
        # Grodzka street towards Grodzka Gate
        {"id": "st_grodzka_start", "x": 50, "z": 15},
        {"id": "st_fara_junction", "x": 115, "z": 18},
        {"id": "st_grodzka_gate", "x": 188, "z": 20},
        # Castle bridge & courtyard
        {"id": "st_castle_gate", "x": 245, "z": 55},
        {"id": "st_castle_courtyard", "x": 275, "z": 95},
        # Złota & Dominikańska alleys (South quarter)
        {"id": "st_zlota_start", "x": 15, "z": -35},
        {"id": "st_dominikanska_mid", "x": -45, "z": -75},
        {"id": "st_dominikanska_wall", "x": -85, "z": -120},
        # Rybna & Kowalska lanes (North quarter)
        {"id": "st_rybna_start", "x": -10, "z": 35},
        {"id": "st_rybna_mid", "x": 40, "z": 75},
        {"id": "st_kowalska_wall", "x": 95, "z": 95},
        # Suburb road
        {"id": "st_suburb_road_01", "x": -195, "z": -105},
        {"id": "st_suburb_road_02", "x": -240, "z": -135},
        {"id": "st_suburb_workshop", "x": -270, "z": -115}
    ]

    street_edges = [
        ("st_krakow_gate", "st_bramowa_mid"),
        ("st_bramowa_mid", "st_rynek_sw"),
        ("st_rynek_sw", "st_rynek_nw"),
        ("st_rynek_nw", "st_rynek_ne"),
        ("st_rynek_ne", "st_rynek_se"),
        ("st_rynek_se", "st_rynek_sw"),
        ("st_rynek_center", "st_grodzka_start"),
        ("st_grodzka_start", "st_fara_junction"),
        ("st_fara_junction", "st_grodzka_gate"),
        ("st_grodzka_gate", "st_castle_gate"),
        ("st_castle_gate", "st_castle_courtyard"),
        ("st_rynek_se", "st_zlota_start"),
        ("st_zlota_start", "st_dominikanska_mid"),
        ("st_dominikanska_mid", "st_dominikanska_wall"),
        ("st_rynek_nw", "st_rybna_start"),
        ("st_rybna_start", "st_rybna_mid"),
        ("st_rybna_mid", "st_kowalska_wall"),
        ("st_krakow_gate", "st_suburb_road_01"),
        ("st_suburb_road_01", "st_suburb_road_02"),
        ("st_suburb_road_02", "st_suburb_workshop")
    ]

    # Generate 580 Parcels with zero identical consecutive building types
    # Distribution across districts:
    # 1. Market Square frontage: 44 high-status plots
    # 2. Bramowa & Grodzka arterials: 96 plots
    # 3. Dominican / Southern quarter: 120 plots
    # 4. Fara / Eastern quarter: 110 plots
    # 5. North wall & Rybna lanes: 100 plots
    # 6. Castle Hill bailey: 30 auxiliary plots
    # 7. Kraków Suburb (unwalled quarter): 80 plots (including player workshop)
    # Total = 580 parcels!

    TARGET_PARCEL_COUNT = 580
    parcels = []
    
    # Track assigned types per street front to avoid consecutive repeats
    last_building_per_street = {}

    def pick_building_type(street_id, district, is_shed=False):
        if is_shed:
            return random.choice(SHED_TYPES)
        last = last_building_per_street.get(street_id, None)
        # Filter candidate houses based on district prestige
        if district == "market_square":
            candidates = [h for h in HOUSE_TYPES if "patrician" in h or "merchant" in h]
        elif district in ["castle_hill"]:
            candidates = [h for h in HOUSE_TYPES if "patrician" in h or "watch" in h or "gothic" in h]
        elif district in ["krakow_suburb"]:
            candidates = [h for h in HOUSE_TYPES if "timber" in h or "thatched" in h or "carpenter" in h or "cooper" in h or "blacksmith" in h or "tanner" in h]
        else:
            candidates = HOUSE_TYPES

        # Avoid consecutive repeats
        choices = [c for c in candidates if c != last]
        if not choices:
            choices = candidates
        chosen = random.choice(choices)
        last_building_per_street[street_id] = chosen
        return chosen

    craft_cycle_index = 0

    # Sector definitions with bounding boxes and street alignments
    sectors = [
        # 1. Market Square frontage (West, North, East, South edges of Rynek)
        {"district": "market_square", "street": "Rynek (Market Square)", "count": 48, "center": (0, 0), "radius": 46, "ring": True},
        # 2. Bramowa Street corridor (SW)
        {"district": "bramowa_quarter", "street": "Ulica Bramowa", "count": 82, "xRange": (-150, -45), "zRange": (-70, -10)},
        # 3. Grodzka Street corridor (NE)
        {"district": "grodzka_quarter", "street": "Ulica Grodzka", "count": 88, "xRange": (40, 180), "zRange": (-10, 50)},
        # 4. Dominican / Southern quarters (Złota, Jezuicka, Archidiakońska)
        {"district": "dominican_quarter", "street": "Ulica Dominikańska / Złota", "count": 105, "xRange": (-110, 80), "zRange": (-135, -55)},
        # 5. North Wall & Rybna quarter (Kowalska, Rybna)
        {"district": "north_wall", "street": "Ulica Rybna / Kowalska", "count": 102, "xRange": (-90, 130), "zRange": (35, 115)},
        # 6. Castle Hill Outer Bailey
        {"district": "castle_hill", "street": "Podzamcze / Dziedziniec Zamkowy", "count": 35, "xRange": (230, 310), "zRange": (40, 125)},
        # 7. Kraków Suburb (Exterior unwalled quarter, timber yards)
        {"district": "krakow_suburb", "street": "Trakt Krakowski (Suburb)", "count": 120, "xRange": (-280, -165), "zRange": (-180, -30)}
    ]

    parcel_index = 1

    # Special parcel 1: Player's Workshop in Kraków Suburb
    player_parcel_id = "p_001_player_workshop"
    parcels.append({
        "id": player_parcel_id,
        "name": "Mistrzowski Warsztat Grzesznika (Player's Guild Workshop)",
        "district": "krakow_suburb",
        "streetName": "Trakt Krakowski (Suburb)",
        "x": -235.0,
        "z": -120.0,
        "width": 14.0,
        "depth": 18.0,
        "orientation": 45.0,
        "elevation": 1.2,
        "buildingType": "artisan_half_timber_workshop",
        "isPlayerProperty": True,
        "craft": {
            "id": "carpenter",
            "name": "Master Joiner & Cartwright",
            "sign": "Golden Compass & Framing Chisel",
            "guild": "Guild of Woodworkers"
        },
        "aging": {
            "ageYears": 18,
            "ridgeSag": 0.08,
            "wallLeanAngle": 0.8,
            "woodGraying": 0.35,
            "mossFoundation": 0.22,
            "maintenanceState": "sound"
        },
        "clutter": ["firewood_rick", "oak_timber_planks", "wheelbarrow", "shaving_bench", "tar_pitch_barrel"],
        "scaffolding": False,
        "wealthClass": "artisan",
        "residents": [],
        "workplaceFor": [],
        "commodities": {"oak_beams": 32, "iron_nails": 250, "linseed_oil": 12}
    })
    parcel_index += 1

    for sec in sectors:
        cnt = sec["count"]
        # Distribute parcels inside this sector
        for i in range(cnt):
            if parcel_index > TARGET_PARCEL_COUNT:
                break
            
            p_id = f"p_{parcel_index:03d}"
            
            # Position calculation
            if sec.get("ring"):
                # Market square perimeter rectangle
                # Square boundary: x in [-38, 38], z in [-28, 28]
                perim_fraction = i / cnt
                # Walk perimeter: Bottom, Right, Top, Left
                if perim_fraction < 0.25: # South
                    t = perim_fraction / 0.25
                    px = -38 + t * 76
                    pz = -30
                    angle = 0
                elif perim_fraction < 0.5: # East
                    t = (perim_fraction - 0.25) / 0.25
                    px = 40
                    pz = -28 + t * 56
                    angle = 90
                elif perim_fraction < 0.75: # North
                    t = (perim_fraction - 0.5) / 0.25
                    px = 38 - t * 76
                    pz = 30
                    angle = 180
                else: # West
                    t = (perim_fraction - 0.75) / 0.25
                    px = -40
                    pz = 28 - t * 56
                    angle = 270
                # Slight setback jitter
                px += random.uniform(-1.5, 1.5)
                pz += random.uniform(-1.5, 1.5)
            else:
                x_min, x_max = sec["xRange"]
                z_min, z_max = sec["zRange"]
                px = round(random.uniform(x_min, x_max), 1)
                pz = round(random.uniform(z_min, z_max), 1)
                # Angle facing roughly towards street
                angle = random.choice([0, 45, 90, 135, 180, 225, 270, 315])

            # Elevation calculation based on loess hill topography
            # Castle hill is highest (+8m), Old Town plateau is +3m to +5m, sloping to Czechówka (+0m)
            dist_to_castle = math.hypot(px - 280, pz - 90)
            if dist_to_castle < 70:
                elevation = round(6.5 + (1.0 - dist_to_castle / 70.0) * 3.5, 2)
            else:
                dist_to_center = math.hypot(px, pz)
                elevation = round(max(0.5, 4.2 - (dist_to_center / 220.0) * 3.8 + random.uniform(-0.3, 0.3)), 2)

            # Determine if this plot has a shed or main house
            is_shed = (random.random() < 0.14) and (sec["district"] != "market_square")
            b_type = pick_building_type(sec["street"], sec["district"], is_shed=is_shed)

            # Assign craft to approx 50% of residential/commercial plots
            has_craft = (not is_shed) and (random.random() < 0.52)
            craft_data = None
            if has_craft:
                craft_data = CRAFTS[craft_cycle_index % len(CRAFTS)]
                craft_cycle_index += 1

            # Wealth class assignment
            if sec["district"] == "market_square":
                wealth = "patrician" if random.random() < 0.65 else "burgher"
            elif sec["district"] == "castle_hill":
                wealth = "patrician" if random.random() < 0.4 else "burgher"
            elif sec["district"] == "krakow_suburb":
                wealth = "artisan" if random.random() < 0.5 else "plebeian"
            else:
                if craft_data:
                    wealth = craft_data["wealth"]
                else:
                    wealth = random.choice(["burgher", "artisan", "plebeian"])

            # Parametric structural aging
            age = random.randint(3, 115)
            # Parabolic correlation with age
            age_factor = age / 115.0
            ridge_sag = round(min(0.35, 0.02 + age_factor * 0.28 + random.uniform(-0.03, 0.05)), 3)
            wall_lean = round(min(3.0, (age_factor * 2.4 + random.uniform(-0.4, 0.6)) * random.choice([-1, 1])), 2)
            wood_gray = round(min(1.0, 0.15 + age_factor * 0.8), 2)
            moss_found = round(min(1.0, 0.05 + age_factor * 0.75 + (0.2 if elevation < 2.0 else 0.0)), 2)
            
            if age > 75:
                maint = "dilapidated" if random.random() < 0.4 else "weathered"
            elif age > 30:
                maint = "weathered" if random.random() < 0.6 else "sound"
            else:
                maint = "pristine" if random.random() < 0.45 else "sound"

            # Yard clutter
            possible_clutter = ["firewood_rick", "oak_barrel", "leaning_ladder", "wicker_hoop", "cart_wheel", "handcart", "water_trough", "cask_stack"]
            clutter_count = random.randint(1, 4)
            clutter = random.sample(possible_clutter, clutter_count)

            # Active building site with timber scaffolding (approx 6% of plots)
            scaffolding = (not is_shed) and (random.random() < 0.06)

            # Dimensions
            width = random.choice([8.0, 9.5, 11.0, 12.5]) if not is_shed else random.choice([5.0, 6.5])
            depth = random.choice([12.0, 14.5, 16.0, 18.0]) if not is_shed else random.choice([6.0, 8.0])

            parcels.append({
                "id": p_id,
                "district": sec["district"],
                "streetName": sec["street"],
                "x": px,
                "z": pz,
                "width": width,
                "depth": depth,
                "orientation": float(angle),
                "elevation": elevation,
                "buildingType": b_type,
                "isShed": is_shed,
                "craft": craft_data,
                "aging": {
                    "ageYears": age,
                    "ridgeSag": ridge_sag,
                    "wallLeanAngle": wall_lean,
                    "woodGraying": wood_gray,
                    "mossFoundation": moss_found,
                    "maintenanceState": maint
                },
                "clutter": clutter,
                "scaffolding": scaffolding,
                "wealthClass": wealth,
                "residents": [],
                "workplaceFor": [],
                "commodities": {
                    "rye_sacks": random.randint(0, 15),
                    "salted_herring_kilderkins": random.randint(0, 8),
                    "tallow_candles": random.randint(5, 50),
                    "grosze": random.randint(10, 600)
                }
            })
            parcel_index += 1

    print(f"[CityPlanGenerator] Generated {len(parcels)} distinct parcel nodes.")

    # 3. Living Autonomous Citizens (~1,500 citizens across ~400 households)
    TARGET_CITIZEN_COUNT = 1500
    citizens = []

    # Map residential parcels
    home_parcels = [p for p in parcels if not p.get("isShed")]
    work_parcels = [p for p in parcels if p.get("craft") is not None]

    # Civic Bell Schedule Definition (8 Canonical Bell Hours of Lublin 1392)
    BELL_HOURS = {
        "matins": {"hour": 5, "name": "Matins (Jutrznia / Dawn)", "action": "waking & lighting hearth"},
        "prime": {"hour": 7, "name": "Prime (Pryma / Guild Opening)", "action": "guild workshop opening"},
        "terce": {"hour": 9, "name": "Terce (Tercja / Royal Fair Opening)", "action": "fair trade & stall bustling"},
        "sext": {"hour": 12, "name": "Sext (Seksta / Midday Bell)", "action": "cloth inspection & tavern lunch"},
        "nones": {"hour": 15, "name": "Nones (Nona / High Fair)", "action": "livestock & foreign trade peak"},
        "vespers": {"hour": 18, "name": "Vespers (Nieszpory / Dusk)", "action": "stall closing & tavern carousing"},
        "compline": {"hour": 21, "name": "Compline (Kompleta / Curfew)", "action": "gate closure & watchmen patrol"},
        "night": {"hour": 0, "name": "Deep Night (Głęboka Noc)", "action": "sleep & lantern watch"}
    }

    foreign_origins = [
        {"origin": "Buda (Kingdom of Hungary)", "trade": "Hungarian Wine Merchant", "goods": "Tokaj casks & brassware"},
        {"origin": "Toruń (Hanseatic League)", "trade": "Hanseatic Merchant", "goods": "Flemish wool & Baltic amber"},
        {"origin": "Gdańsk (Prussia)", "trade": "Amber & Salt Merchant", "goods": "Rock salt & pickled sturgeon"},
        {"origin": "Lwów (Ruthenia)", "trade": "Ruthenian Fur Merchant", "goods": "Sable furs & dark wax"},
        {"origin": "Kraków (Royal Capital)", "trade": "Royal Factor", "goods": "Silver groschen & parchment books"}
    ]

    for c_idx in range(1, TARGET_CITIZEN_COUNT + 1):
        cit_id = f"cit_{c_idx:04d}"
        
        # Gender & Name
        is_male = random.random() < 0.52
        first_name = random.choice(FIRST_NAMES_MALE) if is_male else random.choice(FIRST_NAMES_FEMALE)
        surname = random.choice(SURNAMES_OR_EPITHETS)
        full_name = f"{first_name} {surname}"

        # Assign home household
        home_p = random.choice(home_parcels)
        home_p["residents"].append(cit_id)

        # Profession & Role
        is_visitor = (c_idx > 1380) # Foreign fair visitors
        is_guard = (not is_visitor) and (c_idx % 28 == 0) # Town guard / gatekeepers
        is_monk = (not is_visitor) and (not is_guard) and (c_idx % 45 == 0)

        if is_visitor:
            foreign_info = random.choice(foreign_origins)
            trade_name = foreign_info["trade"]
            guild_rank = "foreign_merchant"
            wealth = "patrician" if random.random() < 0.5 else "burgher"
            work_p_id = "szmatruz" # Trades in cloth hall stalls
            wallet = random.randint(150, 2500)
            carried_item = foreign_info["goods"]
        elif is_guard:
            trade_name = "Town Halberdier & Gate Watch"
            guild_rank = "sergeant" if random.random() < 0.2 else "guardsman"
            wealth = "plebeian"
            work_p_id = random.choice(["gate_krakow", "gate_grodzka", "town_hall", "castle_donjon"])
            wallet = random.randint(15, 65)
            carried_item = "Iron Halberd & Horn Lantern"
        elif is_monk:
            trade_name = "Dominican Friar" if random.random() < 0.6 else "Collegiate Vicar"
            guild_rank = "brother"
            wealth = "plebeian"
            work_p_id = "dominican_monastery" if "Dominican" in trade_name else "parish_fara"
            wallet = random.randint(2, 20)
            carried_item = "Wooden Rosary & Prayer Book"
        else:
            # Burgher / Artisan
            if home_p.get("craft"):
                trade_name = home_p["craft"]["name"]
                work_p_id = home_p["id"]
                guild_rank = random.choice(["apprentice", "journeyman", "master", "guildmaster"])
                wealth = home_p["wealthClass"]
                carried_item = f"Craft Tools of {trade_name}"
            else:
                work_p = random.choice(work_parcels)
                trade_name = work_p["craft"]["name"] if work_p.get("craft") else "Day Laborer"
                work_p_id = work_p["id"]
                guild_rank = "journeyman" if random.random() < 0.4 else "laborer"
                wealth = "plebeian"
                carried_item = "Burlap Sack & Whetstone"
            wallet = random.randint(10, 350)

        # Register workplace
        for p in parcels:
            if p["id"] == work_p_id:
                p["workplaceFor"].append(cit_id)
                break

        # Generate schedule linked to bells
        schedule = [
            {"hour": 5, "state": "WAKING", "location": home_p["id"], "task": "Kindling morning peat hearth and praying"},
            {"hour": 7, "state": "COMMUTING", "location": work_p_id, "task": "Walking through morning mist to workplace"},
            {"hour": 9, "state": "WORKING", "location": work_p_id, "task": f"Guild trade / fair business ({trade_name})"},
            {"hour": 12, "state": "EATING", "location": "market_square" if random.random() < 0.6 else home_p["id"], "task": "Midday bread, roast pork & small beer"},
            {"hour": 14, "state": "WORKING", "location": work_p_id, "task": "Afternoon transactions & guild apprentice training"},
            {"hour": 18, "state": "SOCIALIZING", "location": "market_square", "task": "Vespers bell, visiting fair booths and tavern"},
            {"hour": 21, "state": "RETURNING", "location": home_p["id"], "task": "Returning home before gate portcullis drops"},
            {"hour": 22, "state": "SLEEPING", "location": home_p["id"], "task": "Sound asleep in straw pallet bed"}
        ]

        # Night watchmen invert schedule
        if is_guard:
            schedule = [
                {"hour": 5, "state": "SLEEPING", "location": home_p["id"], "task": "Resting after night watch"},
                {"hour": 12, "state": "WAKING", "location": home_p["id"], "task": "Midday stew & sharpening halberd"},
                {"hour": 15, "state": "COMMUTING", "location": work_p_id, "task": "Reporting to Captain of the Watch"},
                {"hour": 18, "state": "PATROLLING", "location": work_p_id, "task": "Inspecting royal fair merchants & gates"},
                {"hour": 21, "state": "PATROLLING", "location": "curtain_wall", "task": "Locking city gates & torchlight wall watch"},
                {"hour": 0, "state": "PATROLLING", "location": "market_square", "task": "Midnight lantern patrol checking door bolts"}
            ]

        citizens.append({
            "id": cit_id,
            "name": full_name,
            "gender": "male" if is_male else "female",
            "trade": trade_name,
            "guildRank": guild_rank,
            "wealthClass": wealth,
            "homeParcelId": home_p["id"],
            "bedNumber": len(home_p["residents"]),
            "workParcelId": work_p_id,
            "walletGroschen": wallet,
            "carriedItem": carried_item,
            "schedule": schedule
        })

    print(f"[CityPlanGenerator] Simulated {len(citizens)} persistent citizens across {len(home_parcels)} households.")

    # 4. Royal Fair Systemic Events Specification
    fair_events = [
        {
            "id": "event_hungarian_caravan",
            "name": "Arrival of Hungarian Wine Caravans",
            "triggerHour": 9,
            "location": "gate_krakow",
            "description": "Thirty ox-drawn wagons carrying Tokaji wine, copper ingots, and dried prunes pass through Kraków Gate after paying the royal bridge toll."
        },
        {
            "id": "event_cloth_inspection",
            "name": "Guild Cloth Inspection at the Szmatruz",
            "triggerHour": 12,
            "location": "szmatruz",
            "description": "The Senior Alderman of the Weavers and Royal Bailiff inspect Flemish broadcloth rolls with lead seal stamps."
        },
        {
            "id": "event_king_decree",
            "name": "Royal Herald Proclamation",
            "triggerHour": 15,
            "location": "town_hall",
            "description": "A mounted royal herald from King Władysław Jagiełło announces toll exemptions for merchants travelling through Sandomierz and Lublin."
        },
        {
            "id": "event_curfew_closure",
            "name": "Civic Curfew Bell & Gate Locking",
            "triggerHour": 21,
            "location": "gate_krakow",
            "description": "Collegiate bells toll nine times. Heavy oak gates and iron portcullises are bolted shut by municipal halberdiers."
        }
    ]

    city_plan = {
        "metadata": {
            "city": "Lublin",
            "year": 1392,
            "reign": "King Władysław II Jagiełło",
            "event": "Royal Fair of the Assumption & Pentecost",
            "areaHectares": 8.84,
            "generatedAt": "1392-08-15T00:00:00Z",
            "version": "1.0.0"
        },
        "districts": DISTRICTS,
        "defense": {
            "perimeterPoints": wall_points,
            "castleElements": castle_elements
        },
        "civicLandmarks": civic_landmarks,
        "streetNetwork": {
            "nodes": street_nodes,
            "edges": street_edges
        },
        "parcels": parcels,
        "citizens": citizens,
        "bellHours": BELL_HOURS,
        "fairEvents": fair_events,
        "houseTypesCatalog": HOUSE_TYPES,
        "shedTypesCatalog": SHED_TYPES,
        "craftsCatalog": CRAFTS
    }

    # Save to public/city_plan.json and root city_plan.json
    os.makedirs("public", exist_ok=True)
    with open("public/city_plan.json", "w", encoding="utf-8") as f:
        json.dump(city_plan, f, indent=2, ensure_ascii=False)
    
    with open("city_plan.json", "w", encoding="utf-8") as f:
        json.dump(city_plan, f, indent=2, ensure_ascii=False)

    print("[CityPlanGenerator] Successfully wrote public/city_plan.json and city_plan.json!")
    return city_plan

if __name__ == "__main__":
    generate_lublin_city_plan()
