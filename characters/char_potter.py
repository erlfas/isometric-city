# Kit: char_potter. Loaded by build_characters.py (load_kit_builders); runs with its globals.

def _splat(bm, c, u, v, r, mat, seed):
    """Irregular flat clay spatter: a 6-gon in the plane spanned by unit vectors u, v."""
    c, u, v = Vector(c), Vector(u), Vector(v)
    rs = [0.75, 1.0, 0.6, 0.95, 0.7, 0.9]
    k = seed % 6
    verts = []
    for j in range(6):
        a = j / 6 * math.tau
        rr = r * rs[(j + k) % 6]
        verts.append(bm.verts.new(c + u * (math.cos(a) * rr) + v * (math.sin(a) * rr * 0.8)))
    f = bm.faces.new(verts)      # wound so the normal faces -y (toward the viewer)
    if f.normal.y > 0:
        f.normal_flip()
    f.material_index = mat


def _apron_splats(bm, spots, sex, mats):
    """Spatter on the lower bib-apron panel (kit_bib_apron geometry), following its forward tilt."""
    wb, wt, yb, yt = {"m": (0.40, 0.30, -0.215, -0.135), "f": (0.42, 0.28, -0.205, -0.125)}[sex]
    bottom, top = 0.30, 0.99
    for i, (fx, z, r, mi) in enumerate(spots):
        t = (z - bottom) / (top - bottom)
        w = wb + (wt - wb) * t
        y = yb + (yt - yb) * t - 0.002
        slope = (yt - yb) / (top - bottom)
        v = Vector((0, slope, 1)).normalized()
        _splat(bm, (fx * w / 2, y, z), (1, 0, 0), tuple(v), r, mats[mi], i)


def _prism_yz(bm, x, pts, th, mat):
    """Flat plate: outline pts [(y, z)] in the YZ plane, thickness th along X."""
    a = [bm.verts.new(Vector((x - th / 2, y, z))) for y, z in pts]
    b = [bm.verts.new(Vector((x + th / 2, y, z))) for y, z in pts]
    faces = [bm.faces.new(list(reversed(a))), bm.faces.new(b)]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new([a[i], a[j], b[j], b[i]]))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    for f in faces:
        f.material_index = mat


def build(kit):
    """Potter: clay-spattered tunic and apron, cloth headband, wooden shaping rib, terracotta jug."""
    kit.anim = {"work": "shape_clay"}
    kit_body(kit, tunic_slot="tunic", hose_slot="hose", shoe="shoes", sleeves=("full", "rolled"), sleeve_w=(1, 3))
    # Greyish-green / undyed working linen and wool, like the turnaround.
    kit.slot("tunic", [["#7d7a62", 3, "pab"], ["#8a8470", 3, "pab"], ["#6e6a55", 2, "pab"]] + UNDYED[:3] + KIRTLE[:3])
    kit.slot("hose", [["#8a6a2e", 3, "pab"], ["#7c6434", 2, "pab"], ["#9a7a3a", 2, "pab"]] + HOSE[:2])
    kit.slot("apron", [["#6a4a32", 3, "pab"], ["#7a5a3e", 2, "pab"], ["#5a4634", 2, "pab"], ["#8a7a62", 1, "pab"]])
    kit.slot("band", [["#4b4a46", 3, "pab"], ["#6b5d45", 2, "pab"], ["#7a3a2c", 1, "ab"], ["#4b5a6e", 1, "ab"],
                      ["#8a6a2e", 1, "ab"]])
    kit.slot("cap", [["#4a3d2e", 1, "pab"]])
    kit.slot("hood", [["#4d4536", 1, "pab"]])
    kit_heads(kit, {"hat:coif": (1, 0), "hat:bare": (1, 0), "hat:kerchief": (0, 3), "hat:veil": (0, 1),
                    "hair:short": (6, 0), "hair:long": (1, 3), "hair:bald": (1, 0),
                    "beard:none": (1, 1), "beard:short": (3, 0), "beard:full": (2, 0), "beard:moustache": (1, 0)})

    clay_r = kit.mat("clay_red", "#9c5434", roughness=0.95)
    clay_g = kit.mat("clay_grey", "#8f8c84", roughness=0.95)
    terra = kit.mat("terracotta", "#b35a32", roughness=0.7)
    terra_d = kit.mat("terracotta_dark", "#8a4024", roughness=0.75)
    band = kit.mat("slot:band")
    hair = kit.mat("slot:hair")
    cx, cy, cz = HEAD_C

    # Cloth headband (the trade's head signature) tied at the back; sits on top of long hair.
    kit.option("hat", "band", 4, 4)
    bm = kit.bm("head", "hat:band")
    add_tube(bm, [((0, 0.008, 1.668), 0.101, 0.114), ((0, 0.008, 1.706), 0.088, 0.100)],
             segs=12, mat_idx=band, cap0=False, cap1=False)
    add_ellipsoid(bm, (0, 0.122, 1.686), (0.024, 0.016, 0.018), segs=6, rings=4, mat_idx=band)
    for sx in (-1, 1):
        add_tube(bm, [((sx * 0.008, 0.128, 1.68), 0.012, 0.005), ((sx * 0.03, 0.14, 1.61), 0.014, 0.005)],
                 segs=4, mat_idx=band)
    # Women only: hair gathered in a bun at the nape (with band or kerchief it shows behind).
    kit.option("hair", "bun", 0, 2)
    bm = kit.bm("head", "hair:bun")
    add_ellipsoid(bm, (cx, cy + 0.006, cz + 0.008), (HEAD_R[0] * 1.07, HEAD_R[1] * 1.06, HEAD_R[2] * 1.04),
                  segs=12, rings=8, mat_idx=hair,
                  keep=lambda x, y, z: z > 0.32 or (y > -0.25 and z > -0.35) or (y > 0.2 and z > -0.6))
    add_ellipsoid(bm, (0, 0.13, 1.56), (0.05, 0.035, 0.042), segs=8, rings=5, mat_idx=hair)

    # Clay-stained bib apron for everyone, with one of two spatter patterns.
    kit.option("apron", "bib", 1, 1)
    kit_bib_apron(kit, "apron:bib", "apron")
    kit.option("clay", "a", 1, 1)
    kit.option("clay", "b", 1, 1)
    mats = (clay_r, clay_g)
    patterns = {
        "a": [(-0.5, 0.82, 0.03, 0), (0.35, 0.66, 0.04, 1), (-0.2, 0.48, 0.035, 0), (0.6, 0.40, 0.028, 0),
              (0.05, 0.90, 0.022, 1), (-0.65, 0.58, 0.03, 1), (0.25, 0.86, 0.026, 0)],
        "b": [(0.45, 0.80, 0.035, 0), (-0.35, 0.70, 0.04, 1), (0.1, 0.55, 0.03, 0), (-0.55, 0.42, 0.03, 0),
              (0.6, 0.52, 0.026, 1), (-0.1, 0.36, 0.028, 1), (-0.05, 0.92, 0.024, 0)],
    }
    for pat, spots in patterns.items():
        for sex in ("m", "f"):
            _apron_splats(kit.bm("body", f"clay:{pat}+sex:{sex}"), spots, sex, mats)
    # Slip on the sleeves (both arms, base): grey and red smears on the upper sleeve front.
    for side, sx in (("arm_R", -1), ("arm_L", 1)):
        bm = kit.bm(side)
        _splat(bm, (sx * 0.222, -0.062, 1.24), (1, 0, 0), (0, 0, 1), 0.024, clay_g, 1 if sx < 0 else 3)
        _splat(bm, (sx * 0.214, -0.064, 1.31), (1, 0, 0), (0, 0, 1), 0.016, clay_r, 2)

    # Wooden shaping rib in the right fist: a flat rounded-triangle plate pointing forward-down.
    bm = kit.bm("arm_R")
    rib = [(-0.06, 0.81), (-0.14, 0.80), (-0.225, 0.76), (-0.255, 0.71), (-0.225, 0.655),
           (-0.16, 0.64), (-0.095, 0.67), (-0.055, 0.74)]
    _prism_yz(bm, -0.24, rib, 0.016, kit.mat("wood_pale", "#b08a5c", roughness=0.8))

    # Terracotta vessel in the left hand, gripped by its handle: tall jug or squat pot.
    kit.option("vessel", "jug", 3, 3)
    kit.option("vessel", "pot", 2, 2)
    x = 0.24
    bm = kit.bm("arm_L", "vessel:jug")
    add_tube(bm, [((x, -0.165, 0.60), 0.045, 0.045), ((x, -0.165, 0.64), 0.066, 0.066),
                  ((x, -0.165, 0.71), 0.07, 0.07), ((x, -0.165, 0.78), 0.045, 0.045),
                  ((x, -0.165, 0.82), 0.032, 0.032), ((x, -0.168, 0.855), 0.042, 0.04)], segs=10, mat_idx=terra)
    add_tube(bm, [((x, -0.165, 0.857), 0.034, 0.032), ((x, -0.165, 0.84), 0.026, 0.026)],
             segs=10, mat_idx=terra_d, cap0=False)       # dark mouth
    add_tube(bm, [((x, -0.13, 0.82), 0.011, 0.007), ((x, -0.085, 0.81), 0.011, 0.007),
                  ((x, -0.085, 0.72), 0.011, 0.007), ((x, -0.11, 0.69), 0.011, 0.007)], segs=5, mat_idx=terra)
    bm = kit.bm("arm_L", "vessel:pot")
    add_tube(bm, [((x, -0.17, 0.62), 0.05, 0.05), ((x, -0.17, 0.66), 0.08, 0.08),
                  ((x, -0.17, 0.72), 0.078, 0.078), ((x, -0.17, 0.76), 0.055, 0.055),
                  ((x, -0.17, 0.785), 0.06, 0.06)], segs=10, mat_idx=terra)
    add_tube(bm, [((x, -0.17, 0.787), 0.05, 0.05), ((x, -0.17, 0.77), 0.042, 0.042)],
             segs=10, mat_idx=terra_d, cap0=False)
    add_tube(bm, [((x, -0.12, 0.775), 0.011, 0.007), ((x, -0.08, 0.79), 0.011, 0.007),
                  ((x, -0.08, 0.73), 0.011, 0.007), ((x, -0.105, 0.70), 0.011, 0.007)], segs=5, mat_idx=terra)
