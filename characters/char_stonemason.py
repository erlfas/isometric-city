# Kit: char_stonemason. Loaded by build_characters.py (load_kit_builders); runs with its globals.

def split_apron(kit, variant, slot, split=0.62, bottom=0.28, top=1.30, waist_only=False):
    """Mason's leather apron split up the front from the hem, so the two halves part
    over the legs. Same forward tilt as kit_bib_apron, so walking legs clear it."""
    m = kit.mat("slot:" + slot)
    for sex, (wb, wt, yb, yt) in {"m": (0.42, 0.30, -0.22, -0.135), "f": (0.44, 0.28, -0.21, -0.125)}.items():
        def w(z):
            return wb + (wt - wb) * (z - 0.30) / 0.69

        def y(z):
            return yb + (yt - yb) * (z - 0.30) / 0.69
        bm = kit.bm("body", f"{variant}+sex:{sex}")
        add_panel(bm, split, 0.99, w(split), wt, y(split), yt, 0.018, m)
        for sx in (-1, 1):   # the two flaps, splaying slightly at the hem
            add_panel(bm, bottom, split + 0.01, w(bottom) / 2 - 0.012, w(split) / 2 - 0.012,
                      y(bottom), y(split), 0.018, m, x=sx * (w(bottom) + w(split)) / 8 + sx * 0.012)
        if not waist_only:
            yb2 = yt - 0.003
            add_panel(bm, 0.99, top, 0.24, 0.22, yb2, yb2 - 0.004, 0.016, m)
            for sx in (-1, 1):   # neck strap over the shoulders, crossing to the back of the belt
                add_tube(bm, [((sx * 0.1, yb2, top - 0.01), 0.012, 0.006), ((sx * 0.095, -0.06, 1.45), 0.012, 0.006),
                              ((sx * 0.1, 0.11, 1.38), 0.012, 0.006), ((-sx * 0.09, 0.13, 1.0), 0.012, 0.006)],
                             segs=4, mat_idx=m)


def build(kit):
    """Stonemason / quarryman: stone-dust smock, split leather apron, leather gauntlets,
    wooden mallet in the right hand, chisel in the left."""
    kit.anim = {"work": "chisel"}
    kit_body(kit, tunic_slot="smock", hose_slot="hose", shoe="boots", sleeves=("full", "rolled"), sleeve_w=(3, 1))
    # Undyed linen and wool greyed by stone dust.
    kit.slot("smock", [["#a9a498", 3, "pab"], ["#9b968b", 3, "pab"], ["#8e8a80", 2, "pa"],
                       ["#b4ad9e", 2, "pab"], ["#a39782", 2, "pab"], ["#86867e", 2, "pa"], ["#9a8c76", 1, "pa"]])
    kit.slot("hose", [["#3f4238", 3, "pa"], ["#4f4a3e", 3, "pa"], ["#5d4a36", 2, "pab"], ["#3b3f45", 2, "ab"]])
    kit.slot("boots", [["#5a4030", 3, "pab"], ["#4a3626", 2, "pab"], ["#6b4e36", 2, "pab"]])
    kit.slot("apron", [["#6b4a30", 3, "pab"], ["#5a3e26", 3, "pab"], ["#7a5a3c", 2, "pab"], ["#4d3622", 1, "pab"]])
    kit.slot("gloves", [["#4a3424", 3, "pab"], ["#3a2a1c", 2, "pab"], ["#5c4330", 2, "pab"]])
    kit.slot("cap", [["#6f6552", 2, "pab"], ["#4b4a46", 2, "pab"], ["#5d4a36", 1, "pab"]])
    kit.slot("hood", [["#7a7466", 2, "pab"], ["#5a5446", 2, "pab"], ["#6b5d45", 1, "pab"]])
    kit_heads(kit, {"hat:coif": (5, 1), "hat:cap": (2, 0), "hat:hood": (1, 1), "hat:bare": (2, 0),
                    "hat:kerchief": (0, 4), "hat:veil": (0, 1),
                    "hair:short": (4, 0), "hair:long": (1, 0), "hair:bald": (2, 0),
                    "beard:none": (1, 1), "beard:short": (3, 0), "beard:full": (3, 0), "beard:moustache": (1, 0)})

    # Split apron: bib for masons at the banker, waist-only for quarrymen.
    kit.option("apron", "bib", 3, 3)
    kit.option("apron", "waist", 1, 1)
    split_apron(kit, "apron:bib", "apron")
    split_apron(kit, "apron:waist", "apron", split=0.58, bottom=0.34, waist_only=True)

    # Leather gauntlets (trade signature, always drawn): mitten over the hand, flared cuff
    # over the sleeve end.
    gl = kit.mat("slot:gloves")
    for side, sx in (("arm_R", -1), ("arm_L", 1)):
        bm = kit.bm(side)
        add_ellipsoid(bm, (sx * 0.24, -0.065, 0.80), (0.037, 0.049, 0.065), segs=8, rings=5, mat_idx=gl)
        add_tube(bm, [((sx * 0.236, -0.028, 0.955), 0.062, 0.064), ((sx * 0.239, -0.055, 0.84), 0.046, 0.049)],
                 segs=8, mat_idx=gl)

    # Wooden mallet in the right fist: handle forward-down, squared beech block across its end
    # (a round head seen end-on read as a tankard).
    bm = kit.bm("arm_R")
    beech = kit.mat("beech", "#a0805a", roughness=0.8)
    wd = kit.mat("wood_dark")
    a, b = Vector((-0.24, 0.03, 0.82)), Vector((-0.262, -0.25, 0.69))
    add_tube(bm, [(tuple(a), 0.014, 0.014), (tuple(b), 0.016, 0.016)], segs=6, mat_idx=wd)
    d = (b - a).normalized()
    perp = Vector((0, d.z, -d.y)).normalized()   # in the YZ plane, square to the handle
    c = b - d * 0.03
    add_tube(bm, [(tuple(c - perp * 0.085), 0.05, 0.05), (tuple(c + perp * 0.085), 0.055, 0.055)],
             segs=4, mat_idx=beech, smooth=False)

    # Chisel in the left fist: iron shank, steel edge below, mushroomed striking head above.
    bm = kit.bm("arm_L")
    ir, st = kit.mat("iron_dark"), kit.mat("iron_steel")
    butt, tip = Vector((0.212, -0.12, 0.95)), Vector((0.266, -0.015, 0.62))
    add_tube(bm, [(tuple(butt), 0.017, 0.017), (tuple(butt.lerp(tip, 0.75)), 0.013, 0.013)],
             segs=6, mat_idx=st, smooth=False)
    add_tube(bm, [(tuple(butt.lerp(tip, 0.75)), 0.013, 0.013), (tuple(tip), 0.02, 0.003)],
             segs=4, mat_idx=st, smooth=False)
    add_tube(bm, [(tuple(butt + (butt - tip).normalized() * 0.014), 0.014, 0.014), (tuple(butt), 0.022, 0.022)],
             segs=6, mat_idx=ir, smooth=False)

    # Tool pouch on the left hip (optional).
    kit.option("pouch", "yes", 2, 2)
    kit.option("pouch", "no", 1, 1)
    lt = kit.mat("leather_tan")
    for sex, (x, y, z) in {"m": (0.175, -0.04, 0.88), "f": (0.155, -0.03, 0.90)}.items():
        bm = kit.bm("body", f"pouch:yes+sex:{sex}")
        add_ellipsoid(bm, (x, y, z), (0.035, 0.05, 0.065), segs=8, rings=5, mat_idx=lt)
