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

WOODCUTTER_CRAFT = {"id": "woodcutter", "name": "Woodcutter", "sign": "Felling Axe & Log", "guild": "Sawyers & Woodcutters",
                    "wealth": "plebeian"}
LUMBER_YARDS = 3        # outermost craftless Kraków-suburb parcels become logging yards
WOODCUTTERS = 18        # suburb men moved from the wood trades to the yards


def assign_woodcutters(parcels, citizens):
    """Post-pass with its own RNG, so every other parcel and citizen stays as generated.
    Yards render as logging camps (buildingType contains 'logging', src/engine/parcel-kind.ts);
    'Woodcutter' maps to char_woodcutter (three-renderer.ts getCitizenArchetype)."""
    rng = random.Random(1392_7)
    by_id = {p["id"]: p for p in parcels}
    suburb = [p for p in parcels if p["district"] == "krakow_suburb" and not p.get("isShed")
              and not p.get("craft") and not p["id"].endswith("player_workshop")]
    yards = sorted(suburb, key=lambda p: -math.hypot(p["x"], p["z"]))[:LUMBER_YARDS]
    for y in yards:
        y["buildingType"] = "sawyer_logging_yard"
        y["craft"] = WOODCUTTER_CRAFT
    wood_trades = {"Carpenter", "Wheelwright", "Cooper"}
    pool = [c for c in citizens if c["gender"] == "male" and c["trade"] in wood_trades
            and by_id.get(c["homeParcelId"], {}).get("district") == "krakow_suburb"
            and c["guildRank"] in ("apprentice", "journeyman", "laborer")]
    for i, c in enumerate(rng.sample(pool, min(WOODCUTTERS, len(pool)))):
        yard = yards[i % len(yards)]
        old = by_id.get(c["workParcelId"])
        if old and c["id"] in old["workplaceFor"]:
            old["workplaceFor"].remove(c["id"])
        yard["workplaceFor"].append(c["id"])
        for s in c["schedule"]:
            if s["location"] == c["workParcelId"]:
                s["location"] = yard["id"]
            s["task"] = s["task"].replace(f"({c['trade']})", "(Woodcutter)")
        c["trade"] = "Woodcutter"
        c["workParcelId"] = yard["id"]
        c["carriedItem"] = "Felling Axe & Iron Wedges"


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

    # -------------------------------------------------------------
    # 2D Oriented Bounding Box (OBB) & Separating Axis Theorem (SAT)
    # Guarantees ZERO building penetrations or overlapping roofs
    # -------------------------------------------------------------
    def get_obb_corners(cx, cz, w, d, angle_deg, margin=0.3):
        hw = (w / 2.0) + margin
        hd = (d / 2.0) + margin
        ang = math.radians(angle_deg)
        cos_a = math.cos(ang)
        sin_a = math.sin(ang)
        corners = []
        for dx, dz in [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]:
            rx = dx * cos_a - dz * sin_a
            rz = dx * sin_a + dz * cos_a
            corners.append((cx + rx, cz + rz))
        return corners

    def obb_overlap(corners1, corners2):
        for corners in [corners1, corners2]:
            for i in range(4):
                p1 = corners[i]
                p2 = corners[(i + 1) % 4]
                edge_x = p2[0] - p1[0]
                edge_z = p2[1] - p1[1]
                axis_x = -edge_z
                axis_z = edge_x

                min1, max1 = float('inf'), float('-inf')
                for c in corners1:
                    proj = c[0] * axis_x + c[1] * axis_z
                    if proj < min1: min1 = proj
                    if proj > max1: max1 = proj

                min2, max2 = float('inf'), float('-inf')
                for c in corners2:
                    proj = c[0] * axis_x + c[1] * axis_z
                    if proj < min2: min2 = proj
                    if proj > max2: max2 = proj

                if max1 <= min2 or max2 <= min1:
                    return False
        return True

    # Pre-register Landmark Bounding Boxes to avoid any building clipping them
    LANDMARKS_OBB = [
        get_obb_corners(0, 0, 26, 20, 0, margin=3.0),         # Town hall
        get_obb_corners(22, -18, 26, 12, 90, margin=2.5),      # Szmatruz
        get_obb_corners(-14, 10, 6, 6, 0, margin=2.0),         # Well
        get_obb_corners(-160, -80, 16, 16, 210, margin=3.0),   # Krakow Gate
        get_obb_corners(190, 20, 16, 16, 35, margin=3.0),      # Grodzka Gate
        get_obb_corners(275, 75, 18, 18, 0, margin=3.0),       # Castle Donjon
        get_obb_corners(260, 115, 16, 26, 0, margin=3.0),      # Castle Chapel
        get_obb_corners(295, 110, 18, 32, 0, margin=3.0),      # Castle Palace
        get_obb_corners(130, 20, 24, 38, 0, margin=3.0),       # Fara Church
        get_obb_corners(-60, -90, 28, 42, 0, margin=3.0),      # Dominican Monastery
    ]

    placed_obb_corners = list(LANDMARKS_OBB)
    parcel_index = 1
    TARGET_PARCEL_COUNT = 580

    def try_create_parcel(px, pz, width, depth, orientation, district, street_name, is_shed=False, is_player=False):
        nonlocal parcel_index, craft_cycle_index
        if len(parcels) >= TARGET_PARCEL_COUNT:
            return False

        # SAT collision check against all landmarks and existing buildings
        margin = 1.8 if district == "krakow_suburb" else 1.2
        if is_shed:
            margin = 0.8
        corners = get_obb_corners(px, pz, width, depth, orientation, margin=margin)
        for existing in placed_obb_corners:
            if obb_overlap(corners, existing):
                return False

        placed_obb_corners.append(corners)
        p_id = f"p_{parcel_index:03d}"
        if is_player:
            p_id = "p_001_player_workshop"

        # Elevation calculation based on loess hill topography
        dist_to_castle = math.hypot(px - 280, pz - 90)
        if dist_to_castle < 70:
            elevation = round(6.5 + (1.0 - dist_to_castle / 70.0) * 3.5, 2)
        else:
            dist_to_center = math.hypot(px, pz)
            elevation = round(max(0.5, 4.2 - (dist_to_center / 220.0) * 3.8 + random.uniform(-0.2, 0.2)), 2)

        # Building type assignment
        b_type = pick_building_type(street_name, district, is_shed=is_shed)

        # Craft assignment
        has_craft = (not is_shed) and (random.random() < 0.52)
        craft_data = None
        if has_craft and not is_player:
            craft_data = CRAFTS[craft_cycle_index % len(CRAFTS)]
            craft_cycle_index += 1

        # Wealth class
        if district == "market_square":
            wealth = "patrician" if random.random() < 0.65 else "burgher"
        elif district == "castle_hill":
            wealth = "patrician" if random.random() < 0.4 else "burgher"
        elif district == "krakow_suburb":
            wealth = "artisan" if random.random() < 0.5 else "plebeian"
        else:
            wealth = craft_data["wealth"] if craft_data else random.choice(["burgher", "artisan", "plebeian"])

        # Parametric structural aging
        age = random.randint(3, 115)
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

        possible_clutter = ["firewood_rick", "oak_barrel", "leaning_ladder", "wicker_hoop", "cart_wheel", "handcart", "water_trough", "cask_stack"]
        clutter = random.sample(possible_clutter, random.randint(1, 4))
        scaffolding = (not is_shed) and (random.random() < 0.06)

        parcel_obj = {
            "id": p_id,
            "district": district,
            "streetName": street_name,
            "x": round(px, 2),
            "z": round(pz, 2),
            "width": width,
            "depth": depth,
            "orientation": float(round(orientation, 1)),
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
        }

        if is_player:
            parcel_obj["name"] = "Mistrzowski Warsztat Grzesznika (Player's Guild Workshop)"
            parcel_obj["isPlayerProperty"] = True
            parcel_obj["craft"] = {
                "id": "carpenter",
                "name": "Master Joiner & Cartwright",
                "sign": "Golden Compass & Framing Chisel",
                "guild": "Guild of Woodworkers"
            }
            parcel_obj["wealthClass"] = "artisan"

        parcels.append(parcel_obj)
        parcel_index += 1
        return True

    def generate_street_row(x1, z1, x2, z2, offset_dist, facing_side, district, street_name, step=None, w=None, d=None, add_courtyard=True):
        if district == "krakow_suburb":
            if step is None: step = 13.5
            if w is None: w = 8.5
            if d is None: d = 12.0
        else:
            if step is None: step = 10.4
            if w is None: w = 7.4
            if d is None: d = 11.0

        dx = x2 - x1
        dz = z2 - z1
        length = math.hypot(dx, dz)
        if length < 5: return 0
        tx, tz = dx / length, dz / length
        nx, nz = (-tz, tx) if facing_side > 0 else (tz, -tx)
        facing_angle = (math.degrees(math.atan2(-nx, -nz)) + 360) % 360

        cur_dist = step * 0.45
        added = 0
        while cur_dist < length - step * 0.35 and len(parcels) < TARGET_PARCEL_COUNT:
            px = x1 + tx * cur_dist + nx * offset_dist
            pz = z1 + tz * cur_dist + nz * offset_dist
            if try_create_parcel(px, pz, w, d, facing_angle, district, street_name):
                added += 1
                if add_courtyard and len(parcels) < TARGET_PARCEL_COUNT and random.random() < 0.65:
                    shed_dist = d * 0.5 + 4.5
                    shed_offset = offset_dist + (shed_dist if offset_dist >= 0 else -shed_dist)
                    spx = x1 + tx * cur_dist + nx * shed_offset
                    spz = z1 + tz * cur_dist + nz * shed_offset
                    try_create_parcel(spx, spz, 4.8, 5.8, facing_angle, district, f"{street_name} (Podwórze)", is_shed=True)
            cur_dist += step
        return added

    # 1. Special Parcel 1: Player's Guild Workshop in Kraków Suburb
    try_create_parcel(-235.0, -120.0, 10.0, 14.0, 45.0, "krakow_suburb", "Trakt Krakowski (Mistrzowski Warsztat)", is_player=True)

    # 2. Rynek (Market Square) Primary Frontages & Courtyards
    # North pierzeja (Z = 34, facing South towards plaza: 180 deg)
    # South pierzeja (Z = -34, facing North towards plaza: 0 deg)
    for x in [-30, -20, -10, 10, 20, 30]:
        try_create_parcel(x, 34, 7.5, 11.5, 180, "market_square", "Rynek (Północna Pierzeja)")
        try_create_parcel(x, -34, 7.5, 11.5, 0, "market_square", "Rynek (Południowa Pierzeja)")
        try_create_parcel(x, 50, 7.2, 10.5, 180, "market_square", "Zaułek Rynkowy Północny")
        try_create_parcel(x, 63, 5.0, 6.0, 180, "market_square", "Zaułek Rynkowy Północny (Oficyna)", is_shed=True)
        try_create_parcel(x, -50, 7.2, 10.5, 0, "market_square", "Zaułek Rynkowy Południowy")
        try_create_parcel(x, -63, 5.0, 6.0, 0, "market_square", "Zaułek Rynkowy Południowy (Oficyna)", is_shed=True)

    # West pierzeja (X = -44, facing East: 90 deg)
    # East pierzeja (X = 44, facing West: 270 deg)
    for z in [-20, -10, 0, 10, 20]:
        try_create_parcel(-44, z, 7.5, 11.5, 90, "market_square", "Rynek (Zachodnia Pierzeja)")
        try_create_parcel(44, z, 7.5, 11.5, 270, "market_square", "Rynek (Wschodnia Pierzeja)")
        try_create_parcel(-58, z, 7.2, 10.5, 90, "market_square", "Zaułek Rynkowy Zachodni")
        try_create_parcel(58, z, 7.2, 10.5, 270, "market_square", "Zaułek Rynkowy Wschodni")

    # 3. Bramowa Quarter (Kraków Gate to Rynek Arterial & Parallel Alleys)
    for off, side in [(8.0, 1), (-8.0, -1), (23.0, 1), (-23.0, -1)]:
        generate_street_row(-150, -75, -46, -24, off, side, "bramowa_quarter", "Ulica Bramowa")
    for off, side in [(8.0, 1), (-8.0, -1), (22.0, 1), (-22.0, -1)]:
        generate_street_row(-140, -50, -50, -5, off, side, "bramowa_quarter", "Ulica Szewska")
        generate_street_row(-130, -30, -60, 15, off, side, "bramowa_quarter", "Ulica Kozia")
        generate_street_row(-110, -10, -50, 25, off, side, "bramowa_quarter", "Ulica Olejna")

    # 4. Grodzka & Fara Quarters (Rynek to Grodzka Gate & Parish Square)
    for off, side in [(8.0, 1), (-8.0, -1), (23.0, 1), (-23.0, -1)]:
        generate_street_row(46, 18, 180, 20, off, side, "grodzka_quarter", "Ulica Grodzka")
    for off, side in [(8.0, 1), (-8.0, -1), (22.0, 1), (-22.0, -1)]:
        generate_street_row(70, 32, 160, 35, off, side, "grodzka_quarter", "Zaułek Ku Farze")
        generate_street_row(95, 5, 165, 8, off, side, "fara_quarter", "Plac Po Farze Południowy")

    # 5. Złota & Archidiakońska Quarters (South Old Town)
    for off, side in [(8.0, 1), (-8.0, -1), (23.0, 1), (-23.0, -1)]:
        generate_street_row(15, -34, 140, -52, off, side, "fara_quarter", "Ulica Złota / Archidiakońska")
    for off, side in [(8.0, 1), (-8.0, -1), (22.0, 1), (-22.0, -1)]:
        generate_street_row(-20, -70, 70, -90, off, side, "fara_quarter", "Ulica Bernardyńska")
        generate_street_row(-115, -115, 130, -75, off, side, "south_wall", "Podwale Południowe")
        generate_street_row(-30, -135, 70, -140, off, side, "south_wall", "Sady Podmurne")

    # 6. Dominikańska & Jezuicka Quarters
    for off, side in [(8.0, 1), (-8.0, -1), (23.0, 1), (-23.0, -1)]:
        generate_street_row(-40, -45, -85, -125, off, side, "dominican_quarter", "Ulica Dominikańska")
    for off, side in [(8.0, 1), (-8.0, -1), (22.0, 1), (-22.0, -1)]:
        generate_street_row(-135, -95, -70, -135, off, side, "dominican_quarter", "Ulica Jezuicka")

    # 7. North Wall & Rybna & Kowalska Quarters
    for off, side in [(8.0, 1), (-8.0, -1), (23.0, 1), (-23.0, -1)]:
        generate_street_row(-30, 36, 75, 68, off, side, "north_wall", "Ulica Rybna")
    for off, side in [(8.0, 1), (-8.0, -1), (22.0, 1), (-22.0, -1)]:
        generate_street_row(-75, 50, 115, 85, off, side, "north_wall", "Ulica Kowalska")
        generate_street_row(-40, 70, 60, 95, off, side, "north_wall", "Ulica Nowa / Krawiecka")
        generate_street_row(-100, 55, 150, 65, off, side, "north_wall", "Podwale Północne")

    # 8. Castle Hill Bailey (Podzamcze & Courtyard)
    for off, side in [(8.0, 1), (-8.0, -1), (22.0, 1), (-22.0, -1)]:
        generate_street_row(215, 40, 290, 52, off, side, "castle_hill", "Podzamcze Dolne")
        generate_street_row(245, 88, 310, 120, off, side, "castle_hill", "Dziedziniec Zamkowy")
        generate_street_row(225, 65, 275, 125, off, side, "castle_hill", "Stok Zamkowy Północny")
        generate_street_row(210, 15, 295, 30, off, side, "castle_hill", "Ogrody Podzamcza")

    # 9. Kraków Suburb (Spacious unwalled trade quarter)
    for off, side in [(9.0, 1), (-9.0, -1), (28.0, 1), (-28.0, -1), (48.0, 1), (-48.0, -1), (68.0, 1), (-68.0, -1)]:
        generate_street_row(-170, -85, -330, -145, off, side, "krakow_suburb", "Trakt Krakowski")
    for off, side in [(9.0, 1), (-9.0, -1), (28.0, 1), (-28.0, -1), (48.0, 1), (-48.0, -1)]:
        generate_street_row(-170, -40, -325, -45, off, side, "krakow_suburb", "Ulica Panny Marii")
        generate_street_row(-180, -10, -320, 25, off, side, "krakow_suburb", "Ulica Wieniawska")
        generate_street_row(-165, 35, -310, 55, off, side, "krakow_suburb", "Błonia Czechówki")
    for off, side in [(9.0, 1), (-9.0, -1), (28.0, 1), (-28.0, -1), (48.0, 1), (-48.0, -1)]:
        generate_street_row(-170, -120, -325, -180, off, side, "krakow_suburb", "Droga Nadwodna")
        generate_street_row(-195, -35, -255, -170, off, side, "krakow_suburb", "Zaułek Przedmiejski")
        generate_street_row(-240, -20, -315, -165, off, side, "krakow_suburb", "Droga Polna")
        generate_street_row(-185, -150, -320, -215, off, side, "krakow_suburb", "Zaułek Łąkowy")
        generate_street_row(-280, -30, -335, -190, off, side, "krakow_suburb", "Folwark Przedmiejski")
        generate_street_row(-210, -180, -330, -230, off, side, "krakow_suburb", "Bystrzyca Pastwiska")

    print(f"[CityPlanGenerator] Generated {len(parcels)} distinct parcel nodes.")

    # 3. Dedicated Medieval Greenery & Tree Placement (Strict Clearance Check)
    vegetation = []

    def dist_point_to_segment(px, pz, x1, z1, x2, z2):
        dx, dz = x2 - x1, z2 - z1
        seg_len_sq = dx * dx + dz * dz
        if seg_len_sq == 0:
            return math.hypot(px - x1, pz - z1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (pz - z1) * dz) / seg_len_sq))
        proj_x = x1 + t * dx
        proj_z = z1 + t * dz
        return math.hypot(px - proj_x, pz - proj_z)

    node_coords = {n["id"]: (n["x"], n["z"]) for n in street_nodes}
    street_segments = []
    for a_id, b_id in street_edges:
        if a_id in node_coords and b_id in node_coords:
            street_segments.append((node_coords[a_id][0], node_coords[a_id][1], node_coords[b_id][0], node_coords[b_id][1]))

    wall_segments = []
    for i in range(len(wall_points)):
        p1 = wall_points[i]
        p2 = wall_points[(i + 1) % len(wall_points)]
        wall_segments.append((p1["x"], p1["z"], p2["x"], p2["z"]))

    def is_tree_valid(tx, tz, tree_radius=3.8):
        # 1. Building clearance: distance to parcel center >= building half-diagonal + tree_radius + buffer
        for p in parcels:
            b_radius = math.hypot(p["width"], p["depth"]) * 0.5
            dist = math.hypot(tx - p["x"], tz - p["z"])
            if dist < b_radius + tree_radius + 2.0:
                return False

        # 2. Civic landmarks clearance
        for lmark in civic_landmarks:
            l_radius = math.hypot(lmark["width"], lmark["depth"]) * 0.5
            dist = math.hypot(tx - lmark["x"], tz - lmark["z"])
            if dist < l_radius + tree_radius + 2.5:
                return False

        for elm in castle_elements:
            if "x" in elm and "z" in elm:
                ew = elm.get("width", 14)
                ed = elm.get("depth", 14)
                c_radius = math.hypot(ew, ed) * 0.5
                if math.hypot(tx - elm["x"], tz - elm["z"]) < c_radius + tree_radius + 2.5:
                    return False

        # 3. Streets clearance (keep roads clear for carts)
        for x1, z1, x2, z2 in street_segments:
            if dist_point_to_segment(tx, tz, x1, z1, x2, z2) < tree_radius + 2.5:
                return False

        # 4. Defensive wall clearance
        for x1, z1, x2, z2 in wall_segments:
            if dist_point_to_segment(tx, tz, x1, z1, x2, z2) < tree_radius + 3.0:
                return False

        # 5. Tree-to-tree spacing
        for v in vegetation:
            if math.hypot(tx - v["x"], tz - v["z"]) < 5.8:
                return False

        return True

    def try_add_tree(tx, tz, zone_name):
        if is_tree_valid(tx, tz):
            scale = round(random.uniform(0.85, 1.35), 2)
            rot = round(random.uniform(0, 360), 1)
            vegetation.append({
                "id": f"tree_{len(vegetation) + 1:03d}",
                "type": "tree_oak",
                "x": round(tx, 2),
                "z": round(tz, 2),
                "scale": scale,
                "rotation": rot,
                "zone": zone_name
            })
            return True
        return False

    # Zone 1: Sady Podmurne (Southern Wall Orchards)
    for x in range(-55, 75, 12):
        for z in range(-150, -125, 10):
            try_add_tree(x + random.uniform(-2, 2), z + random.uniform(-2, 2), "sady_podmurne")

    # Zone 2: Ogrody Podzamcza (Castle Hill Terraces & Slopes)
    for x in range(200, 275, 14):
        for z in range(15, 55, 12):
            try_add_tree(x + random.uniform(-2, 2), z + random.uniform(-2, 2), "ogrody_podzamcza")
    for x in range(230, 290, 15):
        for z in range(125, 155, 12):
            try_add_tree(x + random.uniform(-2, 2), z + random.uniform(-2, 2), "ogrody_podzamcza")

    # Zone 3: Błonia Czechówki (Riverside Meadows North of Kraków Suburb)
    for x in range(-330, -165, 16):
        for z in range(35, 85, 14):
            try_add_tree(x + random.uniform(-3, 3), z + random.uniform(-3, 3), "blonia_czechowki")

    # Zone 4: Bystrzyca Pastwiska (Southern Grazing Commons)
    for x in range(-330, -170, 16):
        for z in range(-240, -185, 14):
            try_add_tree(x + random.uniform(-3, 3), z + random.uniform(-3, 3), "bystrzyca_pastwiska")

    # Zone 5: Suburban Backyard Gardens & Road Verges
    for _ in range(140):
        sx = random.uniform(-325, -175)
        sz = random.uniform(-180, 20)
        try_add_tree(sx, sz, "suburban_gardens")

    # Zone 6: Outer Green Verge & Promontory Glacis
    for _ in range(70):
        ang = random.uniform(0, math.pi * 2)
        dist = random.uniform(170, 260)
        rx = math.cos(ang) * dist
        rz = math.sin(ang) * dist
        try_add_tree(rx, rz, "outer_verge")

    print(f"[CityPlanGenerator] Placed {len(vegetation)} verified trees with 0 building/street collisions.")

    # 4. Living Autonomous Citizens (~1,500 citizens across households)
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

        # Watch, clergy and long-distance merchants of 1392 were men. The replacement name
        # comes from its own RNG so the main stream (every other citizen and parcel) is unchanged.
        if (is_visitor or is_guard or is_monk) and not is_male:
            is_male = True
            first_name = random.Random(c_idx).choice(FIRST_NAMES_MALE)
            full_name = f"{first_name} {surname}"

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

    assign_woodcutters(parcels, citizens)
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
        "vegetation": vegetation,
        "citizens": citizens,
        "bellHours": BELL_HOURS,
        "fairEvents": fair_events,
        "houseTypesCatalog": HOUSE_TYPES,
        "shedTypesCatalog": SHED_TYPES,
        "craftsCatalog": CRAFTS + [WOODCUTTER_CRAFT]
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
