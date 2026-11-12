# Kit: char_guard. Loaded by build_characters.py (load_kit_builders); runs with its globals.

def _lathe(bm, profile, segs, mat_idx, cx=0.0, cy=0.0):
    """Surface of revolution about the vertical axis through (cx, cy). profile = [(r, z), ...];
    the outside is to the right of the profile direction (walk it top-down for a dome)."""
    rings = []
    for r, z in profile:
        if r < 1e-6:
            rings.append(bm.verts.new(Vector((cx, cy, z))))
        else:
            rings.append([bm.verts.new(Vector((cx + r * math.cos(j / segs * math.tau),
                                                cy + r * math.sin(j / segs * math.tau), z)))
                          for j in range(segs)])
    faces = []
    for a, b in zip(rings, rings[1:]):
        for j in range(segs):
            k = (j + 1) % segs
            if not isinstance(a, list):
                faces.append(bm.faces.new([a, b[j], b[k]]))
            elif not isinstance(b, list):
                faces.append(bm.faces.new([a[j], b, a[k]]))
            else:
                faces.append(bm.faces.new([a[j], b[j], b[k], a[k]]))
    for f in faces:
        f.material_index = mat_idx
        f.smooth = True
    return faces


def _plate(bm, inner, outer, off, mat_idx):
    """Thin closed slab between two matching polylines (blades, prods); off = thickness vector."""
    off = Vector(off)
    I0 = [bm.verts.new(Vector(p) - off / 2) for p in inner]
    O0 = [bm.verts.new(Vector(p) - off / 2) for p in outer]
    I1 = [bm.verts.new(Vector(p) + off / 2) for p in inner]
    O1 = [bm.verts.new(Vector(p) + off / 2) for p in outer]
    faces = []
    n = len(inner)
    for k in range(n - 1):
        faces.append(bm.faces.new([I0[k], O0[k], O0[k + 1], I0[k + 1]]))
        faces.append(bm.faces.new([I1[k + 1], O1[k + 1], O1[k], I1[k]]))
        faces.append(bm.faces.new([I0[k + 1], I1[k + 1], I1[k], I0[k]]))
        faces.append(bm.faces.new([O0[k], O1[k], O1[k + 1], O0[k + 1]]))
    faces.append(bm.faces.new([I0[0], I1[0], O1[0], O0[0]]))
    faces.append(bm.faces.new([O0[-1], O1[-1], I1[-1], I0[-1]]))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.material_index = mat_idx
        f.smooth = False
    return faces


def build(kit):
    """Town guard (also watchmen, crossbowmen): helmet, gambeson, mail collar, red heraldic
    tabard with the gold city gate, halberd grounded at the right foot (or a crossbow), sword."""
    kit.anim = {"work": "watch"}
    kit_body(kit, tunic_slot="gambeson", hose_slot="hose", shoe="boots", sleeves=("full",), sleeve_w=(1,))
    kit.slot("gambeson", [["#b8a77f", 3, "pabr"], ["#a5936b", 3, "pabr"], ["#c6b893", 2, "pabr"],
                          ["#8c7c5c", 2, "pabr"], ["#6f6552", 1, "pabr"]])
    kit.slot("hose", [["#2f2c28", 3, "pabr"], ["#3b3f45", 2, "pabr"], ["#4f4a3e", 2, "pabr"],
                      ["#5d4a36", 1, "pabr"]])
    kit.slot("boots", LEATHER + [["#5a4430", 2, "pabr"]])
    kit.slot("tabard", [["#7a1f1c", 3, "pabr"], ["#8e2a22", 3, "pabr"], ["#6b1818", 2, "pabr"],
                        ["#9a3426", 1, "pabr"]])
    kit_heads(kit, {"hair:short": (4, 0), "hair:long": (1, 0), "hair:bald": (2, 0),
                    "beard:none": (2, 1), "beard:short": (3, 0), "beard:full": (2, 0), "beard:moustache": (2, 0)})

    steel, ird = kit.mat("iron_steel"), kit.mat("iron_dark")
    mail = kit.mat("mail", "#7b7c7f", roughness=0.55, metallic=0.25)
    gold = kit.mat("gold", "#d9a62a", roughness=0.5)
    tab = kit.mat("slot:tabard")
    cx, cy, cz = HEAD_C
    rx, ry, rz = HEAD_R

    # --- body (base): mail collar over the shoulders, tabard front and back, outer belt ---
    bm = kit.bm("body")
    add_tube(bm, [((0, 0.0, 1.27), 0.228, 0.168), ((0, 0.0, 1.36), 0.226, 0.166),
                  ((0, 0.005, 1.425), 0.16, 0.118), ((0, 0.005, 1.475), 0.082, 0.072)],
             segs=10, mat_idx=mail, cap0=False)
    # Panels tilt out at the hem so walking legs clear them.
    add_panel(bm, 0.47, 0.99, 0.33, 0.31, -0.242, -0.152, 0.016, tab)   # front skirt
    add_panel(bm, 0.99, 1.33, 0.31, 0.30, -0.152, -0.152, 0.016, tab)   # chest (top under the mail)
    add_panel(bm, 0.47, 0.99, 0.33, 0.31, 0.226, 0.136, 0.016, tab)     # back skirt
    add_panel(bm, 0.99, 1.33, 0.31, 0.30, 0.136, 0.136, 0.016, tab)
    add_tube(bm, [((0, 0, 0.925), 0.192, 0.17), ((0, 0, 0.965), 0.192, 0.17)], segs=10,
             mat_idx=kit.mat("slot:belt"))
    # Gold city gate on chest and back: two towers and a wall.
    for y, d in ((-0.162, 1), (0.158, -1)):
        add_box(bm, 0, y, 1.13, 0.15, 0.008, 0.09, mat_idx=gold)
        add_box(bm, 0, y, 1.215, 0.04, 0.008, 0.09, mat_idx=gold)
        for sx in (-1, 1):
            add_box(bm, sx * 0.055, y, 1.2, 0.045, 0.008, 0.1, mat_idx=gold)

    # --- helmets (all guards wear one) ---
    kit.option("hat", "kettle", 4, 0)
    kit.option("hat", "chapel", 2, 0)
    kit.option("hat", "bascinet", 2, 0)
    kit.option("hat", "cervelliere", 1, 0)
    hy = cy + 0.008
    # Kettle hat: round skull, brim sloping down.
    _lathe(kit.bm("head", "hat:kettle"), [(0.0, 1.80), (0.07, 1.79), (0.115, 1.76), (0.138, 1.715),
                                          (0.145, 1.668), (0.205, 1.638), (0.202, 1.625), (0.14, 1.654)],
           12, steel, cy=hy)
    # Chapel de fer: lower skull with a ridge, wide flat brim.
    bm = kit.bm("head", "hat:chapel")
    _lathe(bm, [(0.0, 1.785), (0.075, 1.775), (0.122, 1.745), (0.143, 1.70), (0.148, 1.672),
                (0.228, 1.662), (0.225, 1.65), (0.142, 1.660)], 12, steel, cy=hy)
    add_tube(bm, [((0, hy - 0.14, 1.70), 0.008, 0.008), ((0, hy - 0.08, 1.775), 0.01, 0.01),
                  ((0, hy + 0.06, 1.78), 0.01, 0.01), ((0, hy + 0.14, 1.70), 0.008, 0.008)], segs=4, mat_idx=steel)
    # Bascinet: pointed skull, sides and back down over the ears.
    bm = kit.bm("head", "hat:bascinet")
    _lathe(bm, [(0.0, 1.875), (0.035, 1.845), (0.085, 1.79), (0.122, 1.73), (0.138, 1.675)],
           12, steel, cy=hy)
    add_ellipsoid(bm, (cx, hy, 1.62), (0.138, 0.148, 0.155), segs=12, rings=8, mat_idx=steel,
                  keep=lambda x, y, z: -0.62 < z < 0.4 and y > -0.3)
    # Cervelliere: close round skullcap with a riveted rim.
    bm = kit.bm("head", "hat:cervelliere")
    add_ellipsoid(bm, (cx, hy, cz + 0.035), (0.128, 0.14, 0.15), segs=12, rings=8, mat_idx=steel,
                  keep=lambda x, y, z: z > 0.12)
    add_tube(bm, [((0, hy, cz + 0.045), 0.13, 0.142), ((0, hy, cz + 0.07), 0.13, 0.142)], segs=12,
             mat_idx=ird, cap0=False, cap1=False)

    # Mail coif under the helmet (optional): face left open.
    kit.option("coif", "mail", 2, 0)
    kit.option("coif", "none", 3, 1)
    add_ellipsoid(kit.bm("head", "coif:mail"), (cx, cy + 0.01, cz + 0.008), (rx * 1.2, ry * 1.17, rz * 1.12),
                  segs=12, rings=8, mat_idx=mail, keep=lambda x, y, z: not (y < -0.42 and -0.72 < z < 0.55))

    # --- arms: steel spaulders or mail sleeves; leather gauntlets, some with vambraces ---
    kit.option("arms", "spaulders", 3, 0)
    kit.option("arms", "mail", 2, 0)
    kit.option("arms", "plain", 1, 1)
    kit.option("hands", "gauntlets", 3, 0)
    kit.option("hands", "vambraces", 2, 0)
    kit.option("hands", "bare", 1, 1)
    lt = kit.mat("leather_tan")
    for side, sx in (("arm_R", -1), ("arm_L", 1)):
        add_ellipsoid(kit.bm(side, "arms:spaulders"), (sx * 0.215, 0.0, 1.355), (0.085, 0.088, 0.075),
                      segs=8, rings=6, mat_idx=steel, keep=lambda x, y, z: z > -0.35)
        bm = kit.bm(side, "arms:mail")
        add_tube(bm, [((sx * 0.205, 0.0, 1.40), 0.07, 0.072), ((sx * 0.222, 0.006, 1.2), 0.064, 0.066),
                      ((sx * 0.226, 0.008, 1.15), 0.062, 0.064)], segs=8, mat_idx=mail)
        for opt in ("gauntlets", "vambraces"):
            bm = kit.bm(side, "hands:" + opt)
            add_ellipsoid(bm, (sx * 0.24, -0.065, 0.80), (0.036, 0.048, 0.064), segs=8, rings=5, mat_idx=lt)
            add_tube(bm, [((sx * 0.239, -0.052, 0.91), 0.052, 0.054), ((sx * 0.24, -0.06, 0.83), 0.045, 0.047)],
                     segs=8, mat_idx=lt)
        add_tube(kit.bm(side, "hands:vambraces"), [((sx * 0.236, -0.0, 1.07), 0.054, 0.056),
                                                   ((sx * 0.238, -0.04, 0.92), 0.05, 0.052)], segs=8, mat_idx=steel)

    # --- weapon in the right fist: halberd grounded beside the foot, or a crossbow ---
    kit.option("weapon", "halberd", 3, 0)
    kit.option("weapon", "crossbow", 1, 0)
    wa = kit.mat("wood_ash")
    hx, hyy = -0.24, -0.072
    bm = kit.bm("arm_R", "weapon:halberd")
    add_tube(bm, [((hx, hyy, 0.02), 0.006, 0.006), ((hx, hyy, 0.08), 0.017, 0.017)], segs=6, mat_idx=ird)
    add_tube(bm, [((hx, hyy, 0.08), 0.016, 0.016), ((hx, hyy, 1.93), 0.016, 0.016)], segs=6, mat_idx=wa)
    add_tube(bm, [((hx, hyy, 1.90), 0.02, 0.02), ((hx, hyy, 2.10), 0.018, 0.018),
                  ((hx, hyy, 2.38), 0.003, 0.003)], segs=4, mat_idx=steel, smooth=False)
    # Axe blade outward (-X), its edge a shallow crescent; back fluke toward the head.
    t = (0, 0.012, 0)
    _plate(bm, [(hx, hyy, 2.10), (hx, hyy, 2.05), (hx, hyy, 1.99), (hx, hyy, 1.93)],
           [(hx - 0.15, hyy, 2.17), (hx - 0.13, hyy, 2.07), (hx - 0.13, hyy, 1.96), (hx - 0.16, hyy, 1.86)],
           t, steel)
    _plate(bm, [(hx, hyy, 2.07), (hx, hyy, 2.02)], [(hx + 0.06, hyy, 2.03), (hx + 0.11, hyy, 1.95)], t, steel)

    bm = kit.bm("arm_R", "weapon:crossbow")
    hand = Vector((hx, -0.065, 0.80))
    d = Vector((0, -0.59, -0.81)).normalized()
    butt, front = hand - d * 0.16, hand + d * 0.42
    add_tube(bm, [(tuple(butt), 0.022, 0.03), (tuple(hand + d * 0.1), 0.02, 0.024), (tuple(front), 0.018, 0.02)],
             segs=6, mat_idx=kit.mat("wood_dark"))
    c = hand + d * 0.38
    back = -d
    tipL, tipR = c + Vector((0.26, 0, 0)) + back * 0.08, c + Vector((-0.26, 0, 0)) + back * 0.08
    add_tube(bm, [(tuple(tipL), 0.007, 0.007), (tuple(c + Vector((0.14, 0, 0)) + back * 0.02), 0.012, 0.012),
                  (tuple(c), 0.015, 0.015), (tuple(c + Vector((-0.14, 0, 0)) + back * 0.02), 0.012, 0.012),
                  (tuple(tipR), 0.007, 0.007)], segs=5, mat_idx=steel)
    add_tube(bm, [(tuple(tipL), 0.003, 0.003), (tuple(tipR), 0.003, 0.003)], segs=3, mat_idx=kit.mat("slot:linen"))
    add_tube(bm, [(tuple(front + Vector((0.045, 0, 0))), 0.006, 0.006), (tuple(front + d * 0.08), 0.007, 0.007),
                  (tuple(front + Vector((-0.045, 0, 0))), 0.006, 0.006)], segs=4, mat_idx=ird)
    # Bolt case behind the right hip, fletchings showing.
    bm = kit.bm("body", "weapon:crossbow")
    add_tube(bm, [((-0.12, 0.235, 0.74), 0.038, 0.032), ((-0.12, 0.215, 0.98), 0.042, 0.035)], segs=6, mat_idx=lt)
    add_ellipsoid(bm, (-0.12, 0.213, 1.0), (0.03, 0.026, 0.03), segs=6, rings=4, mat_idx=kit.mat("slot:linen"))

    # --- sword on the left hip, scabbard swept back behind the leg (optional) ---
    kit.option("sword", "yes", 3, 0)
    kit.option("sword", "no", 1, 1)
    bm = kit.bm("body", "sword:yes")
    p0 = Vector((0.182, 0.0, 0.93))
    sd = Vector((0.006, 0.42, -0.5)).normalized()
    add_tube(bm, [(tuple(p0), 0.02, 0.012), (tuple(p0 + sd * 0.62), 0.016, 0.01)], segs=6,
             mat_idx=kit.mat("leather_dark", "#2e2119", roughness=0.7))
    add_tube(bm, [(tuple(p0 + sd * 0.62), 0.016, 0.01), (tuple(p0 + sd * 0.68), 0.004, 0.004)], segs=4, mat_idx=steel)
    add_tube(bm, [(tuple(p0 - sd * 0.01), 0.012, 0.012), (tuple(p0 - sd * 0.12), 0.011, 0.011)], segs=5,
             mat_idx=kit.mat("leather_dark"))
    guard = Vector((0, sd.z, -sd.y)).normalized()   # across the blade, in the YZ plane
    add_tube(bm, [(tuple(p0 - sd * 0.015 - guard * 0.07), 0.008, 0.008),
                  (tuple(p0 - sd * 0.015 + guard * 0.07), 0.008, 0.008)], segs=4, mat_idx=steel)
    add_ellipsoid(bm, tuple(p0 - sd * 0.135), (0.02, 0.02, 0.02), segs=6, rings=4, mat_idx=steel)

    # Belt pouch on the right front hip (optional).
    kit.option("pouch", "yes", 1, 1)
    kit.option("pouch", "no", 1, 1)
    add_ellipsoid(kit.bm("body", "pouch:yes"), (-0.12, -0.185, 0.88), (0.045, 0.028, 0.055),
                  segs=8, rings=5, mat_idx=lt)
