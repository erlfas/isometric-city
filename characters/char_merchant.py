# Kit: char_merchant. Loaded by build_characters.py (load_kit_builders); runs with its globals.
#
# The houppelande is an ankle-length gown, so it replaces kit_body's torso. Its lower
# skirt is split into two half-bells carried by the legs: a rigid skirt in the body
# would be pierced by the walking legs (hip pivot 0.90, swing 0.4 rad).

GOWN_M = [(0.40, 0.265, 0.235), (0.60, 0.235, 0.20), (0.80, 0.205, 0.165), (0.95, 0.18, 0.13),
          (1.18, 0.20, 0.14), (1.35, 0.215, 0.135), (1.40, 0.205, 0.12), (1.44, 0.13, 0.085),
          (1.48, 0.08, 0.07)]
GOWN_F = [(0.40, 0.255, 0.225), (0.70, 0.215, 0.18), (0.98, 0.165, 0.125), (1.07, 0.158, 0.113),
          (1.18, 0.17, 0.125), (1.33, 0.18, 0.11), (1.385, 0.185, 0.1), (1.43, 0.12, 0.075),
          (1.465, 0.07, 0.06)]


def _ring_at(rings, z):
    """Interpolated (side, front) radius of a gown profile at height z."""
    for (z0, s0, f0), (z1, s1, f1) in zip(rings, rings[1:]):
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return s0 + (s1 - s0) * t, f0 + (f1 - f0) * t
    return rings[-1][1], rings[-1][2]


def _front_y(rings, x, z, lift=0.004):
    rs, rf = _ring_at(rings, z)
    return -rf * math.sqrt(max(0.0, 1.0 - (x / rs) ** 2)) - lift


def _loop(cx, cy, cz, rx, ry, n=12, dz=None):
    """Closed path of n+1 points round a horizontal ellipse (for add_tube rolls and bands)."""
    pts = []
    for i in range(n + 1):
        a = i / n * math.tau
        z = cz + (dz(a) if dz else 0.0)
        pts.append((cx + math.cos(a) * rx, cy + math.sin(a) * ry, z))
    return pts


def _gown(kit, sex, rings, belt_z, collar, lapels, purse):
    gown, fur, gold = kit.mat("slot:gown"), kit.mat("slot:fur"), kit.mat("gold")
    bm = kit.bm("body", f"sex:{sex}")
    add_tube(bm, [((0, 0, z), s, f) for z, s, f in rings], segs=12, mat_idx=gown)
    s, f = _ring_at(rings, belt_z)
    add_tube(bm, [((0, 0, belt_z - 0.022), s + 0.006, f + 0.006), ((0, 0, belt_z + 0.022), s + 0.006, f + 0.006)],
             segs=12, mat_idx=kit.mat("slot:belt"), cap0=False, cap1=False)
    # Broad fur collar over the shoulders, fur lapels down to the belt.
    add_tube(bm, collar, segs=12, mat_idx=fur, cap0=False, cap1=False)
    for sx in (-1, 1):   # wide at the collar, meeting in a V at the belt (thin parallel strips read as braces)
        pts = [((sx * x, _front_y(rings, x, z, 0.006), z), w, 0.01) for x, z, w in lapels]
        add_tube(bm, pts, segs=4, mat_idx=fur)
    # Gilt band down the front opening, belt to knee.
    add_tube(bm, [((0, _front_y(rings, 0, z), z), 0.016, 0.005) for z in (belt_z - 0.03, 0.80, 0.60, 0.42)],
             segs=4, mat_idx=gold, smooth=False)
    # Purse on a short strap from the belt, the wearer's right front.
    px, pz = purse
    py = _front_y(rings, px, pz, -0.012) - 0.022
    add_tube(bm, [((px, _front_y(rings, px, belt_z - 0.02, 0.0), belt_z - 0.02), 0.006, 0.004),
                  ((px, py, pz + 0.05), 0.006, 0.004)], segs=4, mat_idx=kit.mat("leather_tan"))
    add_ellipsoid(bm, (px, py, pz), (0.05, 0.022, 0.056), segs=8, rings=5, mat_idx=kit.mat("leather_tan"))
    add_box(bm, px, py - 0.012, pz + 0.035, 0.05, 0.012, 0.014, mat_idx=gold)


def build(kit):
    """Patrician merchant: fur-collared houppelande, chaperon or fur hat, purse, sealed scroll."""
    kit.anim = {"work": "reckon"}
    kit_body(kit, tunic_slot="gown", hose_slot="hose", shoe="shoes", sleeves=("full",), sleeve_w=(1,))
    for sex in ("m", "f"):            # drop the knee-length tunic; the gown below replaces it
        kit.parts.pop(("body", f"sex:{sex}")).free()

    rich = "br"
    kit.slot("gown", [["#2b4a8c", 4, rich], ["#7d1e2a", 3, rich], ["#1d1b20", 3, rich], ["#a0322a", 2, rich],
                      ["#2d4b36", 2, rich], ["#4f2342", 2, rich], ["#3a3f6e", 1, rich], ["#6b4a24", 1, rich]])
    kit.slot("fur", [["#5b4330", 3, rich], ["#8a8580", 2, rich], ["#2e241c", 2, rich], ["#7a4a2a", 2, rich],
                     ["#b8b0a4", 1, rich]])        # marten, vair, sable, fox, lamb
    kit.slot("hat", [["#7a1f2b", 4, rich], ["#1e1b1c", 3, rich], ["#2a3560", 2, rich], ["#9a2a24", 2, rich],
                     ["#2f4a33", 1, rich], ["#5a2338", 2, rich]])
    kit.slot("hose", [["#7a2a26", 3, rich], ["#1f1d1f", 3, rich], ["#2f3f63", 2, rich], ["#3e4f3a", 1, rich]])
    kit.slot("belt", [["#8c2a26", 3, rich], ["#2b211a", 2, rich], ["#6e2f28", 2, rich], ["#3a2a1c", 1, rich]])
    kit.slot("shoes", [["#2b211a", 3, rich], ["#4a2a1e", 2, rich], ["#1a1716", 2, rich]])
    kit.slot("hood", [["#7a1f2b", 1, rich], ["#1e1b1c", 1, rich], ["#2a3560", 1, rich]])
    kit.mat("gold", "#c49a3a", roughness=0.45, metallic=0.25)

    _gown(kit, "m", GOWN_M, 0.975,
          collar=[((0, 0, 1.29), 0.228, 0.152), ((0, 0, 1.39), 0.232, 0.152), ((0, 0.0, 1.45), 0.16, 0.115)],
          lapels=[(0.085, 1.31, 0.06), (0.05, 1.17, 0.045), (0.018, 1.0, 0.018)], purse=(-0.08, 0.86))
    _gown(kit, "f", GOWN_F, 1.09,
          collar=[((0, 0, 1.29), 0.205, 0.135), ((0, 0, 1.37), 0.212, 0.128), ((0, 0.0, 1.43), 0.15, 0.1)],
          lapels=[(0.09, 1.30, 0.055), (0.045, 1.19, 0.035), (0.015, 1.11, 0.015)], purse=(-0.08, 0.92))

    # Lower skirt: one half-bell per leg, gilt hem.
    gown, gold = kit.mat("slot:gown"), kit.mat("gold")
    for side, sx in (("leg_R", -1), ("leg_L", 1)):
        bm = kit.bm(side)
        x = sx * 0.075
        add_tube(bm, [((x, 0, 0.60), 0.15, 0.15), ((x, 0, 0.40), 0.185, 0.205), ((x, 0, 0.10), 0.195, 0.225)],
                 segs=12, mat_idx=gown, cap1=False)
        add_tube(bm, [((x, 0, 0.10), 0.199, 0.229), ((x, 0, 0.135), 0.198, 0.227)], segs=12, mat_idx=gold,
                 cap0=False, cap1=False)

    # Houppelande sleeves over the plain forearm.
    kit.option("gownsleeve", "bag", 3, 1)        # funnel to the wrist, fur cuff
    kit.option("gownsleeve", "hanging", 2, 1)    # open sleeve hanging to the knee
    kit.option("gownsleeve", "fitted", 1, 0)
    fur = kit.mat("slot:fur")
    for side, sx in (("arm_R", -1), ("arm_L", 1)):
        bm = kit.bm(side, "gownsleeve:bag")
        add_tube(bm, [((sx * 0.215, 0.005, 1.26), 0.066, 0.068), ((sx * 0.24, 0.0, 1.02), 0.085, 0.09),
                      ((sx * 0.255, -0.02, 0.85), 0.105, 0.11)], segs=10, mat_idx=gown, cap0=False, cap1=False)
        add_tube(bm, [((sx * 0.256, -0.022, 0.875), 0.113, 0.118), ((sx * 0.257, -0.024, 0.835), 0.115, 0.12)],
                 segs=10, mat_idx=fur, cap0=False, cap1=False)
        bm = kit.bm(side, "gownsleeve:hanging")
        add_tube(bm, [((sx * 0.225, 0.015, 1.32), 0.07, 0.075), ((sx * 0.27, 0.035, 1.0), 0.045, 0.12),
                      ((sx * 0.30, 0.05, 0.62), 0.035, 0.155)], segs=8, mat_idx=gown, cap0=False)
        add_tube(bm, [((sx * 0.30, 0.05, 0.63), 0.039, 0.159), ((sx * 0.30, 0.05, 0.60), 0.038, 0.158)],
                 segs=8, mat_idx=gold, cap0=False, cap1=False)
        bm = kit.bm(side, "gownsleeve:fitted")
        add_tube(bm, [((sx * 0.238, -0.048, 0.89), 0.05, 0.052), ((sx * 0.238, -0.05, 0.855), 0.05, 0.052)],
                 segs=8, mat_idx=fur, cap0=False, cap1=False)

    # Sealed scroll hanging from the right fist (double-sided, so it reads from both faces).
    bm = kit.bm("arm_R")
    parch, wax = kit.mat("parchment", "#e3d3a8", roughness=0.85), kit.mat("wax", "#a3201b", roughness=0.5)
    add_tube(bm, [((-0.305, -0.118, 0.795), 0.016, 0.016), ((-0.18, -0.118, 0.795), 0.016, 0.016)],
             segs=6, mat_idx=parch)
    add_panel(bm, 0.585, 0.795, 0.11, 0.11, -0.124, -0.124, 0.006, parch, x=-0.2425)
    add_tube(bm, [((-0.30, -0.12, 0.58), 0.013, 0.013), ((-0.185, -0.12, 0.58), 0.013, 0.013)],
             segs=6, mat_idx=parch)
    add_tube(bm, [((-0.24, -0.128, 0.625), 0.022, 0.022), ((-0.24, -0.138, 0.625), 0.022, 0.022)],
             segs=8, mat_idx=wax, smooth=False)
    add_tube(bm, [((-0.236, -0.13, 0.605), 0.009, 0.003), ((-0.232, -0.132, 0.53), 0.008, 0.003)],
             segs=4, mat_idx=wax, smooth=False)

    # Ledger (optional) held by its top edge in the left hand, covers facing sideways.
    kit.option("ledger", "yes", 2, 1)
    kit.option("ledger", "no", 3, 0)
    bm = kit.bm("arm_L", "ledger:yes")
    cover = kit.mat("ledger", "#5a2a1c", roughness=0.7)
    add_box(bm, 0.28, -0.075, 0.715, 0.026, 0.16, 0.215, mat_idx=parch)
    for dx in (-0.016, 0.016):
        add_box(bm, 0.28 + dx, -0.072, 0.715, 0.007, 0.168, 0.222, mat_idx=cover)
    add_box(bm, 0.28, 0.009, 0.715, 0.039, 0.008, 0.222, mat_idx=cover)

    # Chain of office (burgomasters and councillors) over the fur collar.
    kit.option("chain", "yes", 1, 0)
    kit.option("chain", "no", 3, 1)
    bm = kit.bm("body", "chain:yes+sex:m")
    pts = [(-0.15, -0.10, 1.42), (-0.10, -0.157, 1.33), (0.0, -0.168, 1.27), (0.10, -0.157, 1.33), (0.15, -0.10, 1.42)]
    add_tube(bm, [(p, 0.008, 0.008) for p in pts], segs=4, mat_idx=gold, smooth=False)
    add_ellipsoid(bm, (0, -0.176, 1.235), (0.028, 0.012, 0.032), segs=8, rings=4, mat_idx=gold)

    # Heads: shared hair, beards, hood and veil; the patrician hats are drawn below.
    kit_heads(kit, {"hat:bare": (1, 0), "hat:hood": (1, 0), "hat:veil": (0, 1),
                    "hair:short": (4, 0), "hair:long": (2, 1), "hair:bald": (1, 0),
                    "beard:none": (2, 1), "beard:short": (3, 0), "beard:full": (3, 0), "beard:moustache": (1, 0)})
    hat = kit.mat("slot:hat")
    cx, cy, cz = HEAD_C

    # Chaperon: padded roll, crown, cockscomb flopping to one side, short tail behind.
    kit.option("hat", "chaperon", 5, 0)
    bm = kit.bm("head", "hat:chaperon")
    add_ellipsoid(bm, (cx, cy + 0.005, 1.70), (0.098, 0.112, 0.085), segs=12, rings=8, mat_idx=hat,
                  keep=lambda x, y, z: z > -0.1)
    add_tube(bm, [(p, 0.042, 0.042) for p in _loop(cx, cy + 0.005, 1.705, 0.112, 0.128, n=12,
                                                    dz=lambda a: 0.012 * math.sin(a))],
             segs=6, mat_idx=hat, cap0=False, cap1=False)
    add_ellipsoid(bm, (0.075, 0.0, 1.77), (0.07, 0.085, 0.045), segs=8, rings=5, mat_idx=hat)
    add_tube(bm, [((0.12, -0.02, 1.76), 0.025, 0.06), ((0.17, 0.0, 1.68), 0.02, 0.07),
                  ((0.18, 0.02, 1.58), 0.012, 0.055)], segs=6, mat_idx=hat)
    add_tube(bm, [((-0.04, 0.13, 1.69), 0.032, 0.03), ((-0.07, 0.155, 1.56), 0.028, 0.026),
                  ((-0.09, 0.16, 1.47), 0.022, 0.02)], segs=6, mat_idx=hat)

    # Kolpak: Polish fur hat with a cloth crown.
    kit.option("hat", "kolpak", 3, 0)
    bm = kit.bm("head", "hat:kolpak")
    add_tube(bm, [((cx, cy + 0.006, 1.645), 0.117, 0.128), ((cx, cy + 0.006, 1.70), 0.124, 0.135),
                  ((cx, cy + 0.006, 1.745), 0.12, 0.131)], segs=12, mat_idx=fur, cap0=False)
    add_ellipsoid(bm, (cx, cy + 0.01, 1.75), (0.105, 0.115, 0.07), segs=10, rings=6, mat_idx=hat,
                  keep=lambda x, y, z: z > -0.1)

    # Tall brimmed beaver hat.
    kit.option("hat", "brimmed", 2, 0)
    bm = kit.bm("head", "hat:brimmed")
    add_tube(bm, [((cx, cy + 0.006, 1.695), 0.175, 0.185), ((cx, cy + 0.006, 1.712), 0.175, 0.185)],
             segs=14, mat_idx=hat)
    add_tube(bm, [((cx, cy + 0.006, 1.70), 0.1, 0.112), ((cx, cy + 0.006, 1.84), 0.088, 0.098),
                  ((cx, cy + 0.006, 1.86), 0.07, 0.08)], segs=12, mat_idx=hat, cap0=False)
    add_tube(bm, [((cx, cy + 0.006, 1.712), 0.102, 0.114), ((cx, cy + 0.006, 1.735), 0.101, 0.113)],
             segs=12, mat_idx=kit.mat("slot:belt"), cap0=False, cap1=False)
