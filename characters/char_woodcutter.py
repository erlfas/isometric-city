# Kit: char_woodcutter. Loaded by build_characters.py (load_kit_builders); runs with its globals.
# All woodcutters are men (plebeian sawyers at the Kraków-suburb logging yards).

WOOL_GREY = [["#6e6c66", 3, "pa"], ["#7c776c", 3, "pa"], ["#5c5a54", 2, "pa"], ["#857c6a", 2, "pa"]]
COWL = [["#3a3129", 3, "pa"], ["#2f2c28", 2, "pa"], ["#4a3f30", 2, "pa"], ["#3d4234", 1, "pa"]]
TROUSERS = [["#4a4636", 3, "pa"], ["#3f3a30", 3, "pa"], ["#55493a", 2, "pa"], ["#3b3f3a", 1, "pa"]]
BOOTS = [["#4a3624", 3, "pa"], ["#3a2a1c", 3, "pa"], ["#56402a", 2, "pa"]]
WRAPS = [["#8a7f6a", 3, "pa"], ["#6f6552", 3, "pa"], ["#9b8f76", 1, "pa"]]


def add_slab(bm, x, poly, t, mat_idx):
    """Flat prism in the YZ plane, centred on x, thickness t: poly = [(y, z), ...] convex."""
    front = [bm.verts.new(Vector((x - t / 2, y, z))) for y, z in poly]
    back = [bm.verts.new(Vector((x + t / 2, y, z))) for y, z in poly]
    faces = [bm.faces.new(front), bm.faces.new(list(reversed(back)))]
    n = len(poly)
    for i in range(n):
        k = (i + 1) % n
        faces.append(bm.faces.new([front[k], front[i], back[i], back[k]]))
    for f in faces:
        f.material_index = mat_idx
        f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=faces)


def build(kit):
    """Woodcutter: dark hooded cowl, grey wool tunic, tall boots or wrapped legs, broad
    felling axe in the right fist, iron wedges at the belt; some carry a log."""
    kit.anim = {"work": "chop"}
    kit_body(kit, tunic_slot="tunic", hose_slot="hose", shoe="none", sleeves=("full", "rolled"), sleeve_w=(1, 2))
    kit.slot("tunic", WOOL_GREY + UNDYED[:3])
    kit.slot("hose", TROUSERS)
    kit.slot("boots", BOOTS)
    kit.slot("wraps", WRAPS)
    kit.slot("hood", COWL)
    kit.slot("cap", [["#3a2a1c", 2, "pa"], ["#4b4a46", 2, "pa"], ["#5a4e3e", 1, "pa"]])

    # Heads: the dark cowl is the signature; some wear it pushed back, some a felt cap.
    kit_heads(kit, {"hat:hood": (5, 0), "hat:cap": (2, 0), "hat:bare": (1, 0),
                    "hair:short": (4, 0), "hair:long": (2, 0), "hair:bald": (1, 0),
                    "beard:none": (1, 1), "beard:short": (3, 0), "beard:full": (4, 0), "beard:moustache": (1, 0)})
    # Cowl pushed back: shoulder cape with the empty hood bunched behind the neck.
    kit.option("hat", "cowl", 3, 0)
    bm = kit.bm("head", "hat:cowl")
    hd = kit.mat("slot:hood")
    add_tube(bm, [((0, 0.075, 1.50), 0.075, 0.03), ((0, 0.125, 1.56), 0.085, 0.045),
                  ((0, 0.14, 1.63), 0.06, 0.04)], segs=8, mat_idx=hd)
    bm = kit.bm("body", "hat:cowl")
    add_tube(bm, [((0, 0.01, 1.30), 0.265, 0.195), ((0, 0.01, 1.40), 0.2, 0.15), ((0, 0.01, 1.47), 0.105, 0.098)],
             segs=10, mat_idx=hd, cap1=False)

    # Leather gloves (optional): thick mitten + cuff over each hand.
    kit.option("gloves", "yes", 2, 0)
    kit.option("gloves", "no", 3, 1)
    lt = kit.mat("leather_tan")
    for side, sx in (("arm_R", -1), ("arm_L", 1)):
        bm = kit.bm(side, "gloves:yes")
        add_ellipsoid(bm, (sx * 0.24, -0.065, 0.80), (0.036, 0.048, 0.064), segs=8, rings=5, mat_idx=lt)
        add_tube(bm, [((sx * 0.239, -0.055, 0.90), 0.05, 0.052), ((sx * 0.24, -0.06, 0.83), 0.045, 0.047)],
                 segs=8, mat_idx=lt)

    # Belt gear (signature): leather frog front-left holding two iron felling wedges.
    bm = kit.bm("body", "sex:m")
    ir = kit.mat("iron_dark")
    st = kit.mat("iron_steel")
    add_box(bm, 0.135, -0.118, 0.925, 0.085, 0.014, 0.075, mat_idx=lt)
    for x, y, z in ((0.115, -0.125, 0.835), (0.155, -0.108, 0.845)):
        add_tapered_box(bm, x, y, z, 0.034, 0.006, 0.04, 0.032, 0.13, mat_idx=st)
    # Pouch (optional) on the left hip.
    kit.option("pouch", "yes", 2, 0)
    kit.option("pouch", "no", 1, 1)
    add_ellipsoid(kit.bm("body", "pouch:yes+sex:m"), (0.175, -0.01, 0.875), (0.035, 0.05, 0.065), segs=8, rings=5,
                  mat_idx=lt)

    # Legs: tall boots with a turned-down cuff, or wool wraps over turnshoes.
    kit.option("legs", "boots", 3, 1)
    kit.option("legs", "wraps", 2, 1)
    bt, wr = kit.mat("slot:boots"), kit.mat("slot:wraps")
    rope = kit.mat("binding", "#a08a62", roughness=0.9)
    for side, sx in (("leg_R", -1), ("leg_L", 1)):
        x = sx * 0.095
        bm = kit.bm(side, "legs:boots")
        add_tube(bm, [((x, 0.0, 0.03), 0.062, 0.064), ((x, -0.005, 0.30), 0.064, 0.066),
                      ((x, -0.008, 0.44), 0.066, 0.068)], segs=8, mat_idx=bt)
        add_tube(bm, [((x, -0.008, 0.40), 0.075, 0.077), ((x, -0.01, 0.50), 0.074, 0.076)], segs=8, mat_idx=bt)
        add_tube(bm, [((x, 0.06, 0.06), 0.054, 0.064), ((x, -0.06, 0.055), 0.058, 0.058),
                      ((x, -0.175, 0.035), 0.044, 0.035)], segs=8, mat_idx=bt)
        bm = kit.bm(side, "legs:wraps")
        add_tube(bm, [((x, -0.01, 0.47), 0.063, 0.065), ((x, -0.005, 0.30), 0.055, 0.057),
                      ((x, 0.0, 0.10), 0.047, 0.049)], segs=8, mat_idx=wr)
        for z in (0.18, 0.28, 0.38):
            w = 0.052 + 0.03 * (z - 0.1)
            add_tube(bm, [((x, -0.005, z - 0.015), w + 0.005, w + 0.007), ((x, -0.005, z + 0.015), w + 0.005, w + 0.007)],
                     segs=8, mat_idx=rope, cap0=False, cap1=False)
        add_tube(bm, [((x, 0.055, 0.06), 0.048, 0.06), ((x, -0.06, 0.055), 0.054, 0.055),
                      ((x, -0.165, 0.035), 0.04, 0.032)], segs=8, mat_idx=lt)

    # Broad felling axe in the right fist: haft forward-down through the fist, head at the
    # far end, broad blade on the back-down side so it leads the overhead chop.
    bm = kit.bm("arm_R")
    wa, edge = kit.mat("wood_ash"), kit.mat("edge", "#d4d6d8", roughness=0.35, metallic=0.25)
    hand = Vector((-0.24, -0.065, 0.80))
    al = 0.62
    d = Vector((0, -math.sin(al), -math.cos(al)))
    p = Vector((0, math.cos(al), -math.sin(al)))          # back-down, square to the haft
    butt, head = hand - d * 0.13, hand + d * 0.6
    add_tube(bm, [(tuple(butt), 0.017, 0.017), (tuple(hand), 0.016, 0.016), (tuple(head + d * 0.03), 0.018, 0.018)],
             segs=6, mat_idx=wa)
    for poly, t, m in ((((-0.055, -0.045), (0.035, -0.045), (0.035, 0.035), (-0.055, 0.035)), 0.04, ir),   # eye + poll
                       (((-0.04, 0.03), (0.03, 0.03), (0.1, 0.2), (-0.13, 0.2)), 0.02, st),                # cheeks
                       (((-0.13, 0.195), (0.1, 0.195), (0.11, 0.215), (-0.145, 0.215)), 0.012, edge)):       # bright edge
        pts = [((head + d * u + p * v).y, (head + d * u + p * v).z) for u, v in poly]
        add_slab(bm, -0.24, pts, t, m)

    # Log across the shoulders behind the neck (optional): the arms rise in front of it.
    kit.option("log", "yes", 1, 0)
    kit.option("log", "no", 3, 1)
    bm = kit.bm("body", "log:yes+sex:m")
    bark, wood = kit.mat("bark", "#4a3b2c", roughness=0.95), kit.mat("log_end", "#b89a6a", roughness=0.85)
    a, b = Vector((-0.55, 0.17, 1.44)), Vector((0.55, 0.17, 1.50))
    add_tube(bm, [(tuple(a), 0.07, 0.07), (tuple(b), 0.064, 0.064)], segs=8, mat_idx=bark, cap0=False, cap1=False)
    add_tube(bm, [(tuple(a + (a - b).normalized() * 0.004), 0.066, 0.066), (tuple(a), 0.066, 0.066)],
             segs=8, mat_idx=wood, cap1=False)
    add_tube(bm, [(tuple(b), 0.06, 0.06), (tuple(b + (b - a).normalized() * 0.004), 0.06, 0.06)],
             segs=8, mat_idx=wood, cap0=False)
