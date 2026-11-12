# Kit: char_baker. Loaded by build_characters.py (load_kit_builders); runs with its globals.

def _apron_front(bottom, yb, yt, z, lift=0.004):
    """y of the front face of a kit_bib_apron skirt panel at height z, pushed out by lift."""
    return yb + (yt - yb) * (z - bottom) / (0.99 - bottom) - lift


def build(kit):
    """Baker: flour-white apron, puffed linen cap, long bread peel, loaf in hand."""
    kit.anim = {"work": "knead"}
    kit_body(kit, tunic_slot="tunic", hose_slot="hose", shoe="shoes", sleeves=("full", "rolled"), sleeve_w=(1, 3))
    # Cream linen shirts like the sheet, some undyed or muted wool so the white apron stands out.
    kit.slot("tunic", [["#c2b597", 2, "pab"], ["#ab9d80", 2, "pab"], ["#d6ccb4", 1, "pabr"]]
             + UNDYED + DYED[:4])
    kit.slot("hose", [["#4a3a2a", 3, "pab"], ["#3f3428", 2, "pab"]] + HOSE)
    kit.slot("apron", [["#f2efe7", 3, "pabr"], ["#e9e4d8", 3, "pabr"], ["#f6f3ec", 2, "pabr"]])
    kit.slot("bcap", [["#e4ddcd", 3, "pabr"], ["#d3cab6", 3, "pab"], ["#c8bfac", 2, "pa"]])
    kit.slot("cap", [["#4a3d2e", 1, "pab"]])
    kit.slot("hood", [["#4d4536", 1, "pab"]])
    kit_heads(kit, {"hat:coif": (2, 1), "hat:kerchief": (0, 3), "hat:veil": (0, 1),
                    "hair:short": (4, 0), "hair:long": (1, 0), "hair:bald": (1, 0),
                    "beard:none": (3, 1), "beard:short": (3, 0), "beard:full": (1, 0), "beard:moustache": (1, 0)})

    # Baker's puffed linen cap (barett): band round the head, soft crown flopping back.
    kit.option("hat", "barett", 5, 2)
    bm = kit.bm("head", "hat:barett")
    cm = kit.mat("slot:bcap")
    cx, cy, cz = HEAD_C
    add_tube(bm, [((0, cy + 0.004, 1.683), 0.106, 0.12), ((0, cy + 0.004, 1.718), 0.112, 0.126)],
             segs=12, mat_idx=cm, cap0=False, cap1=False)
    add_ellipsoid(bm, (0, cy + 0.018, 1.738), (0.138, 0.148, 0.052), segs=12, rings=6, mat_idx=cm,
                  keep=lambda x, y, z: z > -0.6)
    add_fringe(bm, kit.mat("slot:hair"))

    # Aprons: bib (most) or waist; flour-and-dough smudges on the skirt.
    kit.option("apron", "bib", 3, 2)
    kit.option("apron", "waist", 1, 2)
    kit_bib_apron(kit, "apron:bib", "apron", bottom=0.34)
    kit_bib_apron(kit, "apron:waist", "apron", bottom=0.40, waist_only=True)
    smudge = kit.mat("dough_smudge", "#d2cab8", roughness=0.95)
    for variant, bottom in (("apron:bib", 0.34), ("apron:waist", 0.40)):
        for sex, (yb, yt) in {"m": (-0.215, -0.135), "f": (-0.205, -0.125)}.items():
            bm = kit.bm("body", f"{variant}+sex:{sex}")
            for (x, z0, z1, w0, w1) in ((-0.07, 0.50, 0.62, 0.07, 0.11), (0.08, 0.72, 0.80, 0.09, 0.05)):
                z0 = max(z0, bottom + 0.04)
                add_panel(bm, z0, z1, w0, w1, _apron_front(bottom, yb, yt, z0), _apron_front(bottom, yb, yt, z1),
                          0.003, smudge, x=x)

    # Flour on the knees of the hose (men; the kirtle hides women's legs).
    kit.option("flour", "knees", 2, 0)
    kit.option("flour", "none", 1, 1)
    flour = kit.mat("flour", "#ece6d8", roughness=0.95)
    for side, sx in (("leg_R", -1), ("leg_L", 1)):
        bm = kit.bm(side, "flour:knees")
        add_ellipsoid(bm, (sx * 0.095, -0.05, 0.50), (0.05, 0.026, 0.08), segs=8, rings=5, mat_idx=flour,
                      keep=lambda x, y, z: y < -0.2)

    # Bread peel upright in the right fist, outside the shoulder so arm swings never clip:
    # ash shaft from hip height to above the head, broad flat blade facing front.
    bm = kit.bm("arm_R")
    wa = kit.mat("peel_wood", "#8a6a48", roughness=0.8)
    x, y = -0.258, -0.068
    add_tube(bm, [((x, y, 0.50), 0.017, 0.017), ((x, y, 1.74), 0.016, 0.016)], segs=6, mat_idx=wa)
    add_tube(bm, [((x, y, 1.70), 0.03, 0.011), ((x, y, 1.77), 0.072, 0.011),
                  ((x, y, 2.0), 0.08, 0.01), ((x, y, 2.05), 0.058, 0.01)], segs=6, mat_idx=wa, smooth=False)

    # Left hand: a round loaf, a long loaf, or empty.
    crust = kit.mat("bread_crust", "#a5662f", roughness=0.85)
    kit.option("loaf", "round", 2, 2)
    kit.option("loaf", "long", 1, 1)
    kit.option("loaf", "none", 1, 1)
    add_ellipsoid(kit.bm("arm_L", "loaf:round"), (0.25, -0.10, 0.76), (0.068, 0.07, 0.045),
                  segs=10, rings=5, mat_idx=crust)
    add_tube(kit.bm("arm_L", "loaf:long"), [((0.25, 0.02, 0.77), 0.022, 0.02), ((0.25, -0.06, 0.78), 0.036, 0.032),
                                             ((0.25, -0.16, 0.78), 0.036, 0.032), ((0.25, -0.23, 0.77), 0.02, 0.018)],
             segs=8, mat_idx=crust)
