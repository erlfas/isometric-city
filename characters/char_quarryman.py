# Kit: char_quarryman. Loaded by build_characters.py (load_kit_builders); runs with its globals.
# All quarrymen are men (plebeian labourers at the limestone quarry, catalog worker_quarryman_hewer).

DUSTY = [["#b2ab9c", 3, "pa"], ["#a39d90", 3, "pa"], ["#9a9182", 2, "pa"], ["#c0b8a6", 2, "pa"],
         ["#8f8b82", 1, "pa"]]
HOSE_Q = [["#5a5446", 3, "pa"], ["#4f4a3e", 3, "pa"], ["#6b5d45", 2, "pa"], ["#5e5a52", 1, "pa"]]
WRAPS_Q = [["#a69c86", 3, "pa"], ["#8a7f6a", 2, "pa"], ["#bdb39c", 1, "pa"]]


def build(kit):
    """Quarryman: rough dust-whitened wool tunic, linen coif or felt cap, leather gloves and
    knee pads, leg wraps, iron pick over the right fist; some carry splitting wedges."""
    kit.anim = {"work": "pick"}
    kit_body(kit, tunic_slot="tunic", hose_slot="hose", shoe="boots", sleeves=("full", "rolled"), sleeve_w=(1, 3),
             male_hem=0.66)
    kit.slot("tunic", DUSTY + UNDYED[:2])
    kit.slot("hose", HOSE_Q)
    kit.slot("boots", [["#5a4632", 3, "pa"], ["#4a3a2a", 2, "pa"], ["#6a5640", 1, "pa"]])
    kit.slot("wraps", WRAPS_Q)
    kit.slot("gloves", [["#5c4330", 3, "pa"], ["#4a3424", 2, "pa"], ["#6d5440", 1, "pa"]])
    kit.slot("cap", [["#6f6552", 2, "pa"], ["#5a5446", 2, "pa"], ["#4b4a46", 1, "pa"]])
    kit.slot("hood", [["#7a7466", 2, "pa"], ["#6b5d45", 2, "pa"]])
    kit_heads(kit, {"hat:coif": (4, 0), "hat:cap": (3, 0), "hat:hood": (1, 0), "hat:bare": (2, 0),
                    "hair:short": (4, 0), "hair:long": (1, 0), "hair:bald": (2, 0),
                    "beard:none": (1, 1), "beard:short": (3, 0), "beard:full": (3, 0), "beard:moustache": (1, 0)})

    # Rough sacking shoulder pad (signature, always drawn): carries the blocks and the pick.
    sack = kit.mat("sacking", "#8c7d5e", roughness=0.95)
    bm = kit.bm("body", "sex:m")
    add_tube(bm, [((0, 0.01, 1.30), 0.235, 0.165), ((0, 0.01, 1.40), 0.215, 0.14), ((0, 0.01, 1.455), 0.12, 0.09)],
             segs=10, mat_idx=sack, cap1=False)

    # Leather gloves, always: thick mitten + cuff.
    gl = kit.mat("slot:gloves")
    for side, sx in (("arm_R", -1), ("arm_L", 1)):
        bm = kit.bm(side)
        add_ellipsoid(bm, (sx * 0.24, -0.065, 0.80), (0.037, 0.049, 0.065), segs=8, rings=5, mat_idx=gl)
        add_tube(bm, [((sx * 0.237, -0.03, 0.94), 0.056, 0.058), ((sx * 0.239, -0.055, 0.84), 0.046, 0.049)],
                 segs=8, mat_idx=gl)

    # Legs: wraps from ankle to knee over the hose (most), or bare hose; leather knee pad.
    kit.option("legs", "wraps", 3, 1)
    kit.option("legs", "hose", 1, 1)
    wr = kit.mat("slot:wraps")
    rope = kit.mat("binding", "#a08a62", roughness=0.9)
    lt = kit.mat("leather_tan")
    for side, sx in (("leg_R", -1), ("leg_L", 1)):
        x = sx * 0.095
        bm = kit.bm(side, "legs:wraps")
        add_tube(bm, [((x, -0.004, 0.45), 0.063, 0.065), ((x, 0.0, 0.10), 0.05, 0.052)], segs=8, mat_idx=wr)
        for z in (0.2, 0.32):
            w = 0.054 + 0.03 * (z - 0.1)
            add_tube(bm, [((x, -0.004, z - 0.015), w + 0.005, w + 0.007), ((x, -0.004, z + 0.015), w + 0.005, w + 0.007)],
                     segs=8, mat_idx=rope, cap0=False, cap1=False)
        bm = kit.bm(side)
        add_ellipsoid(bm, (x, -0.052, 0.5), (0.05, 0.022, 0.06), segs=6, rings=4, mat_idx=lt)

    # Iron pick in the right fist: ash haft forward-down through the fist, double-pointed
    # iron head across its far end (it strikes the face at chest height in the pick loop).
    bm = kit.bm("arm_R")
    wa, ir, st = kit.mat("wood_ash"), kit.mat("iron_dark"), kit.mat("iron_steel")
    hand = Vector((-0.24, -0.065, 0.80))
    al = 0.7
    d = Vector((0, -math.sin(al), -math.cos(al)))
    p = Vector((0, math.cos(al), -math.sin(al)))           # square to the haft, in the YZ plane
    butt, head = hand - d * 0.12, hand + d * 0.62
    add_tube(bm, [(tuple(butt), 0.02, 0.02), (tuple(hand), 0.02, 0.02), (tuple(head), 0.024, 0.024)],
             segs=6, mat_idx=wa)
    add_tube(bm, [(tuple(head - p * 0.04), 0.04, 0.04), (tuple(head + p * 0.04), 0.04, 0.04)], segs=6, mat_idx=ir,
             smooth=False)                                    # eye
    for sgn in (-1, 1):                                       # the two tapering points, curving back
        add_tube(bm, [(tuple(head + p * sgn * 0.04), 0.034, 0.03), (tuple(head + p * sgn * 0.18 + d * 0.02), 0.02, 0.018),
                      (tuple(head + p * sgn * 0.3 + d * 0.07), 0.005, 0.005)], segs=4, mat_idx=st, smooth=False)

    # Splitting wedges in a belt frog (optional) and a water skin (optional).
    kit.option("wedges", "yes", 2, 0)
    kit.option("wedges", "no", 2, 1)
    bm = kit.bm("body", "wedges:yes+sex:m")
    add_box(bm, 0.135, -0.118, 0.925, 0.085, 0.014, 0.075, mat_idx=lt)
    for x, y, z in ((0.115, -0.125, 0.84), (0.155, -0.11, 0.85)):
        add_tapered_box(bm, x, y, z, 0.03, 0.008, 0.035, 0.03, 0.11, mat_idx=ir)
    kit.option("flask", "yes", 1, 0)
    kit.option("flask", "no", 2, 1)
    add_ellipsoid(kit.bm("body", "flask:yes+sex:m"), (0.17, 0.06, 0.86), (0.04, 0.05, 0.08), segs=8, rings=5,
                  mat_idx=kit.mat("waterskin", "#6b4e32", roughness=0.6))
