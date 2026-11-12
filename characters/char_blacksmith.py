# Kit: char_blacksmith. Loaded by build_characters.py (load_kit_builders); runs with its globals.

def build(kit):
    """Blacksmith: linen shirt, long leather apron, cross-peen hammer, tongs."""
    kit.anim = {"work": "hammer"}
    kit_body(kit, tunic_slot="tunic", hose_slot="hose", shoe="shoes", sleeves=("full", "rolled"), sleeve_w=(1, 4))
    kit.slot("tunic", LINEN + [["#a39a86", 3, "pab"], ["#7d7668", 2, "pab"]] + UNDYED[:2])  # sooty linen
    kit.slot("hose", HOSE)
    kit.slot("apron", LEATHER + [["#5a3e26", 2, "pabr"]])
    kit.slot("cap", [["#3a2a1c", 2, "pab"], ["#4b4a46", 1, "pab"]])
    kit.slot("hood", [["#3c3a33", 1, "pab"]])
    kit_heads(kit, {"hat:bare": (3, 0), "hat:coif": (2, 1), "hat:cap": (3, 0),
                    "hat:kerchief": (0, 3), "hat:veil": (0, 1),
                    "hair:short": (4, 0), "hair:long": (1, 0), "hair:bald": (2, 0),
                    "beard:none": (1, 1), "beard:short": (3, 0), "beard:full": (3, 0), "beard:moustache": (1, 0)})
    kit.option("apron", "bib", 1, 1)
    kit_bib_apron(kit, "apron:bib", "apron", bottom=0.26, top=1.33)

    # Leather gloves (optional): thick mitten + cuff over each hand.
    kit.option("gloves", "yes", 1, 1)
    kit.option("gloves", "no", 2, 2)
    for side, sx in (("arm_R", -1), ("arm_L", 1)):
        bm = kit.bm(side, "gloves:yes")
        lt = kit.mat("leather_tan")
        add_ellipsoid(bm, (sx * 0.24, -0.065, 0.80), (0.036, 0.048, 0.064), segs=8, rings=5, mat_idx=lt)
        add_tube(bm, [((sx * 0.239, -0.055, 0.90), 0.05, 0.052), ((sx * 0.24, -0.06, 0.83), 0.045, 0.047)],
                 segs=8, mat_idx=lt)

    # Cross-peen hammer in the right fist: handle forward-down, head across its end.
    bm = kit.bm("arm_R")
    wa, ir = kit.mat("wood_ash"), kit.mat("iron_dark")
    a, b = Vector((-0.24, 0.02, 0.81)), Vector((-0.24, -0.25, 0.68))
    add_tube(bm, [(tuple(a), 0.014, 0.014), (tuple(b), 0.016, 0.016)], segs=6, mat_idx=wa)
    d = (b - a).normalized()
    perp = Vector((0, d.z, -d.y))   # in the YZ plane, square to the handle
    add_tube(bm, [(tuple(b - perp * 0.06), 0.024, 0.024), (tuple(b + perp * 0.075), 0.022, 0.018)],
             segs=4, mat_idx=ir, smooth=False)
    # Tongs in the left hand (optional).
    kit.option("tongs", "yes", 2, 2)
    kit.option("tongs", "no", 1, 1)
    bm = kit.bm("arm_L", "tongs:yes")
    for dx in (-0.012, 0.012):
        add_tube(bm, [((0.24 + dx, -0.03, 0.83), 0.007, 0.007), ((0.24 + dx * 0.4, -0.16, 0.66), 0.007, 0.007),
                      ((0.24 + dx * 1.4, -0.22, 0.52), 0.008, 0.008)], segs=4, mat_idx=ir, smooth=False)
