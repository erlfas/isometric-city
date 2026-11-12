# Kit: char_farmer. Loaded by build_characters.py (load_kit_builders); runs with its globals.

STRAW = [["#c9a75e", 3, "pabr"], ["#b8954d", 3, "pabr"], ["#d6bb78", 2, "pabr"], ["#a2834a", 2, "pabr"]]
ROPE = [["#9c8455", 3, "pabr"], ["#86704a", 2, "pabr"], ["#b09a68", 1, "pabr"]]
BREECHES = [["#5d4a36", 3, "pa"], ["#6b5a40", 3, "pa"], ["#4f4a3e", 2, "pa"], ["#73603f", 2, "pa"],
            ["#5a5446", 2, "pa"]]
PUTTEE = [["#8a7f6a", 3, "pa"], ["#b9ad92", 2, "pa"], ["#6f6552", 2, "pa"], ["#5e5446", 1, "pa"]]


def _straw_hat(kit, variant, crown, brim_r, droop):
    """Straw hat on the head part: crown shape + a lens brim bent down toward its edge."""
    bm = kit.bm("head", variant)
    m = kit.mat("slot:straw")
    cy = 0.012
    if crown == "dome":
        add_ellipsoid(bm, (0, cy, 1.715), (0.125, 0.132, 0.095), segs=12, rings=6, mat_idx=m,
                      keep=lambda x, y, z: z > -0.05)
    elif crown == "peak":
        add_tube(bm, [((0, cy, 1.705), 0.122, 0.13), ((0, cy, 1.78), 0.095, 0.1), ((0, cy + 0.005, 1.875), 0.014, 0.014)],
                 segs=10, mat_idx=m, cap0=False)
    else:  # flat-topped
        add_tube(bm, [((0, cy, 1.705), 0.123, 0.13), ((0, cy, 1.805), 0.112, 0.118), ((0, cy, 1.82), 0.1, 0.106)],
                 segs=10, mat_idx=m, cap0=False)
    faces = add_ellipsoid(bm, (0, cy, 1.705), (brim_r, brim_r, 0.016), segs=14, rings=4, mat_idx=m)
    for v in {v for f in faces for v in f.verts}:
        d = math.hypot(v.co.x, v.co.y - cy) / brim_r
        v.co.z -= droop * d * d


def build(kit):
    """Peasant farmer: straw hat, loose linen shirt, rope belt, scythe / hoe / flail."""
    kit.anim = {"work": "farm_chop"}
    kit_body(kit, tunic_slot="shirt", hose_slot="breeches", shoe="shoes", sleeves=("full", "rolled"),
             sleeve_w=(1, 3), male_hem=0.70)
    kit.slot("shirt", LINEN + [["#bfb39a", 3, "pa"], ["#a99f88", 2, "pa"]] + UNDYED[:2])
    kit.slot("breeches", BREECHES)
    kit.slot("belt", ROPE)
    kit.slot("straw", STRAW)
    kit.slot("puttee", PUTTEE)
    kit.slot("shoes", [["#6b4a2e", 3, "pa"], ["#5a3e26", 2, "pa"], ["#7a5a3a", 2, "pa"]])  # undyed turnshoes

    # Hair and beards (all men). Hats are local: every farmer wears straw.
    kit_heads(kit, {"hair:short": (4, 0), "hair:long": (2, 0), "hair:bald": (1, 0),
                    "beard:none": (1, 1), "beard:short": (3, 0), "beard:full": (3, 0), "beard:moustache": (1, 0)})
    kit.option("hat", "wide", 3, 1)
    kit.option("hat", "peak", 2, 1)
    kit.option("hat", "flat", 2, 1)
    _straw_hat(kit, "hat:wide", "dome", 0.25, 0.04)
    _straw_hat(kit, "hat:peak", "peak", 0.23, 0.03)
    _straw_hat(kit, "hat:flat", "flat", 0.22, 0.012)

    # Rope belt: knot at the front with two hanging ends (belt ring itself is kit_body's).
    bm = kit.bm("body")
    rope = kit.mat("slot:belt")
    add_ellipsoid(bm, (0.02, -0.125, 0.972), (0.026, 0.018, 0.022), segs=6, rings=4, mat_idx=rope)
    add_tube(bm, [((0.015, -0.135, 0.965), 0.009, 0.009), ((0.005, -0.15, 0.86), 0.008, 0.008),
                  ((0.0, -0.155, 0.80), 0.007, 0.007)], segs=4, mat_idx=rope)
    add_tube(bm, [((0.035, -0.13, 0.965), 0.009, 0.009), ((0.045, -0.15, 0.88), 0.008, 0.008)],
             segs=4, mat_idx=rope)
    # Whetstone horn hanging from the belt at the right back hip.
    add_tube(bm, [((-0.15, 0.1, 0.96), 0.03, 0.03), ((-0.17, 0.12, 0.84), 0.022, 0.022),
                  ((-0.175, 0.125, 0.78), 0.008, 0.008)], segs=6, mat_idx=kit.mat("horn", "#3d3328", roughness=0.6))
    # Leather pouch on the left hip (optional).
    kit.option("pouch", "yes", 2, 2)
    kit.option("pouch", "no", 1, 1)
    add_ellipsoid(kit.bm("body", "pouch:yes"), (0.175, -0.07, 0.88), (0.035, 0.05, 0.065), segs=8, rings=5,
                  mat_idx=kit.mat("leather_tan"))

    # Legs: kit_body's hose replaced by loose breeches (rolled at the knee), shins bare or
    # wrapped in puttees, or long trousers; turnshoes tied at the ankle.
    br, sk, pt, sh = kit.mat("slot:breeches"), kit.mat("slot:skin"), kit.mat("slot:puttee"), kit.mat("slot:shoes")
    kit.option("legs", "bare", 3, 3)
    kit.option("legs", "puttees", 3, 3)
    kit.option("legs", "long", 2, 2)
    for side, sx in (("leg_R", -1), ("leg_L", 1)):
        x = sx * 0.095
        bm = kit.bm(side)
        bm.clear()
        add_tube(bm, [((x, 0, 0.93), 0.085, 0.085), ((x, -0.01, 0.62), 0.07, 0.072), ((x, -0.012, 0.45), 0.066, 0.068)],
                 segs=8, mat_idx=br, cap1=False)
        add_tube(bm, [((x, 0.055, 0.06), 0.048, 0.06), ((x, -0.06, 0.055), 0.054, 0.055),
                      ((x, -0.165, 0.035), 0.04, 0.032)], segs=8, mat_idx=sh)
        add_tube(bm, [((x, 0.0, 0.115), 0.047, 0.049), ((x, 0.0, 0.095), 0.047, 0.049)], segs=8, mat_idx=sh)  # ankle tie
        # bare: breeches rolled below the knee, bare shin
        vb = kit.bm(side, "legs:bare")
        add_tube(vb, [((x, -0.012, 0.46), 0.074, 0.076), ((x, -0.01, 0.39), 0.072, 0.074)], segs=8, mat_idx=br)
        add_tube(vb, [((x, -0.01, 0.42), 0.05, 0.052), ((x, 0.0, 0.10), 0.04, 0.042)], segs=8, mat_idx=sk)
        # puttees: cloth bands wound from ankle to knee over the breeches' end
        vb = kit.bm(side, "legs:puttees")
        add_tube(vb, [((x, -0.012, 0.47), 0.064, 0.066), ((x, -0.006, 0.30), 0.055, 0.057),
                      ((x, 0.0, 0.10), 0.047, 0.049)], segs=8, mat_idx=pt)
        for z in (0.17, 0.25, 0.33, 0.41):
            w = 0.051 + 0.03 * (z - 0.1)
            add_tube(vb, [((x, -0.005, z - 0.02), w + 0.006, w + 0.008), ((x, -0.005, z + 0.02), w + 0.006, w + 0.008)],
                     segs=8, mat_idx=pt, cap0=False, cap1=False)
        add_tube(vb, [((x, -0.012, 0.47), 0.012, 0.006), ((x, -0.075, 0.44), 0.01, 0.006)], segs=4, mat_idx=rope)
        # long: trousers to the ankle, rolled at mid-calf
        vb = kit.bm(side, "legs:long")
        add_tube(vb, [((x, -0.012, 0.46), 0.066, 0.068), ((x, -0.005, 0.24), 0.062, 0.064)], segs=8, mat_idx=br)
        add_tube(vb, [((x, -0.005, 0.27), 0.07, 0.072), ((x, -0.003, 0.20), 0.07, 0.072)], segs=8, mat_idx=br)
        add_tube(vb, [((x, -0.004, 0.22), 0.045, 0.047), ((x, 0.0, 0.10), 0.04, 0.042)], segs=8, mat_idx=sk)

    # Tools in the right fist (hand at -0.24, -0.065, 0.80). The shaft stands nearly
    # upright with the working end at the foot, so pitching the arm forward lifts the
    # head out in front and the hoe loop chops it back down.
    wa, wd, st = kit.mat("wood_ash"), kit.mat("wood_dark"), kit.mat("iron_steel")
    kit.option("tool", "scythe", 3, 3)
    kit.option("tool", "hoe", 3, 3)
    kit.option("tool", "flail", 2, 2)
    top, hand, foot = Vector((-0.245, -0.17, 1.62)), Vector((-0.24, -0.068, 0.80)), Vector((-0.29, 0.03, 0.1))

    bm = kit.bm("arm_R", "tool:hoe")
    add_tube(bm, [(tuple(top), 0.017, 0.017), (tuple(hand), 0.018, 0.018), (tuple(foot), 0.019, 0.019)],
             segs=6, mat_idx=wa)
    add_tube(bm, [((-0.29, 0.03, 0.13), 0.026, 0.026), ((-0.29, 0.005, 0.085), 0.024, 0.024)], segs=6, mat_idx=wd)  # socket
    add_tube(bm, [((-0.29, 0.0, 0.1), 0.05, 0.008), ((-0.29, -0.07, 0.06), 0.056, 0.006),
                  ((-0.29, -0.12, 0.035), 0.06, 0.004)], segs=4, mat_idx=kit.mat("iron_dark"), smooth=False)

    bm = kit.bm("arm_R", "tool:scythe")
    add_tube(bm, [((-0.25, -0.12, 1.66), 0.017, 0.017), ((-0.24, -0.068, 1.2), 0.018, 0.018),
                  (tuple(hand), 0.018, 0.018), ((-0.27, -0.02, 0.45), 0.019, 0.019), (tuple(foot), 0.02, 0.02)],
             segs=6, mat_idx=wa)
    add_tube(bm, [((-0.245, -0.09, 1.24), 0.012, 0.012), ((-0.245, -0.18, 1.22), 0.012, 0.012)], segs=4, mat_idx=wa)  # upper nib
    add_tube(bm, [((-0.29, 0.03, 0.1), 0.026, 0.02), ((-0.33, -0.02, 0.105), 0.044, 0.006),
                  ((-0.42, -0.12, 0.14), 0.046, 0.005), ((-0.5, -0.26, 0.2), 0.036, 0.004),
                  ((-0.52, -0.4, 0.28), 0.01, 0.003)], segs=4, mat_idx=st, smooth=False)

    bm = kit.bm("arm_R", "tool:flail")
    hinge = Vector((-0.27, -0.01, 0.42))
    add_tube(bm, [((-0.245, -0.16, 1.35), 0.017, 0.017), (tuple(hand), 0.018, 0.018), (tuple(hinge), 0.019, 0.019)],
             segs=6, mat_idx=wa)
    add_tube(bm, [(tuple(hinge + Vector((0, 0, 0.02))), 0.024, 0.024), (tuple(hinge - Vector((0, 0, 0.03))), 0.024, 0.024)],
             segs=6, mat_idx=kit.mat("leather_tan"))  # leather hinge
    add_tube(bm, [((-0.275, -0.03, 0.39), 0.028, 0.028), ((-0.29, -0.15, 0.08), 0.032, 0.032)],
             segs=6, mat_idx=wd)  # swingle
