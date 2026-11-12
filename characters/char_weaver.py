# Kit: char_weaver. Loaded by build_characters.py (load_kit_builders); runs with its globals.
# Also drawn for tailors and ropers.

# Torso profiles copied from kit_body, redrawn with 12 segments so the ring splits
# exactly at x = 0 (vertices at 90 and 270 degrees) for the mi-parti halves.
WEAVER_TORSO = {
    "m": [((0, 0.0, 0.62), 0.215, 0.155), ((0, 0, 0.80), 0.185, 0.13),
          ((0, 0, 0.98), 0.165, 0.115), ((0, 0, 1.18), 0.19, 0.13),
          ((0, 0, 1.35), 0.205, 0.125), ((0, 0, 1.40), 0.2, 0.112),
          ((0, 0, 1.44), 0.13, 0.078), ((0, 0, 1.475), 0.075, 0.065)],
    "f": [((0, 0.0, 0.07), 0.25, 0.22), ((0, 0, 0.55), 0.205, 0.17),
          ((0, 0, 0.98), 0.15, 0.105), ((0, -0.005, 1.16), 0.165, 0.125),
          ((0, 0, 1.33), 0.18, 0.11), ((0, 0, 1.385), 0.185, 0.1),
          ((0, 0, 1.43), 0.12, 0.075), ((0, 0, 1.465), 0.07, 0.06)],
}
WEAVER_BELT = {"m": (0.95, 1.0, 0.172, 0.122), "f": (0.96, 1.0, 0.155, 0.11)}


def weaver_split(faces, left_mat):
    """Faces on the character's left (+X) take left_mat: the second colour of the mi-parti."""
    for f in faces:
        if f.calc_center_median().x > 1e-4:
            f.material_index = left_mat


def weaver_liripipe(kit, key, wm, wf):
    """Hood with shoulder cape; its long tail runs from a peak at the crown round the left side
    and hangs down the front of the chest, where the isometric camera sees it. All in the head
    part, so the work loop keeps head pitch near zero (pitching down would sink it in the chest)."""
    kit.option("hat", key.split(":")[1], wm, wf)
    m = kit.mat("slot:hood")
    cx, cy, cz = HEAD_C
    rx, ry, rz = HEAD_R
    bm = kit.bm("head", key)
    add_ellipsoid(bm, (cx, cy + 0.015, cz + 0.015), (rx * 1.26, ry * 1.22, rz * 1.15), segs=12, rings=8,
                  mat_idx=m, keep=lambda x, y, z: not (y < -0.42 and -0.75 < z < 0.5))
    add_tube(bm, [((0, 0.01, 1.30), 0.27, 0.2), ((0, 0.01, 1.42), 0.17, 0.14), ((0, 0.015, 1.50), 0.1, 0.1)],
             segs=10, mat_idx=m, cap1=False)
    add_tube(bm, [((0, 0.06, 1.75), 0.05, 0.045), ((0.05, 0.13, 1.71), 0.04, 0.036),
                  ((0.13, 0.11, 1.62), 0.032, 0.03), ((0.16, 0.0, 1.50), 0.03, 0.028),
                  ((0.16, -0.11, 1.40), 0.028, 0.026), ((0.14, -0.215, 1.28), 0.026, 0.024),
                  ((0.13, -0.19, 1.16), 0.024, 0.02), ((0.125, -0.185, 1.05), 0.018, 0.014)],
             segs=6, mat_idx=m)


def build(kit):
    """Weaver: mi-parti cotte (two-colour halves), liripipe hood, shuttle, shears."""
    kit.anim = {"work": "weave"}
    kit_body(kit, tunic_slot="tunic", hose_slot="hose", shoe="shoes", sleeves=("full", "rolled"), sleeve_w=(4, 1))
    tun, par, belt = kit.mat("slot:tunic"), kit.mat("slot:parti"), kit.mat("slot:belt")

    # Mi-parti torso: replace kit_body's torsos with 12-segment ones split down the middle.
    for sex in ("m", "f"):
        kit.parts[("body", f"sex:{sex}")].free()
        bm = kit.parts[("body", f"sex:{sex}")] = bmesh.new()
        weaver_split(add_tube(bm, WEAVER_TORSO[sex], segs=12, mat_idx=tun), par)
        z0, z1, bx, by = WEAVER_BELT[sex]
        add_tube(bm, [((0, 0, z0), bx, by), ((0, 0, z1), bx, by)], segs=12, mat_idx=belt)
    # Left arm in the second colour (base sleeve and both forearm options).
    for key in (("arm_L", ""), ("arm_L", "sleeves:full"), ("arm_L", "sleeves:rolled")):
        for f in kit.parts[key].faces:
            if f.material_index == tun:
                f.material_index = par

    # Right half warm (madder, wine, ochre), left half cool (woad, green, dark), so any pair contrasts.
    kit.slot("tunic", [["#8c2f2a", 3, "pabr"], ["#9a4a2a", 2, "pab"], ["#6e2a33", 2, "abr"],
                       ["#a07a38", 2, "pab"], ["#8a7f6a", 1, "pa"]])
    kit.slot("parti", [["#2f3f63", 3, "abr"], ["#4b5a6e", 2, "pab"], ["#3e4f3a", 2, "pab"],
                       ["#5a3a5e", 1, "abr"], ["#3b3f45", 1, "pa"]])
    kit.slot("hose", HOSE)
    kit.slot("hood", [["#5e1f2a", 3, "pabr"], ["#6e2f28", 2, "pab"], ["#2a3550", 2, "abr"],
                      ["#3c3a33", 1, "pa"], ["#3e4f3a", 1, "pab"]])
    kit.slot("cap", [["#3a2a1c", 2, "pab"], ["#5e1f2a", 1, "ab"], ["#2a3550", 1, "ab"]])
    kit.slot("yarn", LINEN[:2] + [["#b9a27a", 2, "pa"], ["#a86656", 2, "ab"], ["#7e8ea3", 2, "abr"],
                                  ["#b8963f", 1, "ab"]])
    weaver_liripipe(kit, "hat:liripipe", 4, 1)
    kit_heads(kit, {"hat:hood": (1, 0), "hat:cap": (2, 0), "hat:bare": (2, 0), "hat:coif": (1, 1),
                    "hat:kerchief": (0, 3), "hat:veil": (0, 3),
                    "hair:short": (4, 0), "hair:long": (1, 0), "hair:bald": (1, 0),
                    "beard:none": (2, 1), "beard:short": (3, 0), "beard:full": (1, 0), "beard:moustache": (1, 0)})

    # Tailor's shears hanging from the right fist, blades splayed a little.
    bm = kit.bm("arm_R")
    st = kit.mat("iron_steel")
    for (y0, y1) in ((-0.06, -0.15), (-0.075, -0.0)):
        add_tube(bm, [((-0.24, y0, 0.765), 0.006, 0.024), ((-0.24, (y0 + y1) / 2, 0.64), 0.005, 0.018),
                      ((-0.24, y1, 0.51), 0.004, 0.005)], segs=4, mat_idx=st, smooth=False)
    add_tube(bm, [((-0.262, -0.068, 0.765), 0.014, 0.014), ((-0.218, -0.068, 0.765), 0.014, 0.014)],
             segs=6, mat_idx=st)  # rivet
    # Shuttle gripped at its back end in the left fist, pointing out and a little forward: a
    # pointed boat of brown wood with a pale pirn of weft in its slot. (Pointing forward, it
    # projects straight down in the isometric view and reads as a carrot.)
    bm = kit.bm("arm_L")
    sw = kit.mat("shuttle", "#6a4428", roughness=0.6)
    a, d = Vector((0.215, -0.06, 0.80)), Vector((0.95, -0.3, 0.0)).normalized()
    add_tube(bm, [(tuple(a + d * s), r, r * 0.8) for s, r in
                  ((0.0, 0.006), (0.04, 0.026), (0.2, 0.03), (0.27, 0.022), (0.31, 0.004))], segs=6, mat_idx=sw)
    add_ellipsoid(bm, tuple(a + d * 0.155 + Vector((0, 0, 0.018))), (0.05, 0.024, 0.017), segs=6, rings=4,
                  mat_idx=kit.mat("slot:yarn"))

    # At the belt front: a leather pouch (right) and/or a hank of yarn (left).
    kit.option("belt", "pouch", 2, 2)
    kit.option("belt", "skein", 2, 2)
    kit.option("belt", "both", 1, 1)
    kit.option("belt", "none", 1, 1)
    for opt in ("pouch", "both"):
        for sex in ("m", "f"):
            bm = kit.bm("body", f"belt:{opt}+sex:{sex}")
            add_ellipsoid(bm, (-0.10, -0.145, 0.88), (0.04, 0.026, 0.05), segs=8, rings=5, mat_idx=kit.mat("leather_tan"))
            add_tube(bm, [((-0.10, -0.135, 0.93), 0.008, 0.004), ((-0.10, -0.12, 0.975), 0.008, 0.004)],
                     segs=4, mat_idx=kit.mat("leather_tan"))
    for opt in ("skein", "both"):
        for sex in ("m", "f"):
            bm = kit.bm("body", f"belt:{opt}+sex:{sex}")
            y = kit.mat("slot:yarn")
            add_tube(bm, [((0.09, -0.13, 0.975), 0.03, 0.014), ((0.10, -0.15, 0.90), 0.036, 0.018),
                          ((0.10, -0.15, 0.82), 0.03, 0.016), ((0.10, -0.14, 0.79), 0.018, 0.012)],
                     segs=6, mat_idx=y)
