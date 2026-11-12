# Kit: char_townswoman. Loaded by build_characters.py (load_kit_builders); runs with its globals.

WICKER = [["#a07a45", 3, "pabr"], ["#8c6a3c", 2, "pabr"], ["#b58d58", 2, "pabr"]]


def _townswoman_headrail(kit, key, weight):
    """Linen headrail over the hair with a dyed fillet band; open face, drape to the shoulders."""
    kit.option("hat", key[4:], 0, weight)
    bm = kit.bm("head", key)
    m, band = kit.mat("slot:linen"), kit.mat("slot:fillet")
    cx, cy, cz = HEAD_C
    rx, ry, rz = HEAD_R
    add_ellipsoid(bm, (cx, cy + 0.014, cz + 0.014), (rx * 1.17, ry * 1.15, rz * 1.11), segs=12, rings=8,
                  mat_idx=m, keep=lambda x, y, z: z > -0.45 and not (y < -0.3 and z < 0.55))
    add_tube(bm, [((0, 0.07, 1.56), 0.115, 0.06), ((0, 0.1, 1.45), 0.15, 0.06), ((0, 0.115, 1.34), 0.18, 0.05)],
             segs=8, mat_idx=m)
    add_tube(bm, [((0, cy + 0.008, cz + 0.05), rx * 1.2, ry * 1.18), ((0, cy + 0.008, cz + 0.075), rx * 1.2, ry * 1.18)],
             segs=12, mat_idx=band, cap0=False, cap1=False)
    add_fringe(bm, kit.mat("slot:hair"))


def _arc(c, rx, ry, z, a0, a1, n):
    return [(c[0] + rx * math.cos(a0 + (a1 - a0) * i / n), c[1] + ry * math.sin(a0 + (a1 - a0) * i / n), z)
            for i in range(n + 1)]


def _basket(kit, bm, c=(0.315, -0.065)):
    """Wicker basket hung from the left fist, pushed outboard so it clears the skirt."""
    wk = kit.mat("slot:wicker")
    x, y = c
    add_tube(bm, [((x, y, 0.53), 0.07, 0.06), ((x, y, 0.60), 0.092, 0.075), ((x, y, 0.675), 0.102, 0.084)],
             segs=10, mat_idx=wk, cap1=False)
    add_tube(bm, [((x, y, 0.668), 0.104, 0.086), ((x, y, 0.688), 0.104, 0.086)], segs=10, mat_idx=wk)  # rim
    # Handle arcs from the inner rim, over the fist, down to the outer rim.
    add_tube(bm, [((x - 0.095, y, 0.68), 0.008, 0.008), ((0.235, -0.065, 0.78), 0.008, 0.008),
                  ((0.27, -0.065, 0.835), 0.008, 0.008), ((x + 0.06, y, 0.80), 0.008, 0.008),
                  ((x + 0.095, y, 0.69), 0.008, 0.008)], segs=5, mat_idx=wk)


def build(kit):
    """Burgher townswoman: long kirtle, white apron, keys at the belt, market basket."""
    kit.anim = {"work": "gossip"}
    kit_body(kit, tunic_slot="kirtle", hose_slot="hose", shoe="shoes", sleeves=("full",), sleeve_w=(1,))
    kit.slot("kirtle", [["#3f6a35", 4, "pab"], ["#4d5f2e", 3, "pab"], ["#2f5a3e", 2, "abr"]] + KIRTLE)
    kit.slot("hose", HOSE)
    kit.slot("apron", LINEN[:2] + [["#efe9dc", 3, "abr"]])
    kit.slot("fillet", DYED)
    kit.slot("wicker", WICKER)
    kit.slot("cloth", KERCHIEF)
    kit.slot("pouch", LEATHER + [["#6e2f28", 1, "br"]])
    kit.slot("hood", [["#4d4536", 2, "pab"], ["#5c3a30", 1, "ab"], ["#3e4a5a", 1, "abr"]])
    kit_heads(kit, {"hat:veil": (0, 5), "hat:kerchief": (0, 2), "hat:hood": (0, 1)})
    # Dyed kerchiefs only: a pale one over the fringe reads as white hair.
    kit.slot("kerchief", [["#a86656", 2, "pab"], ["#7e8ea3", 2, "abr"], ["#b8963f", 2, "pab"], ["#8c2f2a", 1, "br"], ["#5f6b3a", 1, "pab"]])
    _townswoman_headrail(kit, "hat:headrail", 3)
    lin = kit.mat("slot:linen")

    # Linen cuffs of the chemise at both wrists.
    for side, sx in (("arm_R", -1), ("arm_L", 1)):
        el, wr = Vector((sx * 0.232, 0.01, 1.11)), Vector((sx * 0.238, -0.05, 0.86))
        add_tube(kit.bm(side), [(tuple(el.lerp(wr, 0.86)), 0.05, 0.052), (tuple(el.lerp(wr, 1.0)), 0.049, 0.051)],
                 segs=8, mat_idx=lin)

    # White apron tied at the waist: long (to the shin) or short, tilted so the legs clear it.
    ap = kit.mat("slot:apron")
    kit.option("apron", "long", 0, 3)
    kit.option("apron", "short", 0, 2)
    add_panel(kit.bm("body", "apron:long"), 0.17, 0.99, 0.40, 0.29, -0.236, -0.125, 0.018, ap)
    add_panel(kit.bm("body", "apron:short"), 0.42, 0.99, 0.37, 0.29, -0.2, -0.125, 0.018, ap)

    bm = kit.bm("body")
    ir = kit.mat("iron_dark")
    # Key ring: hook from the belt, iron ring, three keys hanging over the apron.
    add_tube(bm, [((-0.1, -0.115, 0.975), 0.006, 0.006), ((-0.11, -0.165, 0.93), 0.006, 0.006)], segs=4, mat_idx=ir)
    kc = Vector((-0.11, -0.172, 0.895))
    ring = [((kc.x + 0.026 * math.sin(a), kc.y, kc.z + 0.026 * math.cos(a)), 0.006, 0.006)
            for a in [i * math.tau / 8 for i in range(9)]]
    add_tube(bm, ring, segs=4, mat_idx=ir, cap0=False, cap1=False)
    for dx, ln in ((-0.025, 0.12), (0.0, 0.15), (0.022, 0.11)):
        top = (kc.x + dx, kc.y - 0.004, kc.z - 0.03)
        bot = (kc.x + dx * 1.3, kc.y - 0.006, kc.z - 0.03 - ln)
        add_tube(bm, [(top, 0.005, 0.005), (bot, 0.005, 0.005)], segs=4, mat_idx=ir, smooth=False)
        add_box(bm, bot[0] + 0.009, bot[1], bot[2] + 0.012, 0.016, 0.006, 0.022, mat_idx=ir)   # bit

    # Chemise hem showing under the kirtle (optional).
    kit.option("hem", "chemise", 0, 2)
    kit.option("hem", "none", 0, 1)
    add_tube(kit.bm("body", "hem:chemise"), [((0, 0.0, 0.065), 0.254, 0.224), ((0, 0.0, 0.115), 0.25, 0.22)],
             segs=10, mat_idx=lin)

    # Purse on the left hip (optional).
    kit.option("purse", "yes", 0, 1)
    kit.option("purse", "no", 0, 1)
    add_ellipsoid(kit.bm("body", "purse:yes"), (0.12, -0.172, 0.88), (0.03, 0.02, 0.045), segs=8, rings=5,
                  mat_idx=kit.mat("slot:pouch"))
    add_tube(kit.bm("body", "purse:yes"), [((0.115, -0.13, 0.975), 0.005, 0.005), ((0.12, -0.17, 0.925), 0.005, 0.005)],
             segs=4, mat_idx=kit.mat("slot:pouch"))

    # Carried goods in the left hand.
    kit.option("carry", "produce", 0, 4)
    kit.option("carry", "covered", 0, 2)
    kit.option("carry", "jug", 0, 2)
    kit.option("carry", "bundle", 0, 1)
    bread = kit.mat("bread", "#a8703a", roughness=0.85)
    bm = kit.bm("arm_L", "carry:produce")
    _basket(kit, bm)
    add_ellipsoid(bm, (0.295, -0.06, 0.69), (0.045, 0.075, 0.04), segs=8, rings=5, mat_idx=bread)   # loaf
    add_ellipsoid(bm, (0.36, -0.1, 0.69), (0.04, 0.04, 0.035), segs=8, rings=5,
                  mat_idx=kit.mat("cabbage", "#6f8e45", roughness=0.8))
    add_ellipsoid(bm, (0.355, -0.02, 0.685), (0.026, 0.026, 0.026), segs=6, rings=4,
                  mat_idx=kit.mat("turnip", "#d8c8c0", roughness=0.7))
    for dx, dy in ((0.0, 0.0), (0.02, 0.012)):   # carrots poking out with green tops
        add_tube(bm, [((0.25 + dx, -0.03 + dy, 0.66), 0.006, 0.006), ((0.265 + dx, -0.045 + dy, 0.735), 0.013, 0.013)],
                 segs=5, mat_idx=kit.mat("carrot", "#c8692a", roughness=0.7))
        add_tube(bm, [((0.265 + dx, -0.045 + dy, 0.735), 0.01, 0.01), ((0.27 + dx, -0.05 + dy, 0.79), 0.018, 0.012)],
                 segs=4, mat_idx=kit.mat("greens", "#5d7d33", roughness=0.85), smooth=False)
    bm = kit.bm("arm_L", "carry:covered")
    _basket(kit, bm)
    add_ellipsoid(bm, (0.315, -0.065, 0.69), (0.1, 0.083, 0.035), segs=10, rings=5, mat_idx=kit.mat("slot:cloth"),
                  keep=lambda x, y, z: z > -0.2)
    # Earthenware jug carried by its handle.
    bm = kit.bm("arm_L", "carry:jug")
    clay = kit.mat("clay", "#9a5a3a", roughness=0.6)
    add_tube(bm, [((0.29, -0.065, 0.52), 0.045, 0.045), ((0.29, -0.065, 0.6), 0.068, 0.068),
                  ((0.29, -0.065, 0.69), 0.045, 0.045), ((0.29, -0.065, 0.74), 0.034, 0.034),
                  ((0.29, -0.065, 0.765), 0.04, 0.04)], segs=10, mat_idx=clay)
    add_tube(bm, [((0.29, -0.065, 0.735), 0.009, 0.009), ((0.255, -0.065, 0.80), 0.009, 0.009),
                  ((0.26, -0.065, 0.66), 0.009, 0.009)], segs=5, mat_idx=clay)
    # Cloth bundle knotted at the top, hanging from the fist.
    bm = kit.bm("arm_L", "carry:bundle")
    cl = kit.mat("slot:cloth")
    add_ellipsoid(bm, (0.29, -0.065, 0.63), (0.08, 0.075, 0.1), segs=10, rings=6, mat_idx=cl)
    add_tube(bm, [((0.28, -0.065, 0.71), 0.03, 0.025), ((0.245, -0.065, 0.79), 0.015, 0.015)], segs=6, mat_idx=cl)
