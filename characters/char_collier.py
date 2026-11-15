# Kit: char_collier. Loaded by build_characters.py (load_kit_builders); runs with its globals.
# Colliers are men (plebeian charcoal burners living out at the ironworks clamp).

SOOT_SMOCK = [["#4a4640", 3, "pa"], ["#3d3a35", 3, "pa"], ["#55504a", 2, "pa"], ["#5a4e40", 1, "pa"]]
SOOT_HOOD = [["#2f2c28", 3, "pa"], ["#3a3129", 2, "pa"], ["#3d4234", 1, "pa"]]
TROUSERS_C = [["#3f3a30", 3, "pa"], ["#4a4636", 2, "pa"], ["#35322c", 2, "pa"]]


def build(kit):
    """Collier: long sooty smock to the knee, deep hood with a shoulder cape, leather
    leggings, long wooden rake held two-handed out in front; a turf spade at the back."""
    kit.anim = {"work": "rake"}
    kit_body(kit, tunic_slot="smock", hose_slot="hose", shoe="boots", sleeves=("full", "rolled"), sleeve_w=(3, 1),
             male_hem=0.5)
    kit.slot("smock", SOOT_SMOCK)
    kit.slot("hose", TROUSERS_C)
    kit.slot("boots", [["#3a2a1c", 3, "pa"], ["#2f241a", 2, "pa"]])
    kit.slot("hood", SOOT_HOOD)
    kit.slot("cap", [["#2f2c28", 2, "pa"], ["#3a2a1c", 1, "pa"]])
    kit_heads(kit, {"hat:hood": (5, 0), "hat:cap": (1, 0), "hat:bare": (1, 0),
                    "hair:short": (3, 0), "hair:long": (3, 0), "hair:bald": (1, 0),
                    "beard:none": (1, 1), "beard:short": (2, 0), "beard:full": (5, 0), "beard:moustache": (1, 0)})
    # Hood cape over the shoulders (with the hood up or pushed back).
    hd = kit.mat("slot:hood")
    bm = kit.bm("body", "sex:m")
    add_tube(bm, [((0, 0.01, 1.24), 0.275, 0.2), ((0, 0.01, 1.38), 0.225, 0.16), ((0, 0.01, 1.46), 0.11, 0.1)],
             segs=10, mat_idx=hd, cap1=False)
    kit.option("hat", "back", 2, 0)
    add_tube(kit.bm("head", "hat:back"), [((0, 0.075, 1.50), 0.08, 0.035), ((0, 0.13, 1.57), 0.09, 0.05),
                                          ((0, 0.15, 1.65), 0.05, 0.04)], segs=8, mat_idx=hd)

    # Smock hem flare (signature): the long smock widens below the belt.
    sm = kit.mat("slot:smock")
    add_tube(bm, [((0, 0.0, 0.42), 0.235, 0.18), ((0, 0.0, 0.62), 0.215, 0.158)], segs=10, mat_idx=sm, cap1=False)

    # Leather leggings tied below the knee.
    lt = kit.mat("leather_tan")
    for side, sx in (("leg_R", -1), ("leg_L", 1)):
        x = sx * 0.095
        add_tube(kit.bm(side), [((x, -0.006, 0.44), 0.064, 0.066), ((x, 0.0, 0.12), 0.052, 0.054)], segs=8,
                 mat_idx=kit.mat("legging", "#4a3a2a", roughness=0.75))

    # Long wooden rake in the right fist (the left hand rides it further up): shaft forward and
    # down to the ground well ahead, wooden head across its end with short tines.
    bm = kit.bm("arm_R")
    wa, wd = kit.mat("wood_ash"), kit.mat("wood_dark")
    hand = Vector((-0.24, -0.065, 0.80))
    al = 1.05                                               # from vertical: a long low reach
    d = Vector((0, -math.sin(al), -math.cos(al)))
    end = hand + d * 1.45
    add_tube(bm, [(tuple(hand - d * 0.35), 0.016, 0.016), (tuple(hand), 0.017, 0.017), (tuple(end), 0.018, 0.018)],
             segs=6, mat_idx=wa)
    add_box(bm, end.x, end.y, end.z, 0.42, 0.04, 0.04, mat_idx=wd)
    for k in range(5):
        tx = end.x - 0.17 + k * 0.085
        add_box(bm, tx, end.y + 0.01, end.z - 0.05, 0.018, 0.018, 0.08, mat_idx=wd)

    # Turf spade slung across the back (optional).
    kit.option("spade", "yes", 2, 0)
    kit.option("spade", "no", 1, 1)
    bm = kit.bm("body", "spade:yes+sex:m")
    a, b = Vector((-0.2, 0.17, 1.38)), Vector((0.16, 0.19, 0.7))
    add_tube(bm, [(tuple(a), 0.016, 0.016), (tuple(b), 0.017, 0.017)], segs=6, mat_idx=wa)
    add_box(bm, 0.2, 0.2, 0.6, 0.16, 0.025, 0.2, mat_idx=kit.mat("iron_dark"))

    # Charcoal sack at the hip (optional).
    kit.option("sack", "yes", 1, 0)
    kit.option("sack", "no", 2, 1)
    add_ellipsoid(kit.bm("body", "sack:yes+sex:m"), (-0.18, 0.02, 0.84), (0.05, 0.06, 0.09), segs=8, rings=5,
                  mat_idx=kit.mat("coal_sack", "#2c2925", roughness=0.95))
