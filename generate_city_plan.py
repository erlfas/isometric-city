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


# The Bystrzyca (south-east of the city). Mouth and source lie just off the ground plane
# (x -350..350, z -275..275) so the river runs off both map edges.
RIVER_START = (-140.0, -292.0)
RIVER_END = (366.0, -100.0)
RIVER_STEP = 3.0          # m between centreline samples
RIVER_CLEARANCE = 15.0    # m from the bank to any parcel, landmark, street or wall
RIVER_SEED = 1392_11


def _river_course(rng):
    """Centreline [(x, z)] in a local frame: start at the origin heading +x. The heading swings
    in half-bends of random length and amplitude (so S-bends differ), plus a slow drift."""
    pts = [(0.0, 0.0)]
    heading, phase = 0.0, 0.0
    half_len = rng.uniform(40, 80)    # m of arc per half-bend
    amp = rng.uniform(0.55, 1.2)     # rad of heading swing at the bend apex
    sign = rng.choice((-1, 1))
    drift = [(rng.uniform(0.06, 0.16), rng.uniform(380, 620), rng.uniform(0, 2 * math.pi)) for _ in range(2)]
    s = 0.0
    chord = math.hypot(RIVER_END[0] - RIVER_START[0], RIVER_END[1] - RIVER_START[1])
    while pts[-1][0] < chord:
        s += RIVER_STEP
        phase += math.pi * RIVER_STEP / half_len
        if phase >= math.pi:          # apex-to-apex done: next half-bend swings the other way
            phase -= math.pi
            sign = -sign
            half_len = rng.uniform(40, 80)
            amp = rng.uniform(0.55, 1.2)
        heading = sign * amp * math.sin(phase) + sum(a * math.sin(s / lam * 2 * math.pi + ph) for a, lam, ph in drift)
        x, z = pts[-1]
        pts.append((x + RIVER_STEP * math.cos(heading), z + RIVER_STEP * math.sin(heading)))
    return pts


def _chaikin(pts, iterations=2):
    for _ in range(iterations):
        out = [pts[0]]
        for (ax, az), (bx, bz) in zip(pts, pts[1:]):
            out.append((0.75 * ax + 0.25 * bx, 0.75 * az + 0.25 * bz))
            out.append((0.25 * ax + 0.75 * bx, 0.25 * az + 0.75 * bz))
        out.append(pts[-1])
        pts = out
    return pts


def _resample(pts, step):
    out = [pts[0]]
    need = step  # arc length still to go to the next sample
    for (ax, az), (bx, bz) in zip(pts, pts[1:]):
        seg = math.hypot(bx - ax, bz - az)
        pos = 0.0
        while seg - pos >= need:
            pos += need
            t = pos / seg
            out.append((ax + (bx - ax) * t, az + (bz - az) * t))
            need = step
        need -= seg - pos
    if math.hypot(out[-1][0] - pts[-1][0], out[-1][1] - pts[-1][1]) > step * 0.3:
        out.append(pts[-1])
    return out


def _river_widths(pts, rng):
    """9-14 m: a slow wobble along the course, wider where it bends (curvature, smoothed)."""
    n = len(pts)
    curv = [0.0] * n
    for i in range(1, n - 1):
        h1 = math.atan2(pts[i][1] - pts[i - 1][1], pts[i][0] - pts[i - 1][0])
        h2 = math.atan2(pts[i + 1][1] - pts[i][1], pts[i + 1][0] - pts[i][0])
        dh = (h2 - h1 + math.pi) % (2 * math.pi) - math.pi
        curv[i] = abs(dh) / RIVER_STEP
    k = 6
    smooth = [sum(curv[max(0, i - k):i + k + 1]) / len(curv[max(0, i - k):i + k + 1]) for i in range(n)]
    lam, ph = rng.uniform(180, 260), rng.uniform(0, 2 * math.pi)
    widths = []
    for i in range(n):
        w = 9.6 + 1.0 * math.sin(i * RIVER_STEP / lam * 2 * math.pi + ph) + 4.0 * max(0.0, min(1.0, (smooth[i] - 0.010) / 0.030))
        widths.append(round(max(9.0, min(14.0, w)), 2))
    return widths


def generate_river(parcels, landmarks, castle_elements, street_segments, wall_segments, seg_dist):
    """Seeded meander placed in the world by a similarity transform (start and end fixed).
    Tries successive seeds until the bank keeps RIVER_CLEARANCE from everything built."""
    obstacles = [(p["x"], p["z"], math.hypot(p["width"], p["depth"]) * 0.5) for p in parcels]
    obstacles += [(l["x"], l["z"], math.hypot(l["width"], l["depth"]) * 0.5) for l in landmarks]
    obstacles += [(e["x"], e["z"], math.hypot(e.get("width", 14), e.get("depth", 14)) * 0.5)
                  for e in castle_elements if "x" in e and "z" in e]
    segments = list(street_segments) + list(wall_segments)
    segments += [(e["startX"], e["startZ"], e["endX"], e["endZ"]) for e in castle_elements if "startX" in e]
    best = None
    for attempt in range(400):
        seed = RIVER_SEED + attempt
        rng = random.Random(seed)
        local = _river_course(rng)
        # Similarity transform: local start -> RIVER_START, local end -> RIVER_END.
        lx, lz = local[-1]
        wx, wz = RIVER_END[0] - RIVER_START[0], RIVER_END[1] - RIVER_START[1]
        scale = math.hypot(wx, wz) / math.hypot(lx, lz)
        rot = math.atan2(wz, wx) - math.atan2(lz, lx)
        c, s_ = math.cos(rot) * scale, math.sin(rot) * scale
        world = [(RIVER_START[0] + c * x - s_ * z, RIVER_START[1] + s_ * x + c * z) for x, z in local]
        pts = _resample(_chaikin(world), RIVER_STEP)
        widths = _river_widths(pts, rng)
        margin = float("inf")
        for (x, z), w in zip(pts, widths):
            for ox, oz, r in obstacles:
                if abs(ox - x) < 80 and abs(oz - z) < 80:
                    margin = min(margin, math.hypot(ox - x, oz - z) - r - w * 0.5)
            for x1, z1, x2, z2 in segments:
                margin = min(margin, seg_dist(x, z, x1, z1, x2, z2) - w * 0.5)
            if margin < RIVER_CLEARANCE:
                break
        if margin >= RIVER_CLEARANCE:
            best = (pts, widths, margin, seed)
            break
    if best is None:
        raise RuntimeError("no river seed keeps the clearance; move RIVER_START/RIVER_END")
    pts, widths, margin, seed = best
    length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
    river = {
        "name": "Bystrzyca",
        "flow": "downstream = increasing index",
        "lengthM": round(length, 1),
        "points": [{"x": round(x, 2), "z": round(z, 2), "width": w} for (x, z), w in zip(pts, widths)],
    }
    return river, margin, seed


# ------------------------------------------------------------------------------------------
# Riverside woods, footbridge and watermill (stage 4). Everything here draws from its own
# RNG (FOREST_SEED), so parcels, citizens and the older trees stay as generated; the mill
# parcel and its millers are appended after the citizens (add_watermill).
# ------------------------------------------------------------------------------------------
FOREST_SEED = 1392_13
MAP_HALF_X, MAP_HALF_Z = 350.0, 275.0   # the ground plane (three-renderer.ts)
MAP_INSET = 3.0                         # trees keep this far inside its edge
BRIDGE_LEN, BRIDGE_W = 18.0, 2.2        # build_footbridge: deck along local X, centred
BRIDGE_DECK_END, BRIDGE_DECK_MID = 0.15, 1.2
MILL_SETBACK = 7.0                      # house centre, inland from the water's edge
MILL_WHEEL_X = 4.9                      # build_watermill: wheel axle, house-local +X
MILL_WHEEL_Y = 1.7                      # axle height (the paddles dip into the race)
RACE_W = 1.8

# Footprint (crown) radius per model (build_assets.py, measured), for spacing.
VEG_RADIUS = {
    "tree_oak": 7.9, "tree_oak_b": 7.9, "tree_oak_c": 5.3, "tree_alder": 3.6, "tree_alder_b": 3.7,
    "tree_hornbeam": 5.3, "tree_lime": 6.1, "tree_willow": 3.6, "tree_willow_weeping": 6.3,
    "tree_birch": 2.8, "tree_birch_b": 3.8, "tree_pine": 5.8, "tree_pine_b": 6.3,
    "bush_hazel": 2.0, "bush_hawthorn": 1.7, "fern_clump": 1.0, "reed_clump": 1.1,
    "rock_boulder": 1.0, "rock_boulder_b": 1.6, "log_fallen": 3.3,
}
LEANS_TO_WATER = {"tree_willow_weeping", "tree_alder_b"}   # modelled leaning toward +X
GLADE = -100.0                          # generate_forest field(): inside a glade
BANK = -200.0                           # generate_forest field(): on an open river bank


class _ValueNoise:
    """Smooth 2D value noise in [-1, 1], one lattice point per `cell` m."""

    def __init__(self, rng, cell):
        self.cell = cell
        self.perm = list(range(256))
        rng.shuffle(self.perm)
        self.vals = [rng.uniform(-1.0, 1.0) for _ in range(256)]

    def _v(self, ix, iz):
        return self.vals[self.perm[(self.perm[ix & 255] + iz) & 255]]

    def __call__(self, x, z):
        fx, fz = x / self.cell, z / self.cell
        ix, iz = math.floor(fx), math.floor(fz)
        tx, tz = fx - ix, fz - iz
        sx, sz = tx * tx * (3 - 2 * tx), tz * tz * (3 - 2 * tz)
        a, b, c, d = self._v(ix, iz), self._v(ix + 1, iz), self._v(ix, iz + 1), self._v(ix + 1, iz + 1)
        return a + (b - a) * sx + (c - a) * sz + (a - b - c + d) * sx * sz


class _Fbm:
    def __init__(self, rng, cell, octaves=3):
        self.layers = [(_ValueNoise(rng, cell / 2 ** k), 0.5 ** k) for k in range(octaves)]
        self.norm = 1.0 / sum(w for _, w in self.layers) * 1.6   # roughly back to [-1, 1]

    def __call__(self, x, z):
        return max(-1.0, min(1.0, sum(n(x, z) * w for n, w in self.layers) * self.norm))


def _river_frames(river):
    """Per point: x, z, width, unit normal left of the flow (nx, nz), tangent, smoothed
    curvature (> 0 = turning toward +n). Same as river-course.ts riverFrames."""
    p = river["points"]
    n = len(p)
    out, raw = [], [0.0] * n
    for i in range(n):
        a, b = p[max(0, i - 1)], p[min(n - 1, i + 1)]
        dx, dz = b["x"] - a["x"], b["z"] - a["z"]
        ln = math.hypot(dx, dz) or 1.0
        out.append({"x": p[i]["x"], "z": p[i]["z"], "w": p[i]["width"], "tx": dx / ln, "tz": dz / ln,
                    "nx": -dz / ln, "nz": dx / ln, "curv": 0.0})
        if 0 < i < n - 1:
            h1 = math.atan2(p[i]["z"] - p[i - 1]["z"], p[i]["x"] - p[i - 1]["x"])
            h2 = math.atan2(p[i + 1]["z"] - p[i]["z"], p[i + 1]["x"] - p[i]["x"])
            dh = (h2 - h1 + math.pi) % (2 * math.pi) - math.pi
            raw[i] = dh / (math.hypot(p[i + 1]["x"] - p[i]["x"], p[i + 1]["z"] - p[i]["z"]) or 1.0)
    for i in range(n):
        win = raw[max(0, i - 6):i + 7]
        out[i]["curv"] = sum(win) / len(win)
    return out


class _RiverIndex:
    """Distance to the water's edge (negative in the water), the side (+1 = left of the flow,
    the town side; -1 = the far bank), the nearest point index and its curvature."""
    REACH = 60.0
    CELL = 16.0

    def __init__(self, frames):
        self.f = frames
        self.cells = {}
        c, r = self.CELL, self.REACH
        for i in range(len(frames) - 1):
            a, b = frames[i], frames[i + 1]
            for cx in range(math.floor((min(a["x"], b["x"]) - r) / c), math.floor((max(a["x"], b["x"]) + r) / c) + 1):
                for cz in range(math.floor((min(a["z"], b["z"]) - r) / c), math.floor((max(a["z"], b["z"]) + r) / c) + 1):
                    self.cells.setdefault((cx, cz), []).append(i)
        # Far bank: right of the flow, closed off past the map's south and east edges.
        self.far_poly = [(f["x"], f["z"]) for f in frames] + [(frames[-1]["x"] + 60, frames[-1]["z"]),
                                                              (frames[-1]["x"] + 60, -400.0), (frames[0]["x"], -400.0)]

    def query(self, x, z):
        best = (self.REACH, 0, -1, 0.0)
        for i in self.cells.get((math.floor(x / self.CELL), math.floor(z / self.CELL)), ()):
            a, b = self.f[i], self.f[i + 1]
            dx, dz = b["x"] - a["x"], b["z"] - a["z"]
            L2 = dx * dx + dz * dz or 1e-9
            t = max(0.0, min(1.0, ((x - a["x"]) * dx + (z - a["z"]) * dz) / L2))
            px, pz = a["x"] + dx * t, a["z"] + dz * t
            d = math.hypot(x - px, z - pz) - 0.5 * (a["w"] + (b["w"] - a["w"]) * t)
            if d < best[0]:
                side = 1 if (x - px) * a["nx"] + (z - pz) * a["nz"] >= 0 else -1
                best = (d, side, i if t < 0.5 else i + 1, a["curv"])
        if best[2] < 0:
            best = (self.REACH, -1 if self.far(x, z) else 1, -1, 0.0)
        return best

    def far(self, x, z):
        inside, poly = False, self.far_poly
        for k in range(len(poly)):
            (ax, az), (bx, bz) = poly[k], poly[k - 1]
            if (az > z) != (bz > z) and x < ax + (z - az) * (bx - ax) / (bz - az):
                inside = not inside
        return inside


class _Clearance:
    """Distance (capped at REACH) from a point to anything built: parcels, landmarks and
    castle buildings (circles of their half-diagonal), streets, walls and castle walls."""
    REACH = 45.0
    CELL = 20.0

    def __init__(self, circles, segments, seg_dist):
        self.seg_dist = seg_dist
        self.cells = {}
        c, r = self.CELL, self.REACH
        for item in [("c",) + tuple(o) for o in circles] + [("s",) + tuple(s) for s in segments]:
            if item[0] == "c":
                x0, z0, x1, z1 = item[1] - item[3], item[2] - item[3], item[1] + item[3], item[2] + item[3]
            else:
                x0, x1 = min(item[1], item[3]), max(item[1], item[3])
                z0, z1 = min(item[2], item[4]), max(item[2], item[4])
            for cx in range(math.floor((x0 - r) / c), math.floor((x1 + r) / c) + 1):
                for cz in range(math.floor((z0 - r) / c), math.floor((z1 + r) / c) + 1):
                    self.cells.setdefault((cx, cz), []).append(item)

    def __call__(self, x, z):
        best = self.REACH
        for it in self.cells.get((math.floor(x / self.CELL), math.floor(z / self.CELL)), ()):
            d = (math.hypot(x - it[1], z - it[2]) - it[3]) if it[0] == "c" else self.seg_dist(x, z, *it[1:])
            if d < best:
                best = d
        return best


def _smooth_path(ctrl, rng, wobble, step=2.0):
    """Chaikin-rounded polyline through `ctrl`, resampled every `step` m, with a gentle
    sideways wander (a trodden path never runs ruler-straight)."""
    pts = _resample(_chaikin(ctrl, 3), step)
    if wobble <= 0 or len(pts) < 3:
        return pts
    lam, ph, lam2, ph2 = rng.uniform(25, 45), rng.uniform(0, 6.3), rng.uniform(9, 15), rng.uniform(0, 6.3)
    out, s = [pts[0]], 0.0
    for k in range(1, len(pts) - 1):
        (ax, az), (bx, bz) = pts[k - 1], pts[k + 1]
        ln = math.hypot(bx - ax, bz - az) or 1.0
        s += step
        fade = min(1.0, k / 4.0, (len(pts) - 1 - k) / 4.0)    # ends stay put
        o = wobble * fade * (0.75 * math.sin(s / lam * 6.283 + ph) + 0.25 * math.sin(s / lam2 * 6.283 + ph2))
        out.append((pts[k][0] - (bz - az) / ln * o, pts[k][1] + (bx - ax) / ln * o))
    out.append(pts[-1])
    return out


def _seg_dist(px, pz, x1, z1, x2, z2):
    dx, dz = x2 - x1, z2 - z1
    L2 = dx * dx + dz * dz
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - x1) * dx + (pz - z1) * dz) / L2))
    return math.hypot(px - x1 - dx * t, pz - z1 - dz * t)


def _polyline_dist(x, z, pts):
    return min(_seg_dist(x, z, a[0], a[1], b[0], b[1]) for a, b in zip(pts, pts[1:]))


def plan_river_crossing(river, frames, clearance, rng):
    """Footbridge, watermill site and the paths to them (geometry only; the mill parcel is
    added after the citizens by add_watermill). Writes river['crossings'] and
    river['mills']; returns (paths, mill_site)."""
    n = len(frames)
    # Bridge: a narrow, straight reach with ground on both sides, in the middle third of
    # the course (the town is close there and the far bank has room for the woods).
    best = None
    for i in range(n // 3, 2 * n // 3):
        f = frames[i]
        if not (40 < f["x"] < 160):
            continue
        straight = max(abs(frames[k]["curv"]) for k in range(i - 3, i + 4))
        score = f["w"] + 220 * straight
        if best is None or score < best[0]:
            best = (score, i)
    bi = best[1]
    b = frames[bi]
    half = BRIDGE_LEN * 0.5
    north = (b["x"] + b["nx"] * half, b["z"] + b["nz"] * half)
    south = (b["x"] - b["nx"] * half, b["z"] - b["nz"] * half)
    angle = math.degrees(math.atan2(b["nz"], b["nx"]))
    river["crossings"] = [{
        "id": "most_bystrzycki", "name": "Most Bystrzycki (footbridge)", "model": "footbridge",
        "x": round(b["x"], 2), "z": round(b["z"], 2),
        "angle": round(angle, 2),            # deck axis direction in x-z (deg), town end = +
        "length": BRIDGE_LEN, "width": BRIDGE_W,
        "deckEnd": BRIDGE_DECK_END, "deckMid": BRIDGE_DECK_MID,
        "riverIndex": bi,
    }]

    # Mill: on the outside of the next bend downstream that turns toward the town (its
    # outside is the far bank, where the current runs fastest and deepest).
    mi = max(range(bi + 7, min(n - 8, bi + 22)), key=lambda k: frames[k]["curv"])
    m = frames[mi]
    off = m["w"] * 0.5 + MILL_SETBACK
    hx, hz = m["x"] - m["nx"] * off, m["z"] - m["nz"] * off
    rot = math.degrees(math.atan2(-m["nz"], m["nx"]))   # house-local +X (wheel side) -> the river
    wheel = (hx + m["nx"] * MILL_WHEEL_X, hz + m["nz"] * MILL_WHEEL_X)
    # Mill race: leaves the river upstream, runs along the bank behind a strip of earth,
    # past the wheel, and falls back in just below it.
    race = []
    for k in range(mi - 9, mi + 6):
        f = frames[k]
        if k <= mi:
            t = min(1.0, (k - (mi - 9)) / 4.0)
        else:
            t = 1.0 - max(0.0, (k - (mi + 2)) / 3.0)
        t = t * t * (3 - 2 * t)
        lat = (f["w"] * 0.5 - 0.8) + t * (off - MILL_WHEEL_X - (f["w"] * 0.5 - 0.8) + (f["w"] - m["w"]) * 0.5)
        race.append({"x": round(f["x"] - f["nx"] * lat, 2), "z": round(f["z"] - f["nz"] * lat, 2), "width": RACE_W})
    mill_site = {"x": round(hx, 2), "z": round(hz, 2), "orientation": round(rot, 1), "riverIndex": mi}
    river["mills"] = [{"parcelId": "p_watermill_bystrzyca", "riverIndex": mi,
                       "wheel": {"x": round(wheel[0], 2), "z": round(wheel[1], 2), "y": MILL_WHEEL_Y},
                       "race": race}]

    # Paths. 1: from the Kraków gate along the meadow under the south wall, over the bridge.
    def out(p, d):
        return (p[0] + b["nx"] * d, p[1] + b["nz"] * d)
    town = [(-163.0, -88.0), (-150.0, -106.0), (-139.0, -133.0), (-118.0, -154.0), (-75.0, -164.0), (-30.0, -168.0),
            (20.0, -166.0), (out(north, 14)[0] - 14, out(north, 14)[1] + 2), out(north, 7), out(north, 2), north]
    p_town = _smooth_path(town, rng, 1.6)
    # 2: off the far end, into the woods to the south edge of the map.
    s0 = out(south, -3)
    deep = [south, s0, out(south, -9), (s0[0] - 8, s0[1] - 30), (s0[0] + 6, s0[1] - 52), (s0[0] - 4, -MAP_HALF_Z - 6)]
    p_deep = _smooth_path(deep, rng, 2.2)
    # 3: from the bridge's far end along the bank to the mill's loading dock, which faces
    #    upstream (build_watermill: dock at Blender -Y = house-local +Z = upstream here).
    dock = (hx - m["tx"] * 13.0, hz - m["tz"] * 13.0)
    j = p_deep[min(len(p_deep) - 1, 5)]
    mid = ((j[0] + dock[0]) / 2 - m["nx"] * 3, (j[1] + dock[1]) / 2 - m["nz"] * 3)
    p_mill = _smooth_path([j, mid, dock], rng, 0.8)
    # 4: a ride from the mill yard east through the far-bank woods, ~45 m in from the water
    #    (offset points that double back on the inside of a bend are dropped).
    yard = (hx - m["nx"] * 9.0, hz - m["nz"] * 9.0)
    ride = [dock, (dock[0] - m["nx"] * 8, dock[1] - m["nz"] * 8), yard]
    for k in range(mi + 10, n, 12):
        f = frames[k]
        o = f["w"] * 0.5 + 42 + 10 * math.sin(k * 0.21)
        x, z = f["x"] - f["nx"] * o, f["z"] - f["nz"] * o
        if x < ride[-1][0] + 10:
            continue
        if x > MAP_HALF_X + 6:
            ride.append((x, z))
            break
        ride.append((x, max(-MAP_HALF_Z + 8, z)))
    p_ride = _smooth_path(ride, rng, 2.5)
    rnd = lambda pts: [{"x": round(x, 2), "z": round(z, 2)} for x, z in pts]
    paths = [
        {"id": "path_bridge", "kind": "footpath", "width": 1.8, "points": rnd(p_town)},
        {"id": "path_woods", "kind": "footpath", "width": 1.6, "points": rnd(p_deep)},
        {"id": "path_mill", "kind": "track", "width": 2.4, "points": rnd(p_mill)},
        {"id": "ride_east", "kind": "ride", "width": 3.0, "points": rnd(p_ride)},
    ]
    return paths, mill_site


def generate_forest(river, frames, paths, mill_site, clearance, old_trees):
    """Riverside woods: a dart-throwing Poisson-disc sample of trees inside a noise-shaped
    mask around the Bystrzyca, species by distance to the water, then undergrowth, reeds,
    stones and dead wood. Returns the new vegetation entries (ids veg_NNNN)."""
    rng = random.Random(FOREST_SEED)
    rivx = _RiverIndex(frames)
    band_n = _Fbm(rng, 90.0, 3)      # how far the woods reach toward the town
    meadow_n = _Fbm(rng, 60.0, 2)    # the meadow strip's width
    glade_n = _Fbm(rng, 85.0, 3)     # clearings and glades
    stand_a = _Fbm(rng, 110.0, 2)    # stands: oak vs hornbeam
    stand_b = _Fbm(rng, 70.0, 2)     # lime / pine patches
    fern_n = _Fbm(rng, 18.0, 2)      # fern and reed beds
    dense_n = _Fbm(rng, 30.0, 2)     # thicket vs open wood
    cross = river["crossings"][0]
    ca = math.radians(cross["angle"])
    bx0, bz0 = cross["x"] + math.cos(ca) * (cross["length"] * 0.5 + 3), cross["z"] + math.sin(ca) * (cross["length"] * 0.5 + 3)
    bx1, bz1 = cross["x"] - math.cos(ca) * (cross["length"] * 0.5 + 3), cross["z"] - math.sin(ca) * (cross["length"] * 0.5 + 3)
    path_pts = [([(p["x"], p["z"]) for p in path["points"]], path["width"]) for path in paths]
    race = [(p["x"], p["z"]) for p in river["mills"][0]["race"]]
    mx, mz = mill_site["x"], mill_site["z"]
    # Open banks: stretches of water meadow, gravel and grass where the woods stand back from
    # the river (the water and the animals at it can be seen from the usual camera), wider on
    # the inside of bends (point bars). Noise along the course, its own RNG and one per bank.
    bank_rng = random.Random(FOREST_SEED + 7)
    bank_n = {1: _ValueNoise(bank_rng, 55.0), -1: _ValueNoise(bank_rng, 55.0)}
    bank_n2 = {1: _ValueNoise(bank_rng, 19.0), -1: _ValueNoise(bank_rng, 19.0)}
    bank_w = {}
    for side_ in (1, -1):
        for k, f in enumerate(frames):
            s = k * RIVER_STEP
            n = bank_n[side_](s, 0.5) * 0.8 + bank_n2[side_](s, 0.5) * 0.35
            inside = max(0.0, min(1.0, side_ * f["curv"] / 0.035))
            w = 0.0
            if n > -0.05:
                w = 7.0 + 26.0 * max(0.0, min(1.0, (n + 0.05) / 0.55))
            w += 20.0 * inside * (1.0 if n > -0.45 else 0.3)
            bank_w[(k, side_)] = w

    def open_bank(i, side):
        return bank_w.get((i, side), 0.0)

    def kept_clear(x, z, r_crown, under):
        """Bridge, mill yard, race and paths: trees may overhang a path with a crown, not a trunk."""
        if _seg_dist(x, z, bx0, bz0, bx1, bz1) < (2.0 if under else 3.5 + r_crown * 0.4):
            return False
        if math.hypot(x - mx, z - mz) < (12.0 if under else 14.0 + r_crown * 0.5):
            return False
        if _polyline_dist(x, z, race) < (1.6 if under else 2.5 + r_crown * 0.4):
            return False
        for pts, w in path_pts:
            if abs(x - pts[0][0]) > 400:
                continue
            if _polyline_dist(x, z, pts) < w * 0.5 + (0.6 if under else 1.0 + r_crown * 0.35):
                return False
        return True

    def field(x, z):
        """Woodland strength: > 0 inside the woods, ~0..0.4 = the ragged edge."""
        d, side, i, curv = rivx.query(x, z)
        built = clearance(x, z)
        f_meadow = (built - (24.0 + 9.0 * meadow_n(x, z))) / 10.0
        if side > 0:
            f_band = ((34.0 + 20.0 * band_n(x, z)) - d) / 12.0
        else:
            f_band = 1.5
        f_glade = (glade_n(x, z) + 0.55) / 0.22
        if d < 14.0:   # alders and willows line the water even through a glade
            f_glade = max(f_glade, (14.0 - d) / 5.0)
        f_edge = min(MAP_HALF_X - abs(x), MAP_HALF_Z - abs(z)) / 4.0
        rest = min(f_meadow, f_band, f_edge, 2.0)
        if i >= 0 and d > 0:
            w_open = open_bank(i, side)
            if w_open > 0:
                f_bank = (d - w_open) / 7.0
                if f_bank <= 0:
                    return BANK, d, side, i, curv           # water meadow: open sky over the bank
                rest = min(rest, f_bank)
        if f_glade <= 0 < rest - 0.3:
            return GLADE, d, side, i, curv              # inside a glade: lone trees only
        return max(GLADE + 1.0, min(rest, f_glade)), d, side, i, curv

    def pick_species(x, z, d, side, F, r):
        w = {}
        if d < 3.0:
            w = {"tree_willow_weeping": 3.0, "tree_willow": 3.0, "tree_alder": 3.0, "tree_alder_b": 3.0}
        elif d < 13.0:
            k = (d - 3.0) / 10.0
            w = {"tree_willow": 3.0 * (1 - k) + 0.4, "tree_willow_weeping": 2.0 * (1 - k) + 0.2,
                 "tree_alder": 4.0, "tree_alder_b": 2.0 * (1 - k) + 0.3, "tree_birch": 0.6,
                 "tree_hornbeam": 1.2 * k, "tree_oak_c": 0.8 * k}
        else:
            sa, sb = stand_a(x, z), stand_b(x, z)
            far = 1.0 if side < 0 else 0.15
            pine = far * max(0.0, min(1.0, (d - 22.0) / 30.0)) * max(0.0, 0.5 + sb * 1.4) * 9.0
            w = {"tree_oak": 2.2 * (1 + sa), "tree_oak_b": 1.6 * (1 + sa), "tree_oak_c": 1.6 * (1 + sa * 0.5),
                 "tree_hornbeam": 3.4 * (1 - sa), "tree_lime": 2.0 * max(0.1, 1 + sb * 1.6) * (1 - 0.5 * sa),
                 "tree_birch": 0.7, "tree_birch_b": 0.5, "tree_alder": 1.2 * max(0.0, 1 - (d - 13) / 10),
                 "tree_pine": pine * 0.55, "tree_pine_b": pine * 0.45}
        if F < 0.45:   # the edge and glade rims: light-loving birch
            w["tree_birch"] = w.get("tree_birch", 0) + 3.0
            w["tree_birch_b"] = w.get("tree_birch_b", 0) + 2.2
            w["tree_oak_c"] = w.get("tree_oak_c", 0) + 1.0
        names = sorted(k for k, v in w.items() if v > 0)
        tot = sum(w[k] for k in names)
        u = r.random() * tot
        for k in names:
            u -= w[k]
            if u <= 0:
                return k
        return names[-1]

    # Spatial hash of everything placed (old trees too): (x, z, radius, kind).
    G = 6.0
    grid = {}

    def add(x, z, r, kind):
        grid.setdefault((math.floor(x / G), math.floor(z / G)), []).append((x, z, r, kind))

    def near(x, z, reach):
        k = math.ceil(reach / G)
        gx, gz = math.floor(x / G), math.floor(z / G)
        for cx in range(gx - k, gx + k + 1):
            for cz in range(gz - k, gz + k + 1):
                yield from grid.get((cx, cz), ())

    for t in old_trees:
        add(t["x"], t["z"], 4.0 * t.get("scale", 1.0), "tree")

    out = []

    def emit(kind, x, z, scale, rot, zone):
        out.append({"id": f"veg_{len(out) + 1:04d}", "type": kind, "x": round(x, 2), "z": round(z, 2),
                    "scale": round(scale, 2), "rotation": round(rot % 360.0, 1), "zone": zone})

    def toward_water(x, z, i, jitter):
        """Rotation (deg) that turns a model's +X lean toward the river."""
        f = frames[i]
        px, pz = f["x"] - x, f["z"] - z
        return math.degrees(math.atan2(-pz, px)) + jitter

    xmin = min(f["x"] for f in frames) - 70
    xmax = min(MAP_HALF_X, max(f["x"] for f in frames) + 70)
    zmin, zmax = -MAP_HALF_Z, max(f["z"] for f in frames) + 70

    # 1. Trees: darts in random order; each takes its species' crown and keeps
    #    0.58 x (r_i + r_j) from the others, so crowns touch and overlap a little.
    K_TREE = 0.58
    trees = []
    for _ in range(90000):
        x, z = rng.uniform(xmin, xmax), rng.uniform(zmin, zmax)
        if abs(x) > MAP_HALF_X - MAP_INSET or abs(z) > MAP_HALF_Z - MAP_INSET:
            continue
        F, d, side, i, curv = field(x, z)
        lone = F == GLADE or F == BANK
        if F == BANK:
            # Water meadows: a lone willow or alder now and then, mostly near the water.
            if rng.random() > (0.02 if d < 5 else 0.004):
                continue
            kind = rng.choice(("tree_willow", "tree_willow_weeping", "tree_alder", "tree_alder_b", "tree_alder"))
        elif lone:
            # Glades: now and then a lone veteran oak, lime or birch standing in the grass.
            if rng.random() > 0.035:
                continue
            kind = rng.choice(("tree_oak", "tree_oak_b", "tree_oak", "tree_lime", "tree_birch_b", "tree_pine_b" if side < 0 else "tree_oak_b"))
        elif F <= 0 or d < 0.4:
            continue
        # Thinner toward the edge, and open wood vs thicket in patches.
        elif rng.random() > min(1.0, 0.25 + F * 0.9) * (0.72 + 0.28 * dense_n(x, z)):
            continue
        else:
            kind = pick_species(x, z, d, side, F, rng)
        if d < 1.6 and kind not in ("tree_willow", "tree_willow_weeping", "tree_alder", "tree_alder_b"):
            continue
        s = rng.uniform(1.0, 1.15) if lone else rng.uniform(0.85, 1.15)
        r = VEG_RADIUS[kind] * s
        if not kept_clear(x, z, r, False):
            continue
        ok = True
        for (ox, oz, orad, ok_kind) in near(x, z, r + 9.5):
            if ok_kind == "tree" and math.hypot(x - ox, z - oz) < K_TREE * (r + orad):
                ok = False
                break
        if not ok:
            continue
        add(x, z, r, "tree")
        if kind in LEANS_TO_WATER and i >= 0 and d < 14:
            rot = toward_water(x, z, i, rng.uniform(-30, 30))
        else:
            rot = rng.uniform(0, 360)
        zone = "water_meadow" if F == BANK else "glade" if lone else "riverbank" if d < 13 else ("far_woods" if side < 0 else "near_woods")
        trees.append((x, z, r, kind))
        emit(kind, x, z, s, rot, zone)

    def canopy(x, z):
        """How covered (x, z) is: 1 under a crown's middle, 0 in the open."""
        c = 0.0
        for (ox, oz, orad, k) in near(x, z, 9.5):
            if k == "tree":
                c = max(c, 1.0 - math.hypot(x - ox, z - oz) / (orad * 0.9))
        return c

    def free(x, z, r, gap_tree):
        for (ox, oz, orad, k) in near(x, z, r + 9.5):
            dd = math.hypot(x - ox, z - oz)
            if k == "tree":
                if dd < gap_tree:
                    return False
            elif dd < 0.8 * (r + orad):
                return False
        return True

    # 2. Shrubs: hazel and hawthorn where light reaches: the woods' edge, glade rims, gaps.
    for _ in range(26000):
        x, z = rng.uniform(xmin, xmax), rng.uniform(zmin, zmax)
        if abs(x) > MAP_HALF_X - 2 or abs(z) > MAP_HALF_Z - 2:
            continue
        F, d, side, i, curv = field(x, z)
        if (F < -0.25 and not (F == GLADE and rng.random() < 0.07)) or d < 2.0:   # glades: a stray thorn bush
            continue
        cov = canopy(x, z)
        light = (1.0 - cov) * (1.0 if F < 0.6 else 0.45)
        if rng.random() > light * 0.55:
            continue
        kind = "bush_hawthorn" if (F < 0.3 and rng.random() < 0.55) or rng.random() < 0.2 else "bush_hazel"
        s = rng.uniform(0.8, 1.2)
        r = VEG_RADIUS[kind] * s
        if not kept_clear(x, z, r, True) or not free(x, z, r, 2.2):
            continue
        add(x, z, r, "shrub")
        emit(kind, x, z, s, rng.uniform(0, 360), "woods_edge" if F < 0.6 else "understory")

    # 3. Ferns: beds under the canopy (shade, moist ground), clumped by noise.
    for _ in range(40000):
        x, z = rng.uniform(xmin, xmax), rng.uniform(zmin, zmax)
        if abs(x) > MAP_HALF_X - 2 or abs(z) > MAP_HALF_Z - 2:
            continue
        fn = fern_n(x, z)
        if fn < 0.0 or rng.random() > fn * 1.6:
            continue
        F, d, side, i, curv = field(x, z)
        if F < 0.3 or d < 1.0:
            continue
        if canopy(x, z) < 0.25:
            continue
        s = rng.uniform(0.75, 1.3)
        r = VEG_RADIUS["fern_clump"] * s
        if not kept_clear(x, z, r, True) or not free(x, z, r, 0.9):
            continue
        add(x, z, r, "fern")
        emit("fern_clump", x, z, s, rng.uniform(0, 360), "understory")

    # 4. Reeds in the shallows: beds along both banks, thickest on the inside of bends
    #    (slack water and gravel), none on the cut bank of a sharp outside bend.
    for i in range(len(frames)):
        f = frames[i]
        for sgn in (1, -1):
            inside = sgn * f["curv"] > 0
            bend = min(1.0, abs(f["curv"]) / 0.04)
            for k in range(3):
                along = (k / 3.0) * 3.0 - 1.5 + rng.uniform(-0.5, 0.5)
                lat = f["w"] * 0.5 + rng.uniform(-1.9, 0.5) + (rng.uniform(-1.6, 0) * bend if inside else 0)
                x = f["x"] + f["tx"] * along + f["nx"] * sgn * lat
                z = f["z"] + f["tz"] * along + f["nz"] * sgn * lat
                if abs(x) > MAP_HALF_X - 1 or abs(z) > MAP_HALF_Z - 1:
                    continue
                bed = fern_n(x * 1.7 + 40, z * 1.7)
                p = 0.25 + 0.45 * bed + (0.45 * bend if inside else -0.3 * bend)
                if rng.random() > p:
                    continue
                if clearance(x, z) < 12:
                    continue
                s = rng.uniform(0.75, 1.25)
                r = VEG_RADIUS["reed_clump"] * s
                if not kept_clear(x, z, r, True) or not free(x, z, r, 0.0):
                    continue
                add(x, z, r * 0.8, "reed")
                emit("reed_clump", x, z, s, rng.uniform(0, 360), "shallows")

    # 5. Stones and dead wood: a few boulders in and at the water, more in the woods; logs
    #    under the canopy.
    for _ in range(2600):
        x, z = rng.uniform(xmin, xmax), rng.uniform(zmin, zmax)
        if abs(x) > MAP_HALF_X - 3 or abs(z) > MAP_HALF_Z - 3:
            continue
        F, d, side, i, curv = field(x, z)
        in_water = -3.0 < d < 0.8
        if not in_water and (F < 0.2 or rng.random() > 0.25):
            continue
        if in_water and rng.random() > 0.12:
            continue
        cov = canopy(x, z)
        if not in_water and cov > 0.35 and rng.random() < 0.5:
            kind = "log_fallen"
        else:
            kind = "rock_boulder" if rng.random() < 0.55 else "rock_boulder_b"
        s = rng.uniform(0.7, 1.3)
        r = VEG_RADIUS[kind] * s
        if not kept_clear(x, z, r, True) or not free(x, z, r, 1.2 if kind == "log_fallen" else 0.9):
            continue
        add(x, z, r, "stone")
        emit(kind, x, z, s, rng.uniform(0, 360), "in_water" if in_water else "forest_floor")
    return out


def retype_old_trees(vegetation):
    """The older trees outside the woods were all one oak. Orchards stay oak (fruit trees
    read as oaks at this scale); verges, meadows and gardens get a mix, by a hash of the id
    so the choice is stable."""
    mix = {
        "outer_verge": ["tree_oak", "tree_oak_b", "tree_lime", "tree_hornbeam", "tree_birch", "tree_oak_c"],
        "blonia_czechowki": ["tree_willow", "tree_alder", "tree_oak_b", "tree_willow", "tree_birch_b", "tree_oak"],
        "bystrzyca_pastwiska": ["tree_oak_b", "tree_oak", "tree_lime", "tree_birch"],
        "suburban_gardens": ["tree_oak_c", "tree_lime", "tree_oak", "tree_birch"],
    }
    for v in vegetation:
        choices = [c for c in mix.get(v.get("zone", ""), []) if c in VEG_RADIUS]
        if choices:
            h = sum((k + 1) * ord(ch) for k, ch in enumerate(v["id"]))
            v["type"] = choices[h % len(choices)]


MILLER_CRAFT = {"id": "miller", "name": "Miller", "sign": "Millstone & Wheat Sheaf", "guild": "Millers & Bakers",
                "wealth": "plebeian"}
MILLERS = 3


def add_watermill(parcels, citizens, site):
    """Append the watermill parcel and move a few labouring men to it (own RNG, after the
    citizens, so every existing parcel and citizen keeps its id and content)."""
    rng = random.Random(FOREST_SEED + 1)
    mill = {
        "id": "p_watermill_bystrzyca", "district": "krakow_suburb", "streetName": "Brzeg Bystrzycy",
        "x": site["x"], "z": site["z"], "width": 8.5, "depth": 12.0, "orientation": site["orientation"],
        "elevation": 0.0, "buildingType": "riverside_watermill", "isShed": False, "craft": MILLER_CRAFT,
        "aging": {"ageYears": 46, "ridgeSag": 0.12, "wallLeanAngle": 0.6, "woodGraying": 0.55,
                  "mossFoundation": 0.82, "maintenanceState": "weathered"},
        "clutter": ["oak_barrel", "handcart"], "scaffolding": False, "wealthClass": "artisan",
        "residents": [], "workplaceFor": [],
        "commodities": {"rye_sacks": 24, "salted_herring_kilderkins": 0, "tallow_candles": 8, "grosze": 140},
        "name": "Młyn nad Bystrzycą (Bystrzyca Watermill)",
    }
    by_id = {p["id"]: p for p in parcels}
    pool = [c for c in citizens if c["gender"] == "male" and c["wealthClass"] == "plebeian"
            and c["guildRank"] in ("journeyman", "laborer") and c["trade"] not in ("Woodcutter",)
            and c["workParcelId"] in by_id]
    # Men living nearest the mill walk there; pick among the closest few.
    pool.sort(key=lambda c: math.hypot(by_id[c["homeParcelId"]]["x"] - mill["x"], by_id[c["homeParcelId"]]["z"] - mill["z"]))
    for c in rng.sample(pool[:30], MILLERS):
        old = by_id.get(c["workParcelId"])
        if old and c["id"] in old["workplaceFor"]:
            old["workplaceFor"].remove(c["id"])
        mill["workplaceFor"].append(c["id"])
        for s in c["schedule"]:
            if s["location"] == c["workParcelId"]:
                s["location"] = mill["id"]
            s["task"] = s["task"].replace(f"({c['trade']})", "(Miller)")
        c["trade"] = "Miller"
        c["workParcelId"] = mill["id"]
        c["carriedItem"] = "Flour Sack & Mill Pick"
    parcels.append(mill)
    return mill


# ------------------------------------------------------------------------------------------
# Industry outside the walls (stage 5): the limestone quarry south-east of the town and the
# bog-iron works in the south-bank woods. Like the mill, everything here runs after the
# citizens on its own RNG (INDUSTRY_SEED), so every existing parcel, citizen and plant keeps
# its id and content; plants are only removed (clearings) or appended (reeds by the bog).
# Each site is a few parcels with an explicit `model` (the renderer places it unscaled).
# Coordinates are world metres (three.js x, z); orientation as for every parcel (degrees
# about +Y, local +Z -> world (sin, cos)). The default camera looks from +x+z, so the
# quarry's hill stands at the north-west of the pit and its benches open toward the viewer.
# ------------------------------------------------------------------------------------------
INDUSTRY_SEED = 1392_21

QUARRY_CRAFT = {"id": "quarryman", "name": "Quarryman", "sign": "Pick & Iron Wedge",
                "guild": "Masons Confraternity", "wealth": "plebeian"}
CARTER_CRAFT = {"id": "carter", "name": "Carter", "sign": "Ox Yoke", "guild": "Masons Confraternity",
                "wealth": "plebeian"}
ORE_DIGGER_CRAFT = {"id": "ore_digger", "name": "Bog-Ore Digger", "sign": "Spade & Ore Basket",
                    "guild": "Smiths & Armorers Guild", "wealth": "plebeian"}
COLLIER_CRAFT = {"id": "collier", "name": "Collier", "sign": "Charcoal Rake", "guild": "Smiths & Armorers Guild",
                 "wealth": "plebeian"}
SMELTER_CRAFT = {"id": "smelter", "name": "Bloomery Smelter", "sign": "Bellows & Bloom",
                 "guild": "Smiths & Armorers Guild", "wealth": "plebeian"}

QUARRY_SITE = {"x": 230.0, "z": 195.0}
IRONWORKS_SITE = {"x": 198.0, "z": -125.0}

# id suffix, model, x, z, width, depth, orientation, buildingType, name, craft, carried item
QUARRY_PARCELS = [
    ("face", "quarry_face", 212.0, 188.0, 64.0, 52.0, 0.0, "limestone_quarry_face",
     "Kamieniołom (Limestone Quarry)", QUARRY_CRAFT),
    # The pit opens toward the south-east (pit floor centre ~(208, 184)); the yard and the
    # lodges crowd its mouth. masons_lodge: 7 x 12 m, open side local +X (orientation 180 =
    # open to the west).
    ("yard", "quarry_yard", 246.0, 196.0, 26.0, 30.0, 0.0, "quarry_stone_yard",
     "Plac kamieniarski (Stone Yard)", CARTER_CRAFT),
    ("lodge_1", "masons_lodge", 226.0, 224.0, 7.0, 12.0, 0.0, "quarry_masons_lodge",
     "Loża kamieniarzy (Masons' Lodge)", None),
    ("lodge_2", "masons_lodge", 268.0, 186.0, 7.0, 12.0, 180.0, "quarry_masons_lodge",
     "Loża kamieniarzy (Masons' Lodge)", None),
    ("lodge_3", "masons_lodge", 266.0, 222.0, 7.0, 12.0, 180.0, "quarry_masons_lodge",
     "Loża kamieniarzy (Masons' Lodge)", None),
]
IRONWORKS_PARCELS = [
    # The bog fills the meander bay south of the works (river bank ~4 m beyond its edge).
    ("bog", "bog_works", 205.0, -148.0, 34.0, 16.0, 0.0, "ironworks_bog_ore_pits",
     "Torfowisko rudy darniowej (Bog-Ore Pits)", ORE_DIGGER_CRAFT),
    ("clamp", "charcoal_clamp", 172.0, -118.0, 18.0, 14.0, 0.0, "ironworks_charcoal_clamp",
     "Mielerz (Charcoal Clamp)", COLLIER_CRAFT),
    ("bloomery", "bloomery", 200.0, -122.0, 18.0, 12.0, 0.0, "ironworks_bloomery",
     "Dymarki (Bloomery Furnaces)", SMELTER_CRAFT),
    ("forge", "forge_shed", 222.0, -108.0, 9.0, 6.0, 0.0, "ironworks_forge_shed",
     "Kuźnia polowa (Forge Shed)", None),
    ("hut_1", "smithy_hut", 224.0, -127.0, 7.0, 5.0, -90.0, "ironworks_smithy_hut",
     "Chata hutnika (Ironworker's Hut)", None),
    ("hut_2", "smithy_hut", 205.0, -97.0, 7.0, 5.0, 0.0, "ironworks_smithy_hut",
     "Chata hutnika (Ironworker's Hut)", None),
]

# Clearings (plants removed inside; world x0, z0, x1, z1) and the ground painted under them.
QUARRY_CLEARING = (176.0, 150.0, 302.0, 246.0)
IRONWORKS_CLEARING = (152.0, -162.0, 232.0, -86.0)
# kind: spoil = pale trodden stone dust, mud = dark wet peat, yard = trodden earth,
# pool = standing water in the bog (drawn as water, blocked for walkers).
INDUSTRY_GROUNDS = [
    ("quarry_floor", "spoil", [(186, 166), (226, 160), (262, 166), (280, 182), (280, 234), (240, 240), (204, 232), (188, 206)]),
    ("ironworks_yard", "yard", [(160, -126), (186, -134), (214, -136), (230, -126), (228, -100), (206, -90), (164, -106)]),
    ("bog_mud", "mud", [(188, -152), (205, -160), (222, -160), (226, -150), (222, -138), (200, -136), (187, -141)]),
    ("bog_pool_1", "pool", [(192, -150), (197, -153), (201, -150), (198, -146), (193, -146)]),
    ("bog_pool_2", "pool", [(206, -155), (212, -157), (215, -153), (210, -150)]),
    ("bog_pool_3", "pool", [(216, -146), (221, -147), (222, -142), (217, -141)]),
]
INDUSTRY_PATHS = [
    ("path_quarry", "track", 3.2, [(193.0, 26.0), (196.0, 60.0), (194.0, 100.0), (205.0, 135.0), (236.0, 150.0),
                                   (252.0, 164.0), (254.0, 180.0)]),
    ("path_ironworks", "track", 2.4, [(200.0, 14.0), (206.0, -25.0), (203.0, -60.0), (197.0, -88.0),
                                      (198.0, -104.0), (194.0, -112.0)]),
]

# (site, parcel suffix, trade, count, carried item)
INDUSTRY_CREWS = [
    ("quarry", "face", "Quarryman", 16, "Iron Pick & Splitting Wedges"),
    ("quarry", "yard", "Carter", 2, "Ox Goad & Rope"),
    ("quarry", "lodge_1", "Stone Mason", 2, "Mallet, Claw Chisel & Square"),
    ("quarry", "lodge_2", "Stone Mason", 2, "Mallet, Claw Chisel & Square"),
    ("quarry", "lodge_3", "Stone Mason", 2, "Mallet, Claw Chisel & Square"),
    ("ironworks", "bog", "Bog-Ore Digger", 4, "Iron-Shod Spade & Ore Basket"),
    ("ironworks", "clamp", "Collier", 2, "Charcoal Rake & Turf Spade"),
    ("ironworks", "bloomery", "Bloomery Smelter", 4, "Bloom Tongs & Leather Gloves"),
    ("ironworks", "forge", "Blacksmith", 4, "Hammer & Bloom Tongs"),
]
# The ironworks' two huts house the households of one smelter and one smith.
HUT_HOUSEHOLDS = [("hut_1", "Bloomery Smelter"), ("hut_2", "Blacksmith")]


def _site_parcel(site, spec):
    suffix, model, x, z, w, d, rot, btype, name, craft = spec
    return {
        "id": f"p_{site}_{suffix}", "district": "krakow_suburb" if site == "ironworks" else "castle_hill",
        "streetName": "Kamieniołom" if site == "quarry" else "Dymarki nad Bystrzycą",
        "x": x, "z": z, "width": w, "depth": d, "orientation": rot, "elevation": 0.0,
        "buildingType": btype, "model": model, "site": site, "isShed": False, "craft": craft,
        "aging": {"ageYears": 30, "ridgeSag": 0.08, "wallLeanAngle": 0.3, "woodGraying": 0.6,
                  "mossFoundation": 0.7, "maintenanceState": "weathered"},
        "clutter": [], "scaffolding": False, "wealthClass": "plebeian",
        "residents": [], "workplaceFor": [], "commodities": {}, "name": name,
    }


def _in_box(x, z, box, pad=0.0):
    return box[0] - pad < x < box[2] + pad and box[1] - pad < z < box[3] + pad


def add_industry(parcels, citizens, vegetation, paths, river):
    """Quarry and ironworks: parcels, crews (moved like the millers), the ironworks' resident
    households, clearings, painted grounds and tracks. Returns (grounds, sites)."""
    rng = random.Random(INDUSTRY_SEED)
    by_id = {p["id"]: p for p in parcels}
    new = {}
    for site, specs in (("quarry", QUARRY_PARCELS), ("ironworks", IRONWORKS_PARCELS)):
        for spec in specs:
            p = _site_parcel(site, spec)
            new[p["id"]] = p
    masons = next(c for c in CRAFTS if c["id"] == "mason")
    smith = next(c for c in CRAFTS if c["id"] == "blacksmith")
    for pid, p in new.items():
        if p["craft"] is None:
            p["craft"] = masons if "lodge" in pid else smith if "forge" in pid else None

    # Crews: labouring men living nearest each site (not woodcutters or millers).
    moved = set()
    for site, suffix, trade, count, item in INDUSTRY_CREWS:
        dest = new[f"p_{site}_{suffix}"]
        sx, sz = (QUARRY_SITE if site == "quarry" else IRONWORKS_SITE).values()
        pool = [c for c in citizens if c["id"] not in moved and c["gender"] == "male"
                and c["wealthClass"] == "plebeian" and c["guildRank"] in ("journeyman", "laborer")
                and c["trade"] not in ("Woodcutter", "Miller") and c["workParcelId"] in by_id
                and c["homeParcelId"] in by_id]
        pool.sort(key=lambda c: math.hypot(by_id[c["homeParcelId"]]["x"] - sx, by_id[c["homeParcelId"]]["z"] - sz))
        for c in rng.sample(pool[:max(40, count * 3)], count):
            old = by_id.get(c["workParcelId"])
            if old and c["id"] in old["workplaceFor"]:
                old["workplaceFor"].remove(c["id"])
            dest["workplaceFor"].append(c["id"])
            for s in c["schedule"]:
                if s["location"] == c["workParcelId"]:
                    s["location"] = dest["id"]
                s["task"] = s["task"].replace(f"({c['trade']})", f"({trade})")
            c["trade"] = trade
            c["workParcelId"] = dest["id"]
            c["carriedItem"] = item
            moved.add(c["id"])

    # The huts: the whole household of one smelter and one smith moves in (beds renumbered
    # in the same order). Their old house stands empty.
    cit_by_id = {c["id"]: c for c in citizens}
    for suffix, trade in HUT_HOUSEHOLDS:
        hut = new[f"p_ironworks_{suffix}"]
        crew = [c for c in citizens if c["trade"] == trade and c["workParcelId"].startswith("p_ironworks_")
                and c["homeParcelId"] in by_id and 2 <= len(by_id[c["homeParcelId"]]["residents"]) <= 5]
        if not crew:
            continue
        head = rng.choice(crew)
        old = by_id[head["homeParcelId"]]
        for k, rid in enumerate(list(old["residents"])):
            c = cit_by_id[rid]
            for s in c["schedule"]:
                if s["location"] == old["id"]:
                    s["location"] = hut["id"]
            c["homeParcelId"] = hut["id"]
            c["bedNumber"] = k + 1
            hut["residents"].append(rid)
        old["residents"] = []

    parcels.extend(new.values())

    # Clearings: no plant inside, except reeds, alders and willows within 6 m of the water.
    def water_dist(x, z):
        best = float("inf")
        for a, b in zip(river["points"], river["points"][1:]):
            if abs(a["x"] - x) > 40 and abs(b["x"] - x) > 40:
                continue
            best = min(best, _seg_dist(x, z, a["x"], a["z"], b["x"], b["z"]) - a["width"] * 0.5)
        return best
    keep_wet = {"reed_clump", "tree_alder", "tree_alder_b", "tree_willow", "tree_willow_weeping"}
    track_lines = [pts for _, _, _, pts in INDUSTRY_PATHS]
    before = len(vegetation)
    vegetation[:] = [v for v in vegetation
                     if not (_in_box(v["x"], v["z"], QUARRY_CLEARING)
                             or (_in_box(v["x"], v["z"], IRONWORKS_CLEARING)
                                 and not (v["type"] in keep_wet and water_dist(v["x"], v["z"]) < 6.0))
                             or min(_polyline_dist(v["x"], v["z"], pl) for pl in track_lines)
                             < (2.6 if v["type"].startswith("tree_") else 1.8))]
    removed = before - len(vegetation)

    # Reeds round the bog pools (appended, ids veg_ind_NNN).
    grounds = [{"id": gid, "kind": kind, "points": [{"x": float(x), "z": float(z)} for x, z in pts]}
               for gid, kind, pts in INDUSTRY_GROUNDS]
    added = 0
    for g in grounds:
        if g["kind"] != "pool":
            continue
        ring = [(q["x"], q["z"]) for q in g["points"]]
        cx = sum(x for x, _ in ring) / len(ring)
        cz = sum(z for _, z in ring) / len(ring)
        for k in range(len(ring)):
            (ax, az), (bx, bz) = ring[k], ring[(k + 1) % len(ring)]
            for t in (0.2, 0.7):
                x, z = ax + (bx - ax) * t, az + (bz - az) * t
                ox, oz = x - cx, z - cz
                ln = math.hypot(ox, oz) or 1.0
                x, z = x + ox / ln * 0.9, z + oz / ln * 0.9   # just outside the water's edge
                added += 1
                vegetation.append({"id": f"veg_ind_{added:03d}", "type": "reed_clump", "x": round(x, 2),
                                   "z": round(z, 2), "scale": round(rng.uniform(0.8, 1.25), 2),
                                   "rotation": round(rng.uniform(0, 360), 1), "zone": "ironworks_bog"})

    for pid, kind, width, pts in INDUSTRY_PATHS:
        paths.append({"id": pid, "kind": kind, "width": width,
                      "points": [{"x": round(x, 2), "z": round(z, 2)} for x, z in _smooth_path(pts, rng, 1.2)]})

    sites = {
        "quarry": {**QUARRY_SITE, "parcels": [p for p in new if p.startswith("p_quarry_")]},
        "ironworks": {**IRONWORKS_SITE, "parcels": [p for p in new if p.startswith("p_ironworks_")]},
    }
    crew_n = sum(len(p["workplaceFor"]) for p in new.values())
    homes = sum(len(p["residents"]) for p in new.values())
    print(f"[CityPlanGenerator] Industry: quarry + ironworks, {len(new)} parcels, {crew_n} workers moved, "
          f"{homes} living in the huts; cleared {removed} plants, {added} reeds by the bog pools.")
    return grounds, sites


# ------------------------------------------------------------------------------------------
# Clash pass (after everything else, no RNG): houses that the parcel generator let into the
# town wall, its towers and gates, or deep into each other, are pushed clear. The generator's
# own overlap test (get_obb_corners) rotates by +orientation while the renderer turns a model
# by -orientation about Y, so rotated parcels were tested mirrored; this pass uses the
# renderer's convention. Only x/z of the clashing parcels change (ids, residents, schedules
# stay), and plants under a moved house are dropped.
# ------------------------------------------------------------------------------------------
WALL_HALF = 1.7            # curtain wall half thickness incl. battlements and plinth, + margin
TOWER_HALF = 4.6           # curtain_tower is 8.2 m square at the cornice, + margin
GATE_HALF_EXT = {"gate_krakow": (6.5, 6.5), "gate_grodzka": (6.0, 6.0)}
HOUSE_PAD = 0.3            # model overhang past the parcel rectangle
PAIR_SLACK = 0.25          # terraced houses may touch this much


def _render_corners(cx, cz, hw, hd, angle_deg):
    """Rectangle corners as the renderer turns a model: local (x, z) -> (x c + z s, -x s + z c)."""
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    return [(cx + x * c + z * s, cz - x * s + z * c) for x, z in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))]


def _sat_depth(a, b):
    """Penetration depth of two convex polygons (> 0 = overlap) and the axis to push b along."""
    best, axis = float("inf"), (0.0, 0.0)
    for poly in (a, b):
        for i in range(len(poly)):
            (px, pz), (qx, qz) = poly[i], poly[(i + 1) % len(poly)]
            ln = math.hypot(qx - px, qz - pz) or 1.0
            ax, az = -(qz - pz) / ln, (qx - px) / ln
            pa = [x * ax + z * az for x, z in a]
            pb = [x * ax + z * az for x, z in b]
            d1, d2 = max(pa) - min(pb), max(pb) - min(pa)
            d = min(d1, d2)
            if d <= 0:
                return 0.0, (0.0, 0.0)
            if d < best:
                best, axis = d, ((ax, az) if d1 < d2 else (-ax, -az))
    return best, axis


# Ground footprint of each parcel model (model space x0, z0, x1, z1, metres, everything below
# 4 m incl. yard clutter), unscaled. Measured from the GLBs in the running app (template bounds);
# re-measure after changing a house model.
MODEL_FOOTPRINT = {
    "house_patrician_brick": (-4.69, -7.12, 4.69, 8.25), "house_half_timber": (-5.2, -6.0, 5.25, 6.55),
    "house_timber_log": (-5.2, -5.88, 6.2, 7.05), "shed_timber": (-2.75, -3.25, 3.0, 3.85),
    "house_baker": (-4.77, -6.04, 7.1, 6.85), "house_weaver": (-4.45, -6.14, 7.88, 9.17),
    "house_potter": (-4.02, -5.15, 8.75, 5.55), "house_brewer": (-4.51, -6.96, 8.98, 10.85),
    "house_tanner": (-4.11, -6.05, 8.15, 8.79), "blacksmith_workshop": (-3.9, -6.49, 5.65, 7.59),
    "logging_camp": (-6.4, -5.0, 6.6, 4.95), "watermill": (-3.5, -6.5, 6.28, 10.65),
}


def _parcel_hash(p, index):
    """src/engine/parcel-kind.ts parcelHash (JS int32 string hash)."""
    s = p["id"] or f"parcel_{index}"
    h = 0
    for ch in s:
        h = ((h << 5) - h + ord(ch)) & 0xFFFFFFFF
    if h >= 0x80000000:
        h -= 0x100000000
    return abs(h)


def parcel_model(p, index):
    """Model and scale the renderer draws a parcel with (parcel-kind.ts parcelKind +
    three-renderer.ts populateCityScene). Keep in sync with both."""
    craft = (p.get("craft") or {}).get("id", "")
    t = p.get("buildingType") or ""
    h = _parcel_hash(p, index)
    has = lambda *parts: any(s in t for s in parts)
    clamp = lambda v: min(1.15, max(0.85, v))
    scale = (clamp(p["width"] / 8.5), clamp(p["depth"] / 12.0))
    if p.get("model"):
        return p["model"], (1.0, 1.0)
    if p.get("isShed") or t.startswith("shed_"):
        return "shed_timber", (clamp(p["width"] / 5.2), clamp(p["depth"] / 6.2))
    for model, crafts, parts in (("house_baker", ("baker",), ("baker",)), ("house_tanner", ("tanner",), ("tanner",)),
                                 ("house_brewer", ("brewer",), ("brewer",)),
                                 ("blacksmith_workshop", ("blacksmith", "armorer"), ("blacksmith",)),
                                 ("house_potter", ("potter",), ("potter",)), ("house_weaver", ("weaver", "tailor"), ("weaver",))):
        if craft in crafts or has(*parts):
            return model, scale
    if has("watermill"):
        return "watermill", scale
    if has("windmill"):
        return "windmill", scale
    if has("quarry"):
        return "stone_quarry", scale
    if has("sawmill", "logging") or (craft == "carpenter" and p["district"] == "krakow_suburb" and h % 4 == 0):
        return "logging_camp", scale
    if has("harbor"):
        return "river_harbor", scale
    if has("patrician", "kamienica", "brick", "stone_arches") or craft == "goldsmith":
        return "house_patrician_brick", scale
    if has("fachwerk", "half_timber", "jettied", "narrow_gable", "furrier", "shoemaker") \
            or craft in ("shoemaker", "furrier", "candlemaker", "roper", "butcher"):
        return "house_half_timber", scale
    if has("log", "timber", "thatched", "cruck", "longhouse", "cottage", "loess", "cooper") \
            or craft in ("cooper", "wheelwright", "carpenter"):
        return "house_timber_log", scale
    if p["district"] == "market_square":
        return ("house_half_timber" if h % 4 == 0 else "house_patrician_brick"), scale
    if p["district"] == "krakow_suburb":
        return ("house_half_timber" if h % 3 == 0 else "house_timber_log"), scale
    return ("house_half_timber" if h % 2 == 0 else "house_timber_log"), scale


def resolve_clashes(parcels, wall_points, landmarks, castle_elements, vegetation):
    shapes = {}
    for i, p in enumerate(parcels):
        model, (sx, sz) = parcel_model(p, i)
        fp = MODEL_FOOTPRINT.get(model)
        if fp is None:
            fp = (-p["width"] * 0.5, -p["depth"] * 0.5, p["width"] * 0.5, p["depth"] * 0.5)
            sx = sz = 1.0
        shapes[p["id"]] = (fp[0] * sx - HOUSE_PAD, fp[1] * sz - HOUSE_PAD, fp[2] * sx + HOUSE_PAD, fp[3] * sz + HOUSE_PAD)

    def house(p, x=None, z=None):
        x0, z0, x1, z1 = shapes[p["id"]]
        a = math.radians(p["orientation"])
        c, s = math.cos(a), math.sin(a)
        cx, cz = (p["x"] if x is None else x), (p["z"] if z is None else z)
        return [(cx + lx * c + lz * s, cz - lx * s + lz * c) for lx, lz in ((x0, z0), (x1, z0), (x1, z1), (x0, z1))]
    fixed = []   # (name, polygon): wall pieces, towers, gates, landmarks
    n = len(wall_points)
    for i in range(n):
        a, b = wall_points[i], wall_points[(i + 1) % n]
        L = math.hypot(b["x"] - a["x"], b["z"] - a["z"])
        ux, uz = (b["x"] - a["x"]) / L, (b["z"] - a["z"]) / L
        fixed.append(("wall", [(a["x"] - uz * WALL_HALF, a["z"] + ux * WALL_HALF), (b["x"] - uz * WALL_HALF, b["z"] + ux * WALL_HALF),
                               (b["x"] + uz * WALL_HALF, b["z"] - ux * WALL_HALF), (a["x"] + uz * WALL_HALF, a["z"] - ux * WALL_HALF)]))
        hx, hz = GATE_HALF_EXT.get(a.get("id"), (TOWER_HALF, TOWER_HALF))
        fixed.append(("tower", [(a["x"] - hx, a["z"] - hz), (a["x"] + hx, a["z"] - hz), (a["x"] + hx, a["z"] + hz), (a["x"] - hx, a["z"] + hz)]))
    for l in list(landmarks) + [e for e in castle_elements if "width" in e and "x" in e]:
        fixed.append(("landmark", _render_corners(l["x"], l["z"], l["width"] * 0.5 + 1.0, l["depth"] * 0.5 + 1.0, 0.0)))

    # Relaxation: every round, each clashing house is pushed out of the walls / landmarks by
    # the full depth and away from each overlapping neighbour by half of it (the neighbour
    # takes the other half), until nothing clashes or the rounds run out. Moves are capped at
    # MAX_SHIFT from where the generator put the house.
    MAX_SHIFT, ROUNDS, CELLB = 12.0, 120, 24.0
    movable = [p for p in parcels if not p.get("model")]
    start = {p["id"]: (p["x"], p["z"]) for p in movable}
    fixed_polys = [f for _, f in fixed]
    fixed_box = [(min(c[0] for c in f), min(c[1] for c in f), max(c[0] for c in f), max(c[1] for c in f)) for f in fixed_polys]

    def worst_state():
        polys = {p["id"]: house(p) for p in movable}
        bins = {}
        for p in movable:
            bins.setdefault((int(p["x"] // CELLB), int(p["z"] // CELLB)), []).append(p)
        push = {p["id"]: [0.0, 0.0] for p in movable}
        wall_hits, pair_hits = set(), set()
        for p in movable:
            poly = polys[p["id"]]
            xs, zs = [c[0] for c in poly], [c[1] for c in poly]
            for f, (bx0, bz0, bx1, bz1) in zip(fixed_polys, fixed_box):
                if bx1 < min(xs) or bx0 > max(xs) or bz1 < min(zs) or bz0 > max(zs):
                    continue
                d, ax = _sat_depth(f, poly)
                if d > 0:
                    wall_hits.add(p["id"])
                    push[p["id"]][0] += ax[0] * (d + 0.1)
                    push[p["id"]][1] += ax[1] * (d + 0.1)
            bx, bz = int(p["x"] // CELLB), int(p["z"] // CELLB)
            for ix in (bx - 1, bx, bx + 1):
                for iz in (bz - 1, bz, bz + 1):
                    for q in bins.get((ix, iz), ()):
                        if q["id"] <= p["id"]:
                            continue
                        d, ax = _sat_depth(polys[p["id"]], polys[q["id"]])   # ax pushes q away from p
                        if d > PAIR_SLACK:
                            pair_hits.add((p["id"], q["id"]))
                            k = (d - PAIR_SLACK) * 0.5 + 0.05
                            push[q["id"]][0] += ax[0] * k
                            push[q["id"]][1] += ax[1] * k
                            push[p["id"]][0] -= ax[0] * k
                            push[p["id"]][1] -= ax[1] * k
        return push, wall_hits, pair_hits

    walls0 = pairs0 = None
    for _ in range(ROUNDS):
        push, wall_hits, pair_hits = worst_state()
        if walls0 is None:
            walls0, pairs0 = len(wall_hits), len(pair_hits)
        if not wall_hits and not pair_hits:
            break
        for p in movable:
            dx, dz = push[p["id"]]
            if dx == 0 and dz == 0:
                continue
            x0, z0 = start[p["id"]]
            nx, nz = p["x"] + dx, p["z"] + dz
            off = math.hypot(nx - x0, nz - z0)
            if off > MAX_SHIFT:
                nx, nz = x0 + (nx - x0) * MAX_SHIFT / off, z0 + (nz - z0) * MAX_SHIFT / off
            p["x"], p["z"] = nx, nz
    _, wall_hits, pair_hits = worst_state()
    moved = []
    for p in movable:
        x0, z0 = start[p["id"]]
        p["x"], p["z"] = round(p["x"], 2), round(p["z"], 2)
        if (p["x"], p["z"]) != (x0, z0):
            moved.append((p["id"], round(math.hypot(p["x"] - x0, p["z"] - z0), 1)))
    stuck = sorted(wall_hits) + [f"{a}/{b}" for a, b in sorted(pair_hits)]
    print(f"[CityPlanGenerator] Clash pass: wall/tower/landmark clashes {walls0} -> {len(wall_hits)}, "
          f"house pairs {pairs0} -> {len(pair_hits)}")
    moved_ids = {m[0] for m in moved}
    polys = [house(p) for p in parcels if p["id"] in moved_ids]
    before = len(vegetation)

    def under(v):
        r = 1.5 if v["type"].startswith("tree_") else 0.4
        for poly in polys:
            xs = [c[0] for c in poly]
            zs = [c[1] for c in poly]
            if min(xs) - r < v["x"] < max(xs) + r and min(zs) - r < v["z"] < max(zs) + r:
                return True
        return False
    vegetation[:] = [v for v in vegetation if not under(v)]
    print(f"[CityPlanGenerator] Clash pass: moved {len(moved)} parcels clear of the wall and each other "
          f"(max {max([m[1] for m in moved] or [0])} m), {len(stuck)} left clashing {stuck}; "
          f"dropped {before - len(vegetation)} plants under moved houses.")


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

    # 3b. The Bystrzyca: a meandering river through the empty south-east, from past the south
    # edge of the map to past the east edge. Its own RNG, so parcels and citizens are unchanged.
    river, river_margin, river_seed = generate_river(parcels, civic_landmarks, castle_elements,
                                                     street_segments, wall_segments, dist_point_to_segment)
    def river_dist(tx, tz):
        """Distance from (tx, tz) to the channel edge (negative inside the water)."""
        pts = river["points"]
        best = float("inf")
        for a, b in zip(pts, pts[1:]):
            d = dist_point_to_segment(tx, tz, a["x"], a["z"], b["x"], b["z"]) - 0.5 * (a["width"] + b["width"]) * 0.5
            best = min(best, d)
        return best
    before = len(vegetation)
    vegetation[:] = [v for v in vegetation if river_dist(v["x"], v["z"]) >= 4.0]
    print(f"[CityPlanGenerator] River Bystrzyca: {len(river['points'])} points, {river['lengthM']} m "
          f"(seed {river_seed}), nearest parcel/street/wall {river_margin:.1f} m from the bank; "
          f"dropped {before - len(vegetation)} trees in or by the channel.")

    # 3c. Riverside woods, the footbridge and the watermill site (own RNG: FOREST_SEED).
    clear_circles = [(p["x"], p["z"], math.hypot(p["width"], p["depth"]) * 0.5) for p in parcels]
    clear_circles += [(l["x"], l["z"], math.hypot(l["width"], l["depth"]) * 0.5) for l in civic_landmarks]
    clear_circles += [(e["x"], e["z"], math.hypot(e.get("width", 14), e.get("depth", 14)) * 0.5)
                      for e in castle_elements if "x" in e and "z" in e]
    clear_segments = street_segments + wall_segments + [(e["startX"], e["startZ"], e["endX"], e["endZ"])
                                                        for e in castle_elements if "startX" in e]
    clearance = _Clearance(clear_circles, clear_segments, dist_point_to_segment)
    frames = _river_frames(river)
    paths, mill_site = plan_river_crossing(river, frames, clearance, random.Random(FOREST_SEED + 2))
    # Older trees off the paths and out of the mill yard.
    path_lines = [[(q["x"], q["z"]) for q in pth["points"]] for pth in paths]
    vegetation[:] = [v for v in vegetation if all(_polyline_dist(v["x"], v["z"], pl) > 4.5 for pl in path_lines)]
    retype_old_trees(vegetation)
    forest = generate_forest(river, frames, paths, mill_site, clearance, vegetation)
    vegetation.extend(forest)
    counts = {}
    for v in vegetation:
        counts[v["type"]] = counts.get(v["type"], 0) + 1
    print(f"[CityPlanGenerator] Riverside woods: {len(forest)} plants; bridge at "
          f"({river['crossings'][0]['x']}, {river['crossings'][0]['z']}), mill at ({mill_site['x']}, {mill_site['z']}); "
          + ", ".join(f"{k} {counts[k]}" for k in sorted(counts)))

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
    add_watermill(parcels, citizens, mill_site)
    grounds, industry_sites = add_industry(parcels, citizens, vegetation, paths, river)
    resolve_clashes(parcels, wall_points, civic_landmarks, castle_elements, vegetation)
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
        "river": river,
        "paths": paths,
        "grounds": grounds,
        "industrySites": industry_sites,
        "citizens": citizens,
        "bellHours": BELL_HOURS,
        "fairEvents": fair_events,
        "houseTypesCatalog": HOUSE_TYPES,
        "shedTypesCatalog": SHED_TYPES,
        "craftsCatalog": CRAFTS + [WOODCUTTER_CRAFT, MILLER_CRAFT, QUARRY_CRAFT, CARTER_CRAFT,
                                   ORE_DIGGER_CRAFT, COLLIER_CRAFT, SMELTER_CRAFT]
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
