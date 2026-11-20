# Kit: char_groom. Loaded by build_characters.py (load_kit_builders); runs with its globals.
# The stable's crew (stable plan M5): grooms, the hay boy, the postilion and the stablemaster
# (kit.trades dresses the last three). Their loops: work-anims/muck, brush, forkhay, harness.

GROOM_TUNIC = [["#6f6552", 3, "pa"], ["#5a5446", 3, "pa"], ["#7a6a4c", 2, "pa"], ["#5f6346", 2, "pa"],
               ["#6b4a32", 2, "pa"], ["#4b5a6e", 1, "ab"], ["#5f6b3a", 1, "ab"]]
GROOM_HOOD = [["#4d4536", 3, "pa"], ["#5c4a36", 2, "pa"], ["#3e4f3a", 1, "pa"], ["#6e2f28", 1, "ab"]]
SURCOAT = [["#2f3f63", 3, "pabr"], ["#3e4f3a", 2, "pabr"], ["#6e2f28", 2, "pabr"], ["#4a3a2a", 1, "pabr"]]


def build(kit):
    """Groom: short belted tunic, hose, ankle shoes, hood or felt cap, a short leather apron;
    a two-tine hay fork (or a curry comb) in the right fist. Variants: the stablemaster's
    dyed surcoat, brimmed felt hat and ring of keys; the postilion's riding boots and whip;
    the hay boy at child scale."""
    kit.anim = {"work": "brush"}
    kit_body(kit, tunic_slot="tunic", hose_slot="hose", shoe="shoes", sleeves=("full", "rolled"), sleeve_w=(2, 3),
             male_hem=0.66)
    kit.slot("tunic", GROOM_TUNIC)
    kit.slot("hose", HOSE)
    kit.slot("hood", GROOM_HOOD)
    kit.slot("cap", [["#3a2a1c", 2, "pab"], ["#4d4536", 2, "pab"], ["#5a3e26", 1, "pab"]])
    kit.slot("apron", LEATHER)
    kit.slot("boots", LEATHER)
    kit.slot("coat", SURCOAT)
    kit.slot("felt", [["#2b211a", 3, "pabr"], ["#3a3129", 2, "pabr"], ["#4a3a2a", 1, "pabr"]])
    kit_heads(kit, {"hat:hood": (3, 0), "hat:cap": (3, 0), "hat:bare": (2, 1), "hat:kerchief": (0, 3),
                    "hair:short": (4, 0), "hair:long": (2, 0), "hair:bald": (1, 0),
                    "beard:none": (3, 1), "beard:short": (3, 0), "beard:full": (1, 0), "beard:moustache": (1, 0)})

    # Short leather apron from the belt (mucking out), or none.
    kit.option("apron", "waist", 2, 1)
    kit.option("apron", "none", 1, 1)
    kit_bib_apron(kit, "apron:waist", "apron", bottom=0.5, waist_only=True)

    # Tool in the right fist. The fork points forward and down like the collier's rake, so an
    # arm swung forward (muck, forkhay) lifts it into the work. The curry comb is in the left
    # (the brush loop works that arm).
    kit.option("tool", "fork", 2, 0)
    kit.option("tool", "bare", 1, 1)
    kit.option("tool", "whip", 0, 0)
    kit.option("tool", "none", 0, 0)
    wa, wd, ir = kit.mat("wood_ash"), kit.mat("wood_dark"), kit.mat("iron_dark")
    hand = Vector((-0.24, -0.065, 0.80))
    bm = kit.bm("arm_R", "tool:fork")
    al = 0.6
    d = Vector((0, -math.sin(al), -math.cos(al)))
    end = hand + d * 0.72
    add_tube(bm, [(tuple(hand - d * 0.32), 0.015, 0.015), (tuple(hand), 0.016, 0.016), (tuple(end), 0.016, 0.016)],
             segs=6, mat_idx=wa)
    side = Vector((1, 0, 0))
    for s in (-1, 1):                                   # two tines bending out of the shaft's end
        a = end + side * (s * 0.012)
        b = end + side * (s * 0.07) + d * 0.08
        c = b + d * 0.22
        add_tube(bm, [(tuple(a), 0.011, 0.011), (tuple(b), 0.01, 0.01), (tuple(c), 0.007, 0.007)], segs=5,
                 mat_idx=wa)
    kit.option("comb", "yes", 1, 1)
    kit.option("comb", "no", 0, 0)
    bm = kit.bm("arm_L", "comb:yes")                    # oval curry comb, strap over the knuckles
    add_ellipsoid(bm, (0.24, -0.11, 0.79), (0.03, 0.06, 0.04), segs=8, rings=5, mat_idx=wd)
    add_box(bm, 0.24, -0.11, 0.745, 0.05, 0.1, 0.012, mat_idx=ir)
    bm = kit.bm("arm_R", "tool:whip")                   # riding whip: stock up and forward, a short lash
    a, b = hand + Vector((0, 0.02, 0.05)), hand + Vector((0, -0.42, 0.62))
    add_tube(bm, [(tuple(a), 0.012, 0.012), (tuple(b), 0.006, 0.006)], segs=5, mat_idx=wd)
    add_tube(bm, [(tuple(b), 0.004, 0.004), (tuple(b + Vector((0, -0.12, -0.18))), 0.003, 0.003),
                  (tuple(b + Vector((0, -0.1, -0.38))), 0.003, 0.003)], segs=4, mat_idx=kit.mat("leather_tan"))

    # Riding boots to the knee, turned-down cuffs (the postilion).
    kit.option("boots", "low", 1, 1)
    kit.option("boots", "high", 0, 0)
    bt = kit.mat("slot:boots")
    for leg, sx in (("leg_R", -1), ("leg_L", 1)):
        x = sx * 0.095
        bm = kit.bm(leg, "boots:high")
        add_tube(bm, [((x, 0.0, 0.03), 0.062, 0.064), ((x, -0.004, 0.36), 0.066, 0.068), ((x, -0.006, 0.5), 0.07, 0.072)],
                 segs=8, mat_idx=bt)
        add_tube(bm, [((x, -0.006, 0.47), 0.078, 0.08), ((x, -0.006, 0.53), 0.08, 0.082)], segs=8, mat_idx=bt)
        add_tube(bm, [((x, 0.06, 0.06), 0.052, 0.062), ((x, -0.06, 0.055), 0.056, 0.056),
                      ((x, -0.17, 0.035), 0.042, 0.034)], segs=8, mat_idx=bt)

    # The stablemaster: a dyed surcoat over the tunic, flaring to the thigh, with a collar.
    kit.option("coat", "no", 1, 1)
    kit.option("coat", "yes", 0, 0)
    cm = kit.mat("slot:coat")
    bm = kit.bm("body", "coat:yes+sex:m")
    add_tube(bm, [((0, 0.0, 0.56), 0.235, 0.172), ((0, 0, 0.80), 0.198, 0.142), ((0, 0, 0.98), 0.178, 0.127),
                  ((0, 0, 1.18), 0.2, 0.14), ((0, 0, 1.35), 0.214, 0.134), ((0, 0, 1.41), 0.2, 0.118)],
             segs=10, mat_idx=cm, cap0=False, cap1=False)
    add_tube(bm, [((0, 0.005, 1.39), 0.17, 0.12), ((0, 0.01, 1.46), 0.1, 0.085)], segs=10, mat_idx=cm, cap0=False,
             cap1=False)
    add_tube(bm, [((0, 0, 0.95), 0.184, 0.132), ((0, 0, 1.0), 0.184, 0.132)], segs=10, mat_idx=kit.mat("slot:belt"),
             cap0=False, cap1=False)
    # Ring of keys at the left hip.
    kit.option("keys", "no", 1, 1)
    kit.option("keys", "yes", 0, 0)
    bm = kit.bm("body", "keys:yes")
    add_tube(bm, [((0.16 + 0.03 * math.cos(a), -0.11, 0.9 + 0.03 * math.sin(a)), 0.004, 0.004)
                  for a in [k / 10 * math.tau for k in range(11)]], segs=4, mat_idx=ir)
    for k, dx in enumerate((-0.02, 0.0, 0.022)):
        add_box(bm, 0.16 + dx, -0.115, 0.85 - 0.01 * k, 0.008, 0.006, 0.06, mat_idx=ir)
    # Brimmed felt hat (the stablemaster).
    kit.option("hat", "felt", 0, 0)
    fm = kit.mat("slot:felt")
    cx, cy, cz = HEAD_C
    rx, ry, rz = HEAD_R
    bm = kit.bm("head", "hat:felt")
    add_ellipsoid(bm, (cx, cy + 0.004, cz + 0.035), (rx * 1.13, ry * 1.11, rz * 1.05), segs=12, rings=8,
                  mat_idx=fm, keep=lambda x, y, z: z > 0.2)
    add_tube(bm, [((cx, cy + 0.004, cz + 0.06), rx * 1.12, ry * 1.1), ((cx, cy + 0.004, cz + 0.17), rx * 0.9, ry * 0.88)],
             segs=12, mat_idx=fm, cap0=False)
    add_tube(bm, [((cx, cy + 0.004, cz + 0.05), 0.2, 0.21), ((cx, cy + 0.004, cz + 0.066), 0.2, 0.21)], segs=14,
             mat_idx=fm)

    kit.trades = {
        "stablemaster": {"pick": {"coat": "yes", "keys": "yes", "hat": "felt", "tool": "none", "comb": "no", "apron": "none"},
                         "anim": "watch"},
        "postilion": {"pick": {"boots": "high", "tool": "whip", "comb": "no", "apron": "none"}, "anim": "harness"},
        "hay boy": {"pick": {"tool": "fork", "beard": "none", "hat": "cap"}, "anim": "forkhay", "scale": 0.8},
    }
