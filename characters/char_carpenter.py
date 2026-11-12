# Kit: char_carpenter. Loaded by build_characters.py (load_kit_builders); runs with its globals.
# Also the fallback look for townsmen without a trade, so several options stay plain.

CANVAS = [["#b8a985", 3, "pab"], ["#a6976f", 3, "pab"], ["#c4b896", 2, "pabr"], ["#9a8a68", 2, "pa"]]
SMOCK = [["#7a5634", 3, "pab"], ["#6b5a40", 3, "pab"], ["#8a6e4a", 2, "pab"]] + UNDYED + DYED[:5]


def add_slab(bm, x, poly, t, mat_idx):
    """Flat prism in the YZ plane, centred on x, thickness t: poly = [(y, z), ...] convex, CCW seen from -X."""
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
    """Carpenter: canvas smock and apron, tool belt with mallet and square, broadaxe, block plane."""
    kit.anim = {"work": "hew"}
    kit_body(kit, tunic_slot="tunic", hose_slot="hose", shoe="boots", sleeves=("full", "rolled"), sleeve_w=(3, 2))
    kit.slot("tunic", SMOCK)
    kit.slot("hose", HOSE)
    kit.slot("boots", LEATHER + [["#5c4430", 2, "pab"]])
    kit.slot("apron", CANVAS)
    kit.slot("cap", [["#4b4a46", 3, "pab"], ["#5a4e3e", 2, "pab"], ["#3a2a1c", 1, "pab"], ["#4b5a6e", 1, "ab"]])
    kit.slot("hood", [["#5a4e3e", 2, "pab"], ["#4d4536", 1, "pab"], ["#6e2f28", 1, "ab"]])
    kit_heads(kit, {"hat:cap": (4, 0), "hat:bare": (3, 0), "hat:hood": (1, 0), "hat:coif": (1, 1),
                    "hat:kerchief": (0, 3), "hat:veil": (0, 2),
                    "hair:short": (4, 0), "hair:long": (2, 0), "hair:bald": (1, 0),
                    "beard:none": (2, 1), "beard:short": (3, 0), "beard:full": (2, 0), "beard:moustache": (1, 0)})

    # Canvas apron: bib for most men, waist for women, none for the plain townsmen.
    kit.option("apron", "bib", 3, 1)
    kit.option("apron", "waist", 1, 3)
    kit.option("apron", "none", 2, 2)
    kit_bib_apron(kit, "apron:bib", "apron", bottom=0.34)
    kit_bib_apron(kit, "apron:waist", "apron", bottom=0.38, waist_only=True)

    # Tool belt over the apron (men): heavy belt, mallet front-left, iron square front-right,
    # two pouches at the back.
    kit.option("toolbelt", "yes", 3, 0)
    kit.option("toolbelt", "no", 1, 1)
    bm = kit.bm("body", "toolbelt:yes+sex:m")
    lt, wa, wd, ir = kit.mat("leather_tan"), kit.mat("wood_ash"), kit.mat("wood_dark"), kit.mat("iron_steel")
    add_tube(bm, [((0, -0.012, 0.905), 0.188, 0.142), ((0, -0.012, 0.95), 0.186, 0.14)],
             segs=10, mat_idx=lt, cap0=False, cap1=False)
    add_tube(bm, [((0.115, -0.175, 0.905), 0.03, 0.026), ((0.115, -0.175, 0.83), 0.03, 0.026)], segs=6, mat_idx=wa)
    add_tube(bm, [((0.115, -0.175, 0.83), 0.01, 0.01), ((0.115, -0.18, 0.72), 0.01, 0.01)], segs=4, mat_idx=wa)
    add_box(bm, -0.105, -0.168, 0.85, 0.016, 0.008, 0.15, mat_idx=ir)    # square: long arm down
    add_box(bm, -0.135, -0.168, 0.781, 0.075, 0.008, 0.016, mat_idx=ir)  # short arm out
    for sx in (-1, 1):
        add_ellipsoid(bm, (sx * 0.11, 0.145, 0.87), (0.045, 0.03, 0.055), segs=8, rings=4, mat_idx=lt)

    # Broadaxe in the right fist (optional for the plain men): handle forward-down, bearded
    # blade off the lower side so it bites when the arm swings forward.
    kit.option("axe", "yes", 4, 0)
    kit.option("axe", "no", 2, 1)
    bm = kit.bm("arm_R", "axe:yes")
    a, b = Vector((-0.24, 0.0, 0.88)), Vector((-0.24, -0.265, 0.554))   # through the fist centre
    add_tube(bm, [(tuple(a), 0.014, 0.014), (tuple(b), 0.016, 0.016)], segs=6, mat_idx=wa)
    d = (b - a).normalized()
    p = Vector((0, -d.z, d.y))          # square to the handle, back-down when hanging
    if p.z > 0:
        p = -p
    for poly, t in ((((-0.05, -0.035), (0.04, -0.035), (0.04, 0.03), (-0.05, 0.03)), 0.034),        # eye
                    (((-0.035, 0.02), (0.04, 0.02), (0.095, 0.19), (-0.15, 0.2)), 0.018)):          # blade
        pts = [((b + d * u + p * v).y, (b + d * u + p * v).z) for u, v in poly]
        add_slab(bm, -0.24, pts, t, ir)

    # Block plane in the left fist (optional): body below the hand, tote in the grip.
    kit.option("plane", "yes", 2, 1)
    kit.option("plane", "no", 2, 3)
    bm = kit.bm("arm_L", "plane:yes")
    add_box(bm, 0.24, -0.085, 0.71, 0.055, 0.25, 0.065, mat_idx=wd)
    add_box(bm, 0.24, -0.06, 0.765, 0.018, 0.05, 0.05, mat_idx=wd)       # tote, inside the fist
    add_box(bm, 0.24, -0.15, 0.75, 0.034, 0.018, 0.03, mat_idx=ir)       # iron wedge
