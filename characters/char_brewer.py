# Kit: char_brewer (also drawn for coopers). Loaded by build_characters.py (load_kit_builders); runs with its globals.

REDS = [["#8c2f2a", 3, "pabr"], ["#7a3a2c", 3, "pab"], ["#9a3f2c", 2, "abr"], ["#6e2f28", 2, "pab"],
        ["#a2502f", 1, "ab"]]


def _apron_front_y(sex, z, bottom=0.30):
    """Front face (-y) of kit_bib_apron's skirt panel at height z."""
    yb, yt = {"m": (-0.215, -0.135), "f": (-0.205, -0.125)}[sex]
    return yb + (yt - yb) * (z - bottom) / (0.99 - bottom)


def _chaperon(kit):
    """Padded chaperon: cloth shell over the head and ears, a thick roll round the brow,
    a puffed crown and a short tail hanging at the back-left."""
    cx, cy, cz = HEAD_C
    rx, ry, rz = HEAD_R
    m = kit.mat("slot:chaperon")
    bm = kit.bm("head", "hat:chaperon")
    add_ellipsoid(bm, (cx, cy + 0.012, cz + 0.012), (rx * 1.17, ry * 1.14, rz * 1.1), segs=10, rings=7,
                  mat_idx=m, keep=lambda x, y, z: z > -0.5 and not (y < -0.45 and z < 0.4))
    ring = []
    for i in range(11):
        a = i / 10 * math.tau
        ring.append(((math.cos(a) * rx * 1.22, cy + 0.01 + math.sin(a) * ry * 1.2, cz + 0.06), 0.036, 0.03))
    add_tube(bm, ring, segs=6, mat_idx=m)
    add_ellipsoid(bm, (0.012, cy + 0.02, cz + 0.105), (rx * 1.05, ry * 1.0, 0.06), segs=8, rings=5, mat_idx=m,
                  keep=lambda x, y, z: z > -0.2)
    add_tube(bm, [((0.07, 0.11, 1.68), 0.032, 0.026), ((0.11, 0.145, 1.58), 0.03, 0.02),
                  ((0.125, 0.155, 1.47), 0.024, 0.014)], segs=6, mat_idx=m)
    add_fringe(bm, kit.mat("slot:hair"))


def build(kit):
    """Brewer: red cotte, stained bib apron with a rope girdle, chaperon, mash paddle, tankard."""
    kit.anim = {"work": "mash"}
    kit_body(kit, tunic_slot="tunic", hose_slot="hose", shoe="boots", sleeves=("full", "rolled"), sleeve_w=(1, 2))
    kit.slot("tunic", REDS + [["#7d6a4a", 1, "pa"], ["#5f6b3a", 1, "ab"]])
    kit.slot("hose", HOSE)
    kit.slot("boots", LEATHER + [["#5a4430", 2, "pab"]])
    kit.slot("belt", [["#a08a5c", 3, "pabr"], ["#8d7a52", 2, "pabr"]])   # rope girdle
    kit.slot("apron", [["#3d3832", 3, "pabr"], ["#47403a", 2, "pabr"], ["#352f2a", 2, "pabr"],
                       ["#4a3b2e", 2, "pabr"]])
    kit.slot("chaperon", [["#2f4a73", 3, "pabr"], ["#3b5680", 2, "abr"], ["#5a2a2a", 1, "abr"],
                          ["#3e4f3a", 1, "pab"], ["#4d4536", 1, "pa"]])
    kit.slot("hood", [["#4d4536", 2, "pab"], ["#3c3a33", 1, "pab"], ["#2f4a73", 1, "ab"]])
    kit.slot("cap", [["#4a3d2e", 2, "pab"], ["#2f3f63", 1, "ab"]])
    kit_heads(kit, {"hat:coif": (1, 1), "hat:cap": (1, 0), "hat:hood": (1, 1), "hat:bare": (1, 0),
                    "hat:kerchief": (0, 4), "hat:veil": (0, 2),
                    "hair:short": (4, 0), "hair:long": (1, 0), "hair:bald": (1, 0),
                    "beard:none": (2, 1), "beard:short": (3, 0), "beard:full": (3, 0), "beard:moustache": (1, 0)})
    kit.option("hat", "chaperon", 7, 2)
    _chaperon(kit)

    # Stained bib apron, rope girdle knotted over it with hanging ends, rusty stains.
    kit.option("apron", "bib", 1, 1)
    kit_bib_apron(kit, "apron:bib", "apron")
    rope, stain = kit.mat("slot:belt"), kit.mat("stain", "#55402e", roughness=0.95)
    for sex in ("m", "f"):
        bm = kit.bm("body", f"apron:bib+sex:{sex}")
        hw = 0.165 if sex == "m" else 0.15
        yf = _apron_front_y(sex, 0.97) - 0.008
        add_tube(bm, [((-hw, yf + 0.03, 0.97), 0.011, 0.011), ((0, yf, 0.97), 0.011, 0.011),
                      ((hw, yf + 0.03, 0.97), 0.011, 0.011)], segs=4, mat_idx=rope)
        for dx, z1 in ((-0.03, 0.70), (0.0, 0.76)):
            add_tube(bm, [((0.03, yf - 0.006, 0.965), 0.01, 0.01),
                          ((0.03 + dx, _apron_front_y(sex, z1) - 0.012, z1), 0.009, 0.009)], segs=4, mat_idx=rope)
        for (x, z, rx, rz) in ((-0.08, 0.60, 0.075, 0.09), (0.09, 0.44, 0.06, 0.07)):
            add_ellipsoid(bm, (x, _apron_front_y(sex, z) - 0.001, z), (rx, 0.006, rz), segs=6, rings=3,
                          mat_idx=stain, smooth=False)

    # Mash paddle, upright in the right fist, in front of the forearm: ash shaft, broad blade at the foot.
    bm = kit.bm("arm_R")
    wa, wd = kit.mat("wood_ash"), kit.mat("wood_dark")
    add_tube(bm, [((-0.245, -0.10, 0.36), 0.021, 0.021), ((-0.245, -0.10, 1.62), 0.019, 0.019)], segs=6, mat_idx=wa)
    add_tube(bm, [((-0.245, -0.10, 0.05), 0.05, 0.013), ((-0.245, -0.10, 0.30), 0.058, 0.013),
                  ((-0.245, -0.10, 0.38), 0.02, 0.012)], segs=6, mat_idx=kit.mat("paddle", "#8a5634", roughness=0.7), smooth=False)

    # Wooden tankard in the left fist (optional): staves, two dark hoops, handle into the grip.
    kit.option("tankard", "yes", 1, 1)
    kit.option("tankard", "no", 1, 1)
    bm = kit.bm("arm_L", "tankard:yes")
    c = (0.245, -0.15, 0.80)
    add_tube(bm, [((c[0], c[1], 0.735), 0.048, 0.048), ((c[0], c[1], 0.865), 0.044, 0.044)], segs=8, mat_idx=wa)
    for z in (0.75, 0.85):
        add_tube(bm, [((c[0], c[1], z - 0.007), 0.051, 0.051), ((c[0], c[1], z + 0.007), 0.049, 0.049)],
                 segs=8, mat_idx=wd, cap0=False, cap1=False)
    add_tube(bm, [((c[0], c[1] + 0.04, 0.845), 0.009, 0.009), ((c[0], -0.075, 0.83), 0.009, 0.009),
                  ((c[0], -0.075, 0.77), 0.009, 0.009), ((c[0], c[1] + 0.04, 0.76), 0.009, 0.009)],
             segs=4, mat_idx=wd)

    # Belt pouch (optional) on the left hip.
    kit.option("pouch", "yes", 1, 1)
    kit.option("pouch", "no", 1, 1)
    for sex, (x, y) in {"m": (0.17, -0.04), "f": (0.155, -0.04)}.items():
        bm = kit.bm("body", f"pouch:yes+sex:{sex}")
        add_ellipsoid(bm, (x, y, 0.88), (0.032, 0.05, 0.06), segs=8, rings=5, mat_idx=kit.mat("leather_tan"))
