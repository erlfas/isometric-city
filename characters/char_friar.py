# Kit: char_friar. Loaded by build_characters.py (load_kit_builders); runs with its globals.

HABIT = [["#e9e3d3", 4, "pabr"], ["#ddd5c0", 3, "pabr"], ["#cfc5ad", 2, "pab"],
         ["#7c7262", 1, "pab"]]            # bleached wool; a few grey (Franciscan) habits
SCAPULAR = [["#26221e", 3, "pabr"], ["#3d2c20", 3, "pabr"], ["#4f3a28", 2, "pab"],
            ["#1d1d22", 2, "pabr"]]        # black, dark brown, black-blue


def friar_body(kit):
    """Ankle-length habit (body), wide sleeves, bare shins and sandals. Replaces kit_body."""
    sk = kit.mat("slot:skin")
    hab = kit.mat("slot:habit")
    scap = kit.mat("slot:scapular")
    rope = kit.mat("rope", "#d3c7a6", roughness=0.95)
    kit.slot("sandals", LEATHER)

    # Habit to the ankle, flared at the hem so walking legs mostly stay inside.
    bm = kit.bm("body")
    add_tube(bm, [((0, 0.01, 0.07), 0.255, 0.225), ((0, 0.005, 0.5), 0.215, 0.18),
                  ((0, 0, 0.97), 0.18, 0.13), ((0, 0, 1.18), 0.19, 0.13),
                  ((0, 0, 1.35), 0.205, 0.125), ((0, 0, 1.40), 0.2, 0.112),
                  ((0, 0, 1.44), 0.13, 0.078), ((0, 0, 1.475), 0.075, 0.065)], segs=10, mat_idx=hab)
    # Scapular, front and back: hangs straight from the shoulders, belted at the waist;
    # the lower halves flare out so the striding legs stay behind them.
    add_panel(bm, 0.97, 1.38, 0.22, 0.26, -0.152, -0.138, 0.012, scap)
    add_panel(bm, 0.30, 0.97, 0.30, 0.22, -0.27, -0.152, 0.012, scap)
    add_panel(bm, 0.97, 1.38, 0.22, 0.26, 0.142, 0.128, 0.012, scap)
    add_panel(bm, 0.30, 0.97, 0.30, 0.22, 0.27, 0.142, 0.012, scap)
    # Capuce: short shoulder cape over the scapular's top.
    add_tube(bm, [((0, 0.01, 1.17), 0.30, 0.205), ((0, 0.01, 1.30), 0.29, 0.195),
                  ((0, 0.005, 1.40), 0.28, 0.18), ((0, 0.005, 1.455), 0.17, 0.125),
                  ((0, 0.005, 1.49), 0.085, 0.076)], segs=10, mat_idx=scap, cap0=False, cap1=False)
    # Rope cincture with two knotted ends hanging at the right hip.
    add_tube(bm, [((0, 0, 0.955), 0.2, 0.185), ((0, 0, 0.985), 0.2, 0.185)], segs=12, mat_idx=rope, cap0=False, cap1=False)
    for dx, end in ((0.0, 0.55), (0.03, 0.62)):
        add_tube(bm, [((-0.11 - dx, -0.165, 0.96), 0.011, 0.011), ((-0.12 - dx, -0.2, 0.78), 0.011, 0.011),
                      ((-0.125 - dx, -0.24, end), 0.011, 0.011)], segs=4, mat_idx=rope, cap0=False)
        add_ellipsoid(bm, (-0.125 - dx, -0.24, end), (0.02, 0.02, 0.026), segs=5, rings=3, mat_idx=rope)

    # Neck + head + face (as kit_body).
    bm = kit.bm("head")
    add_tube(bm, [((0, 0.005, 1.42), 0.055, 0.055), ((0, 0.005, 1.53), 0.05, 0.05)], segs=8, mat_idx=sk)
    add_ellipsoid(bm, HEAD_C, HEAD_R, segs=12, rings=8, mat_idx=sk, taper=0.16)
    eye, lip = kit.mat("eye"), kit.mat("lip")
    hair = kit.mat("slot:hair")
    for sx in (-1, 1):
        x = sx * 0.038
        add_box(bm, x, head_surface_y(x, 1.625, -0.006), 1.625, 0.026, 0.014, 0.017, mat_idx=eye)
        xb = sx * 0.042
        add_box(bm, xb, head_surface_y(xb, 1.652, -0.004), 1.652, 0.042, 0.016, 0.011, mat_idx=hair)
        add_ellipsoid(bm, (sx * 0.092, 0.012, 1.612), (0.014, 0.022, 0.032), segs=6, rings=3, mat_idx=sk)
    ny = head_surface_y(0, 1.60)
    add_tube(bm, [((0, ny + 0.012, 1.635), 0.011, 0.008), ((0, ny - 0.018, 1.592), 0.02, 0.016),
                  ((0, ny - 0.006, 1.578), 0.016, 0.01)], segs=6, mat_idx=sk)
    add_box(bm, 0, head_surface_y(0, 1.552, -0.004), 1.552, 0.046, 0.014, 0.010, mat_idx=lip)

    # Arms: wide habit sleeves widening to the cuff, turned-back cuff, hand.
    for side, sx in (("arm_R", -1), ("arm_L", 1)):
        bm = kit.bm(side)
        sh = (sx * 0.205, 0.0, 1.385)
        el = (sx * 0.232, 0.01, 1.11)
        wr = (sx * 0.238, -0.045, 0.88)
        add_ellipsoid(bm, (sx * 0.2, 0.0, 1.37), (0.064, 0.066, 0.034), segs=8, rings=4, mat_idx=hab)
        add_tube(bm, [(sh, 0.064, 0.066), (el, 0.06, 0.062), (wr, 0.072, 0.076)], segs=8, mat_idx=hab, cap0=False, cap1=False)
        add_tube(bm, [((sx * 0.237, -0.035, 0.92), 0.079, 0.082), ((sx * 0.238, -0.047, 0.875), 0.08, 0.083)],
                 segs=8, mat_idx=hab, cap0=False)
        add_tube(bm, [((sx * 0.238, -0.04, 0.9), 0.034, 0.036), ((sx * 0.239, -0.058, 0.83), 0.032, 0.034)],
                 segs=6, mat_idx=sk, cap0=False, cap1=False)   # wrist
        add_ellipsoid(bm, (sx * 0.24, -0.065, 0.80), (0.03, 0.042, 0.058), segs=6, rings=4, mat_idx=sk)

    # Legs: robe-coloured upper (reads as the habit swinging), bare shin, sandal.
    sd = kit.mat("slot:sandals")
    for side, sx in (("leg_R", -1), ("leg_L", 1)):
        bm = kit.bm(side)
        x = sx * 0.095
        add_tube(bm, [((x, 0, 0.9), 0.08, 0.08), ((x, -0.005, 0.5), 0.07, 0.07), ((x, 0.0, 0.3), 0.07, 0.07)],
                 segs=6, mat_idx=hab, cap0=False)
        add_tube(bm, [((x, 0, 0.32), 0.042, 0.044), ((x, 0.0, 0.08), 0.038, 0.04)], segs=6, mat_idx=sk, cap0=False, cap1=False)
        add_tube(bm, [((x, 0.05, 0.06), 0.042, 0.05), ((x, -0.06, 0.045), 0.045, 0.045),
                      ((x, -0.15, 0.03), 0.035, 0.028)], segs=6, mat_idx=sk)       # bare foot
        add_box(bm, x, -0.045, 0.01, 0.1, 0.25, 0.02, mat_idx=sd)                  # sole
        add_tube(bm, [((x, -0.06, 0.03), 0.05, 0.03), ((x, -0.07, 0.05), 0.05, 0.03)],
                 segs=6, mat_idx=sd, cap0=False, cap1=False)                       # toe strap
        add_tube(bm, [((x, 0.01, 0.075), 0.044, 0.046), ((x, 0.01, 0.1), 0.044, 0.046)],
                 segs=6, mat_idx=sd, cap0=False, cap1=False)                       # ankle strap


def build(kit):
    """Friar (also vicars and priests): white habit to the ankle, dark scapular and capuce,
    rope cincture, tonsure, garden hoe."""
    kit.anim = {"work": "till"}
    friar_body(kit)
    kit.slot("habit", HABIT)
    kit.slot("scapular", SCAPULAR)
    hair = kit.mat("slot:hair")
    cx, cy, cz = HEAD_C
    rx, ry, rz = HEAD_R

    # Hair: mostly the tonsure (ring of hair, bare crown); some secular priests keep short hair.
    kit.option("hair", "tonsure", 6, 6)
    bm = kit.bm("head", "hair:tonsure")
    add_ellipsoid(bm, (cx, cy + 0.006, cz + 0.008), (rx * 1.07, ry * 1.06, rz * 1.04), segs=12, rings=8,
                  mat_idx=hair, keep=lambda x, y, z: (0.4 < z < 0.7) or (y > -0.2 and -0.3 < z <= 0.4))
    kit_heads(kit, {"hair:short": (1, 1), "hair:bald": (1, 1),
                    "beard:none": (5, 5), "beard:short": (2, 2), "beard:full": (1, 1)})

    # Hood (cowl): down on the back, or up over the head.
    scap = kit.mat("slot:scapular")
    kit.option("cowl", "down", 3, 3)
    kit.option("cowl", "up", 1, 1)
    bm = kit.bm("body", "cowl:down")
    add_ellipsoid(bm, (0, 0.17, 1.38), (0.13, 0.07, 0.11), segs=10, rings=6, mat_idx=scap)
    add_tube(bm, [((0, 0.2, 1.33), 0.05, 0.03), ((0, 0.235, 1.2), 0.025, 0.015)], segs=6, mat_idx=scap)
    bm = kit.bm("head", "cowl:up")
    add_ellipsoid(bm, (cx, cy + 0.02, cz + 0.02), (rx * 1.3, ry * 1.25, rz * 1.18), segs=12, rings=8,
                  mat_idx=scap, keep=lambda x, y, z: not (y < -0.42 and -0.75 < z < 0.55))
    add_tube(bm, [((0, 0.02, 1.43), 0.13, 0.115), ((0, 0.02, 1.51), 0.11, 0.11)], segs=10, mat_idx=scap,
             cap0=False, cap1=False)

    # Long garden hoe in the right fist, shaft slanting forward to the ground,
    # blade turned back toward the friar (chops when the arm swings down).
    bm = kit.bm("arm_R")
    wa, ir = kit.mat("wood_ash"), kit.mat("iron_dark")
    hand = Vector((-0.24, -0.065, 0.80))
    d = Vector((0, -0.574, -0.819))           # down the shaft, 35 deg forward of vertical
    bot, top = hand + d * 0.80, hand - d * 0.46
    add_tube(bm, [(tuple(top), 0.015, 0.015), (tuple(bot), 0.016, 0.016)], segs=6, mat_idx=wa)
    p = Vector((0, 0.819, -0.574))            # square to the shaft, back toward the feet
    add_tube(bm, [(tuple(bot - d * 0.02), 0.022, 0.022), (tuple(bot + d * 0.03), 0.022, 0.022)],
             segs=6, mat_idx=ir, smooth=False)
    add_tube(bm, [(tuple(bot + d * 0.01), 0.06, 0.008), (tuple(bot + d * 0.01 + p * 0.13), 0.068, 0.004)],
             segs=4, mat_idx=ir, smooth=False)

    # Left hand: herb basket, a book, or empty.
    kit.option("carry", "basket", 2, 2)
    kit.option("carry", "book", 2, 2)
    kit.option("carry", "none", 1, 1)
    bm = kit.bm("arm_L", "carry:basket")
    wk = kit.mat("wicker", "#a07a45", roughness=0.9)
    herb, lav = kit.mat("herbs", "#5d7a3a", roughness=0.9), kit.mat("lavender", "#7a659a", roughness=0.9)
    add_tube(bm, [((0.3, -0.07, 0.48), 0.07, 0.06), ((0.3, -0.07, 0.55), 0.088, 0.075),
                  ((0.3, -0.07, 0.62), 0.095, 0.08)], segs=10, mat_idx=wk, cap1=False)
    add_ellipsoid(bm, (0.3, -0.07, 0.62), (0.085, 0.072, 0.04), segs=8, rings=4, mat_idx=herb)
    for dx, dy in ((-0.03, 0.02), (0.035, -0.02)):
        add_tube(bm, [((0.3 + dx, -0.07 + dy, 0.62), 0.012, 0.012), ((0.3 + dx * 1.3, -0.07 + dy, 0.71), 0.014, 0.014)],
                 segs=4, mat_idx=lav)
    add_tube(bm, [((0.3, -0.07 + 0.075, 0.62), 0.009, 0.009), ((0.27, -0.068, 0.79), 0.009, 0.009),
                  ((0.3, -0.07 - 0.075, 0.62), 0.009, 0.009)], segs=4, mat_idx=wk)
    bm = kit.bm("arm_L", "carry:book")
    add_box(bm, 0.25, -0.075, 0.73, 0.045, 0.17, 0.22, mat_idx=kit.mat("book", "#6a2a22", roughness=0.7))
    add_box(bm, 0.25, -0.07, 0.73, 0.047, 0.15, 0.2, mat_idx=kit.mat("pages", "#e4dcc4", roughness=0.9))

    # Rosary hanging from the cincture on the left (optional).
    kit.option("rosary", "yes", 2, 2)
    kit.option("rosary", "no", 1, 1)
    bm = kit.bm("body", "rosary:yes")
    wd = kit.mat("wood_dark")
    for i in range(7):
        t = i / 6
        add_ellipsoid(bm, (0.13 + 0.01 * t, -0.175 - 0.06 * t, 0.94 - 0.3 * t), (0.012, 0.012, 0.012),
                      segs=5, rings=3, mat_idx=wd, smooth=False)
    add_box(bm, 0.14, -0.238, 0.6, 0.012, 0.012, 0.07, mat_idx=wd)
    add_box(bm, 0.14, -0.238, 0.615, 0.045, 0.012, 0.012, mat_idx=wd)
