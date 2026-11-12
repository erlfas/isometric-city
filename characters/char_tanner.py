# Kit: char_tanner. Loaded by build_characters.py (load_kit_builders); runs with its globals.

def build(kit):
    """Tanner: high greased boots, oiled leather apron, curved fleshing knife."""
    kit.anim = {"work": "scrape"}
    kit_body(kit, tunic_slot="tunic", hose_slot="hose", shoe="boots", sleeves=("full", "rolled"), sleeve_w=(1, 3))
    kit.slot("tunic", [["#5f6346", 3, "pab"], ["#6b5d45", 3, "pab"], ["#555a4a", 2, "pab"]] + UNDYED + DYED[:3])
    kit.slot("hose", HOSE)
    kit.slot("boots", OILED)
    kit.slot("apron", OILED)
    kit.slot("hood", [["#4d4536", 2, "pab"], ["#3c3a33", 2, "pab"], ["#5c4a36", 1, "pab"]])
    kit.slot("cap", [["#4a3d2e", 2, "pab"], ["#3b3a35", 1, "pab"]])
    kit_heads(kit, {"hat:coif": (4, 1), "hat:cap": (2, 0), "hat:hood": (1, 0), "hat:bare": (2, 0),
                    "hat:kerchief": (0, 3), "hat:veil": (0, 2),
                    "hair:short": (4, 0), "hair:long": (1, 0), "hair:bald": (1, 0),
                    "beard:none": (2, 1), "beard:short": (3, 0), "beard:full": (2, 0), "beard:moustache": (1, 0)})
    kit.option("apron", "bib", 3, 3)
    kit.option("apron", "waist", 1, 2)
    kit_bib_apron(kit, "apron:bib", "apron")
    kit_bib_apron(kit, "apron:waist", "apron", bottom=0.36, waist_only=True)

    # Two-handled fleshing knife hanging from the right fist: grip, broad blade bowed
    # slightly forward, far handle. (A thin blade curling forward read as a hook.)
    bm = kit.bm("arm_R")
    wd, st = kit.mat("wood_dark"), kit.mat("iron_steel")
    add_tube(bm, [((-0.24, -0.065, 0.86), 0.016, 0.016), ((-0.24, -0.07, 0.74), 0.016, 0.016)], segs=6, mat_idx=wd)
    add_tube(bm, [((-0.24, -0.07, 0.74), 0.005, 0.02), ((-0.24, -0.09, 0.64), 0.005, 0.026),
                  ((-0.24, -0.1, 0.52), 0.005, 0.026), ((-0.24, -0.09, 0.42), 0.005, 0.02)],
             segs=4, mat_idx=st, smooth=False)
    add_tube(bm, [((-0.24, -0.09, 0.42), 0.016, 0.016), ((-0.24, -0.085, 0.31), 0.016, 0.016)], segs=6, mat_idx=wd)
    # Belt pouch (optional) on the left hip.
    kit.option("pouch", "yes", 2, 2)
    kit.option("pouch", "no", 1, 1)
    for sex, (x, y) in {"m": (0.17, -0.06), "f": (0.15, -0.05)}.items():
        bm = kit.bm("body", f"pouch:yes+sex:{sex}")
        add_ellipsoid(bm, (x, y, 0.88), (0.035, 0.05, 0.065), segs=8, rings=5, mat_idx=kit.mat("leather_tan"))
