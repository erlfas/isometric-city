import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import type { CityPlan, Citizen } from '../types';
import { TextureLibrary } from './texture-library';
import { CitizenCrowd } from './citizen-crowd';

interface LightPreset {
  sun: number; sunI: number;          // directional key light
  sky: number; ground: number; hemiI: number; // hemisphere fill (sky above, ground bounce below)
  amb: number; ambI: number;          // small flat ambient
  bg: number;                         // clear colour
}

/**
 * Lighting presets (concept_art/medieval_isometric_art_style_guide.md, section 3).
 *
 * three.js lights are physical here: diffuse = albedo / PI * irradiance. For noon:
 *   fill on a vertical wall F = hemiI * (sky + ground) / 2 + ambI       ~= 1.55
 *   sun on the lit wall face   = sunI * cos(theta); the view-locked sun
 *   (updateCameraTransform: 45 deg up, 15 deg past screen-left) gives cos ~= 0.35 ~= 1.25
 * so a sunlit wall shows its texture near its painted value ((F + sun) / PI ~= 0.9) and
 * the shaded side sits at F / (F + sun) ~= 0.55 - the guide's 45-55%. Most fill comes
 * from the hemisphere (directional: tops lighter than undersides); flat ambient is
 * kept low because it washes out texture contrast.
 */
const LIGHT_PRESETS: Record<'dawn' | 'noon' | 'dusk' | 'night', LightPreset> = {
  dawn: { sun: 0xffb07a, sunI: 2.5, sky: 0xffd9b8, ground: 0x5a4a40, hemiI: 1.9, amb: 0x5c4238, ambI: 0.3, bg: 0x735348 },
  noon: { sun: 0xfff8e7, sunI: 3.6, sky: 0xfff4e2, ground: 0x6b6250, hemiI: 2.35, amb: 0xdde3ea, ambI: 0.3, bg: 0x3a4f63 },
  dusk: { sun: 0xff8a55, sunI: 2.3, sky: 0xe9b39a, ground: 0x4a3a40, hemiI: 1.6, amb: 0x382c44, ambI: 0.3, bg: 0x483244 },
  night: { sun: 0x6f8fc4, sunI: 0.9, sky: 0x40507a, ground: 0x15161e, hemiI: 0.9, amb: 0x181e28, ambI: 0.3, bg: 0x0a1018 },
};

export class ThreeIsometricRenderer {
  public scene: THREE.Scene;
  public camera: THREE.OrthographicCamera;
  public renderer: THREE.WebGLRenderer;
  private canvas: HTMLCanvasElement;

  // Camera navigation & isometric projection
  public targetPos = new THREE.Vector3(0, 0, 0);
  public currentPos = new THREE.Vector3(0, 0, 0);
  public zoom: number = 65.0; // World units visible (spacious city view)
  public targetZoom: number = 65.0;
  public rotationQuadrant: number = 0; // 0=SW, 1=NW, 2=NE, 3=SE
  public currentRotationAngle: number = 0;
  public targetRotationAngle: number = 0;

  // Lighting
  private dirLight: THREE.DirectionalLight;
  private hemiLight: THREE.HemisphereLight;
  private ambientLight: THREE.AmbientLight;

  // Loaded GLTF model templates
  public models: Map<string, THREE.Group> = new Map();
  public isLoaded: boolean = false;
  public textures = new TextureLibrary();

  private groundPlane: THREE.Mesh;
  private crowd: CitizenCrowd;

  // Speech bubbles data
  public activeBubbles: { id: string; text: string; x: number; y: number; z: number; timer: number }[] = [];
  public hoveredCitizen: Citizen | null = null;
  public followingCitizen: Citizen | null = null;

  // Raycasting for touch & click picking
  private raycaster = new THREE.Raycaster();
  private groundPlaneMath = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  private ndcVec = new THREE.Vector2();

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x4a6572); // Medieval daylight sky
    this.crowd = new CitizenCrowd(this.scene);

    // Orthographic Isometric Camera
    const aspect = canvas.clientWidth / canvas.clientHeight || 16 / 9;
    this.camera = new THREE.OrthographicCamera(
      -this.zoom * aspect * 0.5,
      this.zoom * aspect * 0.5,
      this.zoom * 0.5,
      -this.zoom * 0.5,
      -500,
      1000
    );

    // Renderer setup with shadows
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
      powerPreference: 'high-performance'
    });
    this.renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
    
    // Dynamic mobile DPR clamping to prevent mobile GPU thermal throttling
    const isMobile = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0) || window.innerWidth < 768;
    const maxDpr = isMobile ? 1.5 : 2.0;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, maxDpr));
    this.renderer.shadowMap.enabled = true;
    // Crisp shadows per the style guide (PCFSoft is removed in this three.js and fell back anyway).
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    // Linear: the light rig (LIGHT_PRESETS) is balanced so lit walls show textures near
    // their painted value, so no curve is needed. ACES desaturated brick toward grey-pink;
    // Neutral's black-level offset crushed the blue channel of dark brick (measured).
    this.renderer.toneMapping = THREE.LinearToneMapping;
    this.renderer.toneMappingExposure = 1.0;

    // Mobile WebGL context preservation
    this.canvas.addEventListener('webglcontextlost', (e) => {
      e.preventDefault();
      console.warn('[WebGL] Context lost on mobile device.');
    });
    this.canvas.addEventListener('webglcontextrestored', () => {
      console.info('[WebGL] Context restored.');
      this.render();
    });

    // Atmospheric lighting (values come from LIGHT_PRESETS via updateDayNightLighting)
    this.hemiLight = new THREE.HemisphereLight();
    this.scene.add(this.hemiLight);

    this.ambientLight = new THREE.AmbientLight();
    this.scene.add(this.ambientLight);

    // Directional sunlight casting crisp isometric diagonal shadows
    const shadowRes = isMobile ? 1024 : 4096;
    this.dirLight = new THREE.DirectionalLight();
    this.dirLight.position.set(-80, 130, -70);
    this.dirLight.castShadow = true;
    this.dirLight.shadow.mapSize.width = shadowRes;
    this.dirLight.shadow.mapSize.height = shadowRes;
    this.dirLight.shadow.camera.near = 10;
    this.dirLight.shadow.camera.far = 400;
    const d = 140;
    this.dirLight.shadow.camera.left = -d;
    this.dirLight.shadow.camera.right = d;
    this.dirLight.shadow.camera.top = d;
    this.dirLight.shadow.camera.bottom = -d;
    this.dirLight.shadow.bias = -0.0003;
    this.scene.add(this.dirLight);
    this.scene.add(this.dirLight.target);
    this.applyLightPreset(LIGHT_PRESETS.noon);

    // Create ground terrain with cobblestone / dirt textures
    this.groundPlane = this.createGroundTerrain();
    this.scene.add(this.groundPlane);

    this.updateCameraTransform();
  }

  private groundCanvas!: HTMLCanvasElement;
  private groundTex!: THREE.CanvasTexture;

  private createGroundTerrain(): THREE.Mesh {
    this.groundCanvas = document.createElement('canvas');
    this.groundCanvas.width = 2048;
    this.groundCanvas.height = 2048;
    const ctx = this.groundCanvas.getContext('2d')!;

    // The canvas is a SPLAT MASK once textures load (applyGroundTextures):
    //   R = cobblestone weight, B = dirt weight, G = large-scale tone (0.5 = neutral).
    // Until then it is shown directly as the ground colour, so it must also look sane.
    ctx.fillStyle = 'rgb(0,128,0)';
    ctx.fillRect(0, 0, 2048, 2048);

    // Large-scale tone variation: breaks up texture repetition across the meadow.
    ctx.filter = 'blur(6px)';
    for (let i = 0; i < 4000; i++) {
      const rx = Math.random() * 2048;
      const ry = Math.random() * 2048;
      const r = Math.random() * 14 + 6;
      ctx.fillStyle = Math.random() < 0.5 ? 'rgb(0,104,0)' : 'rgb(0,152,0)';
      ctx.beginPath();
      ctx.arc(rx, ry, r, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.filter = 'none';

    this.groundTex = new THREE.CanvasTexture(this.groundCanvas);
    this.groundTex.wrapS = THREE.ClampToEdgeWrapping;
    this.groundTex.wrapT = THREE.ClampToEdgeWrapping;

    const geo = new THREE.PlaneGeometry(700, 550, 32, 32);
    const mat = new THREE.MeshStandardMaterial({
      map: this.groundTex,
      roughness: 0.92,
      metalness: 0.04
    });

    const mesh = new THREE.Mesh(geo, mat);
    mesh.rotation.x = -Math.PI / 2;
    mesh.position.y = 0;
    mesh.receiveShadow = true;

    return mesh;
  }

  /**
   * Turn the ground into a texture splat: tiled grass / dirt / cobblestone in world
   * metres, blended by the canvas mask (R cobble, B dirt, G large-scale tone).
   */
  private applyGroundTextures(): void {
    const grass = this.textures.getAlbedo('grass');
    const dirt = this.textures.getAlbedo('dirt_road');
    const cobble = this.textures.getAlbedo('cobblestone');
    if (!grass || !dirt || !cobble) return;
    const tile = (id: string) => (this.textures.getTile(id) ?? [4, 4])[0];

    const mat = this.groundPlane.material as THREE.MeshStandardMaterial;
    mat.customProgramCacheKey = () => 'ground-splat-v1';
    mat.onBeforeCompile = (shader) => {
      shader.uniforms.groundGrass = { value: grass };
      shader.uniforms.groundDirt = { value: dirt };
      shader.uniforms.groundCobble = { value: cobble };
      shader.uniforms.groundTiles = { value: new THREE.Vector3(tile('grass'), tile('dirt_road'), tile('cobblestone')) };

      shader.vertexShader = 'varying vec2 vGroundXZ;\n' + shader.vertexShader.replace(
        '#include <begin_vertex>',
        '#include <begin_vertex>\n  vGroundXZ = (modelMatrix * vec4(transformed, 1.0)).xz;'
      );
      shader.fragmentShader =
        'varying vec2 vGroundXZ;\nuniform sampler2D groundGrass;\nuniform sampler2D groundDirt;\n' +
        'uniform sampler2D groundCobble;\nuniform vec3 groundTiles;\n' +
        shader.fragmentShader.replace(
          '#include <map_fragment>',
          `
  vec4 gMask = texture2D( map, vMapUv );
  vec3 gGrass = texture2D( groundGrass, vGroundXZ / groundTiles.x ).rgb;
  // second, rotated and larger grass sample hides the 6 m repeat at city zoom
  vec2 gRot = mat2( 0.8, -0.6, 0.6, 0.8 ) * vGroundXZ / ( groundTiles.x * 3.7 );
  gGrass = mix( gGrass, texture2D( groundGrass, gRot ).rgb, 0.35 );
  vec3 gDirt = texture2D( groundDirt, vGroundXZ / groundTiles.y ).rgb;
  vec3 gCobble = texture2D( groundCobble, vGroundXZ / groundTiles.z ).rgb;
  float wCobble = gMask.r;
  float wDirt = gMask.b * ( 1.0 - wCobble );
  vec3 gCol = mix( mix( gGrass, gDirt, wDirt ), gCobble, wCobble );
  gCol *= 0.78 + 0.44 * gMask.g;
  diffuseColor.rgb *= gCol;
`
        );
    };
    mat.needsUpdate = true;
  }

  private updateGroundWithPlan(plan: CityPlan): void {
    if (!this.groundCanvas || !this.groundTex) return;
    const ctx = this.groundCanvas.getContext('2d')!;

    // Coordinate mapping: World (-350..350, -275..275) to Canvas (0..2048, 0..2048)
    const toCanvasX = (wx: number) => ((wx + 350) / 700) * 2048;
    const toCanvasY = (wz: number) => ((wz + 275) / 550) * 2048;

    // Splat-mask painting: each layer ADDS to its own channel ('lighter'), so cobble (R),
    // dirt (B) and tone (G) stay independent. Blur gives soft, painterly transitions.
    ctx.globalCompositeOperation = 'lighter';

    // 1. Lublin Promontory Old Town loess plateau: trodden earth showing through grass
    if (plan.defense && plan.defense.perimeterPoints.length > 0) {
      ctx.save();
      ctx.filter = 'blur(10px)';
      ctx.fillStyle = 'rgb(0,0,110)';
      ctx.beginPath();
      const first = plan.defense.perimeterPoints[0];
      ctx.moveTo(toCanvasX(first.x), toCanvasY(first.z));
      for (let i = 1; i < plan.defense.perimeterPoints.length; i++) {
        const pt = plan.defense.perimeterPoints[i];
        ctx.lineTo(toCanvasX(pt.x), toCanvasY(pt.z));
      }
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    }

    // 2. Castle Hill bailey plateau
    ctx.save();
    ctx.filter = 'blur(10px)';
    ctx.fillStyle = 'rgb(0,0,110)';
    ctx.beginPath();
    ctx.ellipse(toCanvasX(275), toCanvasY(90), 160, 130, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // 3. Czechówka & Bystrzyca river valley slopes: lusher, darker meadow (tone down)
    ctx.save();
    ctx.globalCompositeOperation = 'source-over';
    ctx.filter = 'blur(12px)';
    ctx.strokeStyle = 'rgb(0,90,0)';
    ctx.lineWidth = 45;
    ctx.beginPath();
    ctx.moveTo(toCanvasX(-340), toCanvasY(45));
    ctx.quadraticCurveTo(toCanvasX(-100), toCanvasY(55), toCanvasX(210), toCanvasY(35));
    ctx.stroke();
    ctx.restore();

    // 4. Street network: dirt verges with a cobbled carriageway
    if (plan.streetNetwork && plan.streetNetwork.nodes && plan.streetNetwork.edges) {
      const nodeMap = new Map<string, { x: number; z: number }>();
      plan.streetNetwork.nodes.forEach(n => nodeMap.set(n.id, { x: n.x, z: n.z }));

      // Outer wide road border (dirt)
      ctx.save();
      ctx.filter = 'blur(3px)';
      ctx.strokeStyle = 'rgb(0,0,255)';
      ctx.lineWidth = 26;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.beginPath();
      plan.streetNetwork.edges.forEach(([idA, idB]) => {
        const a = nodeMap.get(idA);
        const b = nodeMap.get(idB);
        if (a && b) {
          ctx.moveTo(toCanvasX(a.x), toCanvasY(a.z));
          ctx.lineTo(toCanvasX(b.x), toCanvasY(b.z));
        }
      });
      ctx.stroke();

      // Inner cobblestone street track
      ctx.filter = 'blur(2px)';
      ctx.strokeStyle = 'rgb(255,0,0)';
      ctx.lineWidth = 18;
      ctx.stroke();
      ctx.restore();
    }

    // 5. Rynek (Market Square): fully cobbled plaza
    const rx1 = toCanvasX(-42);
    const rz1 = toCanvasY(-32);
    const rx2 = toCanvasX(42);
    const rz2 = toCanvasY(32);

    ctx.save();
    ctx.filter = 'blur(2px)';
    ctx.fillStyle = 'rgb(255,0,0)';
    ctx.fillRect(rx1, rz1, rx2 - rx1, rz2 - rz1);
    ctx.restore();

    ctx.globalCompositeOperation = 'source-over';
    this.groundTex.needsUpdate = true;
  }

  public async loadAllModels(): Promise<void> {
    const loader = new GLTFLoader();
    const modelNames = [
      'town_hall',
      'szmatruz',
      'market_stall_red_white',
      'market_stall_blue_white',
      'market_stall_yellow_white',
      'market_cart',
      'town_well',
      'house_timber_log',
      'house_half_timber',
      'house_patrician_brick',
      'shed_timber',
      'church_gothic',
      'castle_donjon',
      'curtain_wall',
      'curtain_tower',
      'tree_oak',
      'house_baker',
      'house_brewer',
      'house_tanner',
      'house_potter',
      'house_weaver',
      'blacksmith_workshop',
      'watermill',
      'windmill',
      'stone_quarry',
      'logging_camp',
      'river_harbor',
      'gate_krakow',
      'gate_grodzka',
      'monastery_cloister',
      'archery_yard',
      'char_baker',
      'char_tanner',
      'char_carpenter',
      'char_blacksmith',
      'char_brewer',
      'char_potter',
      'char_weaver',
      'char_stonemason',
      'char_woodcutter',
      'char_friar',
      'char_guard',
      'char_merchant',
      'char_farmer',
      'char_townswoman'
    ];

    try {
      await this.textures.load(this.renderer);
      this.applyGroundTextures();
    } catch (err) {
      // Flat colours still render; textures are an enhancement. The ground canvas is a
      // splat mask (pure R/G/B), so fall back to a plain meadow colour instead.
      console.warn('[ThreeRenderer] Texture library failed to load, using flat materials:', err);
      const gm = this.groundPlane.material as THREE.MeshStandardMaterial;
      gm.map = null;
      gm.color.set(0x475d2e);
      gm.needsUpdate = true;
    }

    console.log('[ThreeRenderer] Loading 45 Blender-authored GLB assets (buildings and characters)...');

    for (const name of modelNames) {
      try {
        const gltf = await loader.loadAsync(`/models/${name}.glb`);
        gltf.scene.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            child.castShadow = true;
            child.receiveShadow = true;
          }
        });
        if (name.startsWith('char_')) this.crowd.addArchetype(name, gltf.scene);
        else this.textures.applyToTemplate(gltf.scene);
        gltf.scene.name = name; // clones keep it: findInstances() looks placed models up by name
        this.models.set(name, gltf.scene);
      } catch (err) {
        console.warn(`[ThreeRenderer] Failed loading /models/${name}.glb:`, err);
      }
    }

    this.isLoaded = true;
    console.log(`[ThreeRenderer] Successfully loaded ${this.models.size} 3D assets!`);
  }

  public populateCityScene(plan: CityPlan): void {
    if (!this.isLoaded) return;

    // 0. Paint street networks and terrain matching historical topography
    this.updateGroundWithPlan(plan);

    // 1. Place Old Town Hall at Market Square center
    const townHallTemplate = this.models.get('town_hall');
    if (townHallTemplate) {
      const th = townHallTemplate.clone();
      th.position.set(0, 0, 0);
      th.rotation.y = 0;
      this.scene.add(th);
    }

    // 2. Place Szmatruz (Cloth Hall)
    const szmatruzTemplate = this.models.get('szmatruz');
    if (szmatruzTemplate) {
      const sz = szmatruzTemplate.clone();
      sz.position.set(22, 0, -18);
      sz.rotation.y = Math.PI / 2;
      this.scene.add(sz);
    }

    // 3. Place Municipal Well and Pillory in the square
    const wellTemplate = this.models.get('town_well');
    if (wellTemplate) {
      const well = wellTemplate.clone();
      well.position.set(-14, 0, 10);
      this.scene.add(well);
    }

    // 4. Place Collegiate Parish Church (Fara - Kościół św. Michała)
    const churchTemplate = this.models.get('church_gothic');
    if (churchTemplate) {
      const church = churchTemplate.clone();
      church.position.set(130, 1.2, 20);
      church.rotation.y = Math.PI / 2;
      this.scene.add(church);
    }

    // 5. Place Castle Donjon Keep & Archery Training Yard on Castle Hill
    const donjonTemplate = this.models.get('castle_donjon');
    if (donjonTemplate) {
      const donjon = donjonTemplate.clone();
      donjon.position.set(275, 2.5, 75);
      this.scene.add(donjon);
    }

    const archeryTemplate = this.models.get('archery_yard');
    if (archeryTemplate) {
      const yard = archeryTemplate.clone();
      yard.position.set(245, 2.0, 95);
      yard.rotation.y = Math.PI / 4;
      this.scene.add(yard);
    }

    // 5b. Place Dominican Monastery & Cloister Garden in Friary Quarter
    const cloisterTemplate = this.models.get('monastery_cloister');
    if (cloisterTemplate) {
      const cloister = cloisterTemplate.clone();
      cloister.position.set(70, 0.5, -60);
      cloister.rotation.y = 0;
      this.scene.add(cloister);
    }

    // 6. Place Vibrant Royal Fair Market Stalls and Carts across Rynek
    const stallTypes = ['market_stall_red_white', 'market_stall_blue_white', 'market_stall_yellow_white'];
    const stallCoords = [
      { x: -16, z: -14, rot: 0 },
      { x: -10, z: -14, rot: 0 },
      { x: -4, z: -14, rot: 0 },
      { x: 10, z: -14, rot: 0 },
      { x: 16, z: -14, rot: 0 },
      { x: -16, z: 14, rot: Math.PI },
      { x: -10, z: 14, rot: Math.PI },
      { x: -4, z: 14, rot: Math.PI },
      { x: 10, z: 14, rot: Math.PI },
      { x: 16, z: 14, rot: Math.PI },
      { x: -22, z: -6, rot: Math.PI / 2 },
      { x: -22, z: 2, rot: Math.PI / 2 },
      { x: -22, z: 8, rot: Math.PI / 2 },
      { x: 26, z: -6, rot: -Math.PI / 2 },
      { x: 26, z: 2, rot: -Math.PI / 2 }
    ];

    stallCoords.forEach((coord, idx) => {
      const type = stallTypes[idx % stallTypes.length];
      const tmpl = this.models.get(type);
      if (tmpl) {
        const stall = tmpl.clone();
        stall.position.set(coord.x, 0, coord.z);
        stall.rotation.y = coord.rot;
        this.scene.add(stall);
      }
    });

    // Market carts with spoked wheels
    const cartTemplate = this.models.get('market_cart');
    if (cartTemplate) {
      const cartPositions = [
        { x: -24, z: -18, rot: 0.4 },
        { x: 22, z: -26, rot: -0.6 },
        { x: -24, z: 16, rot: 1.2 },
        { x: 6, z: 18, rot: -0.8 },
        { x: -2, z: -20, rot: 1.8 }
      ];
      cartPositions.forEach(pos => {
        const cart = cartTemplate.clone();
        cart.position.set(pos.x, 0, pos.z);
        cart.rotation.y = pos.rot;
        this.scene.add(cart);
      });
    }

    // 7. Build Defensive Curtain Wall and Towers around Perimeter
    const wallTemplate = this.models.get('curtain_wall');
    const towerTemplate = this.models.get('curtain_tower');
    const krakowGateTmpl = this.models.get('gate_krakow');
    const grodzkaGateTmpl = this.models.get('gate_grodzka');
    const perimeter = plan.defense.perimeterPoints;

    // Gate body half-extents in world X (road axis) and Z (wall axis): L/2 and W/2 of
    // build_krakow_gate / build_grodzka_gate in build_assets.py. Keep in sync.
    const GATE_HALF: Record<string, [number, number]> = {
      gate_krakow: [5.25, 5.0],
      gate_grodzka: [4.75, 4.5],
    };
    const WALL_HALF_THICK = 1.3; // curtain_wall plinth is 2.6 m deep
    // Distance from a gate centre along unit direction (ux, uz) at which a wall segment should start.
    const gateTrim = (id: string, ux: number, uz: number): number => {
      const half = GATE_HALF[id];
      if (!half) return 0;
      const ax = Math.abs(ux), az = Math.abs(uz);
      const tx = ax > 1e-6 ? half[0] / ax : Infinity;
      const tz = az > 1e-6 ? half[1] / az : Infinity;
      // Inset so the wall's end face corners stay inside the gate body.
      const inset = tz <= tx ? WALL_HALF_THICK * ax / az : WALL_HALF_THICK * az / ax;
      return Math.max(0, Math.min(tx, tz) - inset - 0.2);
    };

    for (let i = 0; i < perimeter.length; i++) {
      const p1 = perimeter[i];
      const p2 = perimeter[(i + 1) % perimeter.length];

      // Add Dedicated Fortified Gate or Defense Tower
      if (p1.id === 'gate_krakow' && krakowGateTmpl) {
        const gate = krakowGateTmpl.clone();
        gate.position.set(p1.x, 0, p1.z);
        gate.rotation.y = Math.PI;
        this.scene.add(gate);
      } else if (p1.id === 'gate_grodzka' && grodzkaGateTmpl) {
        const gate = grodzkaGateTmpl.clone();
        gate.position.set(p1.x, 0, p1.z);
        gate.rotation.y = 0;
        this.scene.add(gate);
      } else if (towerTemplate) {
        const tower = towerTemplate.clone();
        tower.position.set(p1.x, 0, p1.z);
        this.scene.add(tower);
      }

      // Add Wall Segment. At a gate the segment stops at the gate body's outer face (tucked in
      // just far enough to hide the wall's end corners) instead of running into the passage.
      if (wallTemplate) {
        const len0 = Math.hypot(p2.x - p1.x, p2.z - p1.z);
        const ux = (p2.x - p1.x) / len0;
        const uz = (p2.z - p1.z) / len0;
        const t0 = gateTrim(p1.id, ux, uz);
        const t1 = len0 - gateTrim(p2.id, ux, uz);
        const ax = p1.x + ux * t0, az = p1.z + uz * t0;
        const bx = p1.x + ux * t1, bz = p1.z + uz * t1;
        const midX = (ax + bx) * 0.5;
        const midZ = (az + bz) * 0.5;
        const dx = bx - ax;
        const dz = bz - az;
        const segLen = Math.hypot(dx, dz);
        const angle = Math.atan2(dx, dz);

        // Tile 16 m wall modules along the segment instead of stretching one module:
        // stretching smeared the brick texture (UVs are in metres) and the crenellations.
        const MODULE = 16.0;
        const count = Math.max(1, Math.round(segLen / MODULE));
        const fit = segLen / (count * MODULE); // close to 1
        for (let k = 0; k < count; k++) {
          const t = (k + 0.5) / count - 0.5;
          const wall = wallTemplate.clone();
          wall.position.set(midX + dx * t, 0, midZ + dz * t);
          wall.rotation.y = angle + Math.PI / 2;
          wall.scale.set(fit, 1.0, 1.0);
          this.scene.add(wall);
        }
      }
    }

    // 8. Populate 580 Parcels with Distinct Authentic 3D Models
    const shedTmpl = this.models.get('shed_timber');
    const brickTmpl = this.models.get('house_patrician_brick');
    const halfTimberTmpl = this.models.get('house_half_timber');
    const logTmpl = this.models.get('house_timber_log');
    const bakerTmpl = this.models.get('house_baker');
    const brewerTmpl = this.models.get('house_brewer');
    const tannerTmpl = this.models.get('house_tanner');
    const potterTmpl = this.models.get('house_potter');
    const weaverTmpl = this.models.get('house_weaver');
    const smithTmpl = this.models.get('blacksmith_workshop');
    const watermillTmpl = this.models.get('watermill');
    const windmillTmpl = this.models.get('windmill');
    const quarryTmpl = this.models.get('stone_quarry');
    const loggingTmpl = this.models.get('logging_camp');
    const harborTmpl = this.models.get('river_harbor');

    // Helper for deterministic hashing
    const hashString = (str: string): number => {
      let hash = 0;
      for (let k = 0; k < str.length; k++) {
        hash = (hash << 5) - hash + str.charCodeAt(k);
        hash |= 0;
      }
      return Math.abs(hash);
    };

    const hsl = { h: 0, s: 0, l: 0 };

    for (let i = 0; i < plan.parcels.length; i++) {
      const p = plan.parcels[i];
      let tmpl: THREE.Group | undefined;
      let scaleX = 1.0;
      let scaleZ = 1.0;

      const craftId = (p as any).craft?.id || '';
      const bType = p.buildingType || '';
      const hash = hashString(p.id || `parcel_${i}`);

      // 1. Storage & utility sheds
      if ((p.isShed || bType.startsWith('shed_')) && shedTmpl) {
        tmpl = shedTmpl;
        scaleX = Math.min(1.15, Math.max(0.85, p.width / 5.2));
        scaleZ = Math.min(1.15, Math.max(0.85, p.depth / 6.2));
      }
      // 2. Specific Craft Guild Workshops & Industrial Facilities
      else if (craftId === 'baker' || bType.includes('baker')) {
        tmpl = bakerTmpl || halfTimberTmpl;
      } else if (craftId === 'tanner' || bType.includes('tanner')) {
        tmpl = tannerTmpl || logTmpl;
      } else if (craftId === 'brewer' || bType.includes('brewer')) {
        tmpl = brewerTmpl || brickTmpl;
      } else if (craftId === 'blacksmith' || craftId === 'armorer' || bType.includes('blacksmith')) {
        tmpl = smithTmpl || halfTimberTmpl;
      } else if (craftId === 'potter' || bType.includes('potter')) {
        tmpl = potterTmpl || logTmpl;
      } else if (craftId === 'weaver' || craftId === 'tailor' || bType.includes('weaver')) {
        tmpl = weaverTmpl || halfTimberTmpl;
      } else if (bType.includes('watermill')) {
        tmpl = watermillTmpl || logTmpl;
      } else if (bType.includes('windmill')) {
        tmpl = windmillTmpl || logTmpl;
      } else if (bType.includes('quarry') || craftId === 'mason') {
        tmpl = quarryTmpl || brickTmpl;
      } else if (bType.includes('sawmill') || bType.includes('logging') || (craftId === 'carpenter' && p.district === 'krakow_suburb' && (hash % 4 === 0))) {
        tmpl = loggingTmpl || logTmpl;
      } else if (bType.includes('harbor')) {
        tmpl = harborTmpl || halfTimberTmpl;
      }
      // 3. Patrician Kamienice & Stone/Brick Architecture (Old Town, Rynek, Grodzka)
      else if (
        bType.includes('patrician') ||
        bType.includes('kamienica') ||
        bType.includes('brick') ||
        bType.includes('stone_arches') ||
        craftId === 'goldsmith'
      ) {
        tmpl = brickTmpl;
      }
      // 4. Urban Half-Timber & Jettied Fachwerk (Middle-Class Artisans)
      else if (
        bType.includes('fachwerk') ||
        bType.includes('half_timber') ||
        bType.includes('jettied') ||
        bType.includes('narrow_gable') ||
        bType.includes('furrier') ||
        bType.includes('shoemaker') ||
        craftId === 'shoemaker' ||
        craftId === 'furrier' ||
        craftId === 'candlemaker' ||
        craftId === 'roper' ||
        craftId === 'butcher'
      ) {
        tmpl = halfTimberTmpl;
      }
      // 5. Rustic Vernacular Timber & Thatched Cottages
      else if (
        bType.includes('log') ||
        bType.includes('timber') ||
        bType.includes('thatched') ||
        bType.includes('cruck') ||
        bType.includes('longhouse') ||
        bType.includes('cottage') ||
        bType.includes('loess') ||
        bType.includes('cooper') ||
        craftId === 'cooper' ||
        craftId === 'wheelwright' ||
        craftId === 'carpenter'
      ) {
        tmpl = logTmpl;
      }
      // 6. District Harmonious Context Fallbacks
      else if (p.district === 'market_square') {
        tmpl = (hash % 4 === 0 ? halfTimberTmpl : brickTmpl) || brickTmpl;
      } else if (p.district === 'krakow_suburb') {
        tmpl = (hash % 3 === 0 ? halfTimberTmpl : logTmpl) || logTmpl;
      } else {
        tmpl = (hash % 2 === 0 ? halfTimberTmpl : logTmpl) || halfTimberTmpl;
      }

      if (!tmpl) tmpl = halfTimberTmpl || brickTmpl || logTmpl;

      if (!p.isShed && !bType.startsWith('shed_')) {
        scaleX = Math.min(1.15, Math.max(0.85, p.width / 8.5));
        scaleZ = Math.min(1.15, Math.max(0.85, p.depth / 12.0));
      }

      if (tmpl) {
        const house = tmpl.clone(true);
        const scaleY = 0.95 + ((hash % 11) / 10) * 0.10; // 0.95 to 1.05 height variation

        house.position.set(p.x, p.elevation * 0.3, p.z);
        house.rotation.y = (p.orientation * Math.PI) / 180;
        house.scale.set(scaleX, scaleY, scaleZ);
        house.userData = { parcelId: p.id };

        // Subtle deterministic HSL color variation on materials for organic historical realism
        const rand1 = ((hash % 31) / 30) * 2 - 1;
        const rand2 = (((hash >> 3) % 31) / 30) * 2 - 1;
        const rand3 = (((hash >> 6) % 31) / 30) * 2 - 1;

        house.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            const mesh = child as THREE.Mesh;
            const applyJitter = (mat: THREE.Material): THREE.Material => {
              // Textured families: shared cached variant (brick a/b + tint) per parcel hash.
              const textured = this.textures.variant(mat, hash);
              if (textured) return textured;
              if (!(mat as THREE.MeshStandardMaterial).isMeshStandardMaterial) return mat;
              const stdMat = (mat as THREE.MeshStandardMaterial).clone();
              const mName = stdMat.name || '';

              if (mName.includes('RoofTileRed')) {
                // Pantiles: shift between warm terracotta orange and deep burnt tile red
                stdMat.color.getHSL(hsl);
                stdMat.color.setHSL(
                  hsl.h + rand1 * 0.025,
                  Math.max(0.2, Math.min(1.0, hsl.s + rand2 * 0.08)),
                  Math.max(0.12, Math.min(0.65, hsl.l + rand3 * 0.06))
                );
              } else if (mName.includes('RoofThatch')) {
                // Thatch: golden dry straw vs weathered grey-brown thatch
                stdMat.color.getHSL(hsl);
                stdMat.color.setHSL(
                  hsl.h + rand1 * 0.02,
                  Math.max(0.15, Math.min(1.0, hsl.s + rand2 * 0.07)),
                  Math.max(0.2, Math.min(0.68, hsl.l + rand3 * 0.06))
                );
              } else if (mName.includes('RoofShingle')) {
                // Wood shingle: grey weathered vs tar-treated
                stdMat.color.getHSL(hsl);
                stdMat.color.setHSL(
                  hsl.h,
                  hsl.s,
                  Math.max(0.15, Math.min(0.55, hsl.l + rand1 * 0.06))
                );
              } else if (mName.includes('Plaster')) {
                // Limewash: warm chalk vs fresh white
                stdMat.color.getHSL(hsl);
                stdMat.color.setHSL(
                  hsl.h + rand1 * 0.012,
                  hsl.s,
                  Math.max(0.72, Math.min(0.96, hsl.l + rand2 * 0.04))
                );
              } else if (mName.includes('Timber')) {
                // Oak timber: linseed/pitch treated vs weathered
                stdMat.color.getHSL(hsl);
                stdMat.color.setHSL(
                  hsl.h,
                  hsl.s,
                  Math.max(0.08, Math.min(0.42, hsl.l + rand1 * 0.04))
                );
              } else if (mName.includes('Brick')) {
                // Brick masonry kiln batches
                stdMat.color.getHSL(hsl);
                stdMat.color.setHSL(
                  hsl.h + rand1 * 0.02,
                  Math.max(0.2, Math.min(0.9, hsl.s + rand2 * 0.05)),
                  Math.max(0.15, Math.min(0.55, hsl.l + rand3 * 0.04))
                );
              }
              return stdMat;
            };

            if (Array.isArray(mesh.material)) {
              mesh.material = mesh.material.map(applyJitter);
            } else if (mesh.material) {
              mesh.material = applyJitter(mesh.material as THREE.Material);
            }
          }
        });

        this.scene.add(house);
      }
    }

    // 9. Place Medieval Oak Trees along roads and outer green verge
    const treeTemplate = this.models.get('tree_oak');
    if (treeTemplate) {
      if (plan.vegetation && plan.vegetation.length > 0) {
        for (let i = 0; i < plan.vegetation.length; i++) {
          const v = plan.vegetation[i];
          const tree = treeTemplate.clone();
          tree.position.set(v.x, 0, v.z);
          const s = v.scale ?? 1.0;
          tree.scale.set(s, s, s);
          tree.rotation.y = ((v.rotation ?? 0) * Math.PI) / 180;
          this.scene.add(tree);
        }
        console.log(`[ThreeRenderer] Placed ${plan.vegetation.length} clearance-verified historical trees.`);
      } else {
        // Fallback: strict spatial clearance check
        const placedTrees: { x: number; z: number }[] = [];
        for (let t = 0; t < 120; t++) {
          const ang = Math.random() * Math.PI * 2;
          const dist = 165 + Math.random() * 95;
          const tx = Math.cos(ang) * dist;
          const tz = Math.sin(ang) * dist;

          // Check against parcels
          let collides = false;
          for (let p = 0; p < plan.parcels.length; p++) {
            const parcel = plan.parcels[p];
            const bRad = Math.hypot(parcel.width, parcel.depth) * 0.5;
            if (Math.hypot(tx - parcel.x, tz - parcel.z) < bRad + 5.5) {
              collides = true;
              break;
            }
          }
          if (collides) continue;

          // Check against other trees
          for (let k = 0; k < placedTrees.length; k++) {
            if (Math.hypot(tx - placedTrees[k].x, tz - placedTrees[k].z) < 5.5) {
              collides = true;
              break;
            }
          }
          if (collides) continue;

          placedTrees.push({ x: tx, z: tz });
          const tree = treeTemplate.clone();
          tree.position.set(tx, 0, tz);
          const s = 0.8 + Math.random() * 0.5;
          tree.scale.set(s, s, s);
          tree.rotation.y = Math.random() * Math.PI * 2;
          this.scene.add(tree);
        }
      }
    }

    console.log('[ThreeRenderer] Full medieval city populated successfully with 0 building overlaps!');
  }

  public getCitizenArchetype(c: Citizen): string {
    const trade = (c.trade || '').toLowerCase();
    const rank = (c.guildRank || '').toLowerCase();
    const wealth = c.wealthClass || '';

    if (trade.includes('baker')) return 'char_baker';
    if (trade.includes('tanner') || trade.includes('shoemaker') || trade.includes('furrier') || trade.includes('butcher')) return 'char_tanner';
    if (trade.includes('carpenter') || trade.includes('joiner') || trade.includes('wheelwright')) return 'char_carpenter';
    if (trade.includes('blacksmith') || trade.includes('armorer') || trade.includes('goldsmith')) return 'char_blacksmith';
    if (trade.includes('brewer') || trade.includes('cooper')) return 'char_brewer';
    if (trade.includes('potter')) return 'char_potter';
    if (trade.includes('weaver') || trade.includes('tailor') || trade.includes('roper')) return 'char_weaver';
    if (trade.includes('stone') || trade.includes('mason') || trade.includes('quarry')) return 'char_stonemason';
    if (trade.includes('wood') || trade.includes('sawyer') || trade.includes('forester') || trade.includes('lumber')) return 'char_woodcutter';
    if (trade.includes('friar') || trade.includes('vicar') || trade.includes('priest') || trade.includes('monk') || trade.includes('cleric')) return 'char_friar';
    if (trade.includes('halberd') || trade.includes('guard') || trade.includes('watch') || trade.includes('soldier') || trade.includes('crossbow')) return 'char_guard';
    if (wealth === 'patrician' || trade.includes('merchant') || trade.includes('factor') || trade.includes('burgomaster') || rank.includes('merchant')) return 'char_merchant';
    if (c.gender === 'female') return 'char_townswoman';
    if (wealth === 'plebeian' || trade.includes('farmer') || trade.includes('peasant') || trade.includes('scythe')) return 'char_farmer';

    return 'char_carpenter';
  }

  /** Debug: stand the first n citizens of an archetype in a row at the view centre,
   *  three-quarter facing the camera, idle or working. Pause the sim first. */
  public lineup(citizens: Citizen[], archetype: string, n: number, mode: 'idle' | 'work' | 'walk'): number {
    const camYaw = this.currentRotationAngle + Math.PI / 4;
    const rx = Math.cos(camYaw), rz = -Math.sin(camYaw); // screen right on the ground
    const picked = citizens.filter((c) => this.getCitizenArchetype(c) === archetype).slice(0, n);
    // Stand 1.4 m toward the camera so chest height, not the feet, is at the view centre.
    const bx = this.targetPos.x + Math.sin(camYaw) * 1.4, bz = this.targetPos.z + Math.cos(camYaw) * 1.4;
    picked.forEach((c, k) => {
      const off = (k - (picked.length - 1) / 2) * 1.1;
      c.currentX = bx + rx * off;
      c.currentZ = bz + rz * off;
      c.isMoving = false;
      c.state = mode === 'work' ? 'WORKING' : 'IDLE';
    });
    this.crowd.pose(new Set(picked.map((c) => c.id)), camYaw - 0.45, mode === 'walk');
    return picked.length;
  }

  public citizenTriangles(): number {
    return this.crowd.drawnTriangles();
  }

  public updateCitizens(citizens: Citizen[], dt: number): void {
    this.camera.updateMatrixWorld();
    this.crowd.update(citizens, (c) => this.getCitizenArchetype(c), dt, performance.now() * 0.001, this.camera);
  }

  public updateCamera(dt: number): void {
    // Follow citizen if tracking is active
    if (this.followingCitizen) {
      this.targetPos.x = this.followingCitizen.currentX ?? this.targetPos.x;
      this.targetPos.z = this.followingCitizen.currentZ ?? this.targetPos.z;
    }

    // Smooth camera center lerping
    this.currentPos.lerp(this.targetPos, Math.min(1.0, dt * 8.0));
    this.zoom += (this.targetZoom - this.zoom) * Math.min(1.0, dt * 10.0);

    // Smooth rotation angle lerping
    let diff = this.targetRotationAngle - this.currentRotationAngle;
    while (diff < -Math.PI) diff += Math.PI * 2;
    while (diff > Math.PI) diff -= Math.PI * 2;
    this.currentRotationAngle += diff * Math.min(1.0, dt * 8.0);

    this.updateCameraTransform();
  }

  private updateCameraTransform(): void {
    const aspect = this.canvas.clientWidth / this.canvas.clientHeight || 16 / 9;
    this.camera.left = -this.zoom * aspect * 0.5;
    this.camera.right = this.zoom * aspect * 0.5;
    this.camera.top = this.zoom * 0.5;
    this.camera.bottom = -this.zoom * 0.5;
    this.camera.updateProjectionMatrix();

    // Classic 35.264° true isometric / 30° dimetric projection
    const isoDist = 120.0;
    const yaw = this.currentRotationAngle + Math.PI / 4;
    const pitch = 0.615479; // ~35.264°

    const camX = this.currentPos.x + Math.sin(yaw) * Math.cos(pitch) * isoDist;
    const camY = this.currentPos.y + Math.sin(pitch) * isoDist;
    const camZ = this.currentPos.z + Math.cos(yaw) * Math.cos(pitch) * isoDist;

    this.camera.position.set(camX, camY, camZ);
    this.camera.lookAt(this.currentPos);

    // Sun is fixed RELATIVE TO THE VIEW (style guide: every view shares one light angle,
    // key light top-left at 45 deg). It used to sit at a fixed world offset only ~8 deg
    // from behind the camera, which lit every visible face alike and hid all shadows.
    // Here: from screen-left, swung SUN_SWING toward the far side, SUN_ELEVATION up, so
    // left-facing walls are lit, right-facing walls shaded, shadows fall to the right.
    const SUN_SWING = THREE.MathUtils.degToRad(15);
    const SUN_ELEVATION = THREE.MathUtils.degToRad(45);
    const SUN_DIST = 150;
    const leftX = -Math.cos(yaw), leftZ = Math.sin(yaw);     // screen-left on the ground
    const farX = -Math.sin(yaw), farZ = -Math.cos(yaw);      // away from the camera
    const hx = leftX * Math.cos(SUN_SWING) + farX * Math.sin(SUN_SWING);
    const hz = leftZ * Math.cos(SUN_SWING) + farZ * Math.sin(SUN_SWING);
    const horiz = Math.cos(SUN_ELEVATION) * SUN_DIST;
    this.dirLight.position.set(
      this.currentPos.x + hx * horiz,
      this.currentPos.y + Math.sin(SUN_ELEVATION) * SUN_DIST,
      this.currentPos.z + hz * horiz
    );
    this.dirLight.target.position.copy(this.currentPos);
  }

  public setRotationQuadrant(q: number): void {
    this.rotationQuadrant = ((q % 4) + 4) % 4;
    this.targetRotationAngle = (this.rotationQuadrant * Math.PI) / 2;
  }

  public rotateClockwise(): void {
    this.setRotationQuadrant(this.rotationQuadrant + 1);
  }

  public rotateCounterClockwise(): void {
    this.setRotationQuadrant(this.rotationQuadrant - 1);
  }

  public rotateByAngle(deltaRad: number): void {
    this.targetRotationAngle += deltaRad;
    let norm = ((this.targetRotationAngle % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
    this.rotationQuadrant = Math.round(norm / (Math.PI / 2)) % 4;
  }

  public snapRotationToNearestQuadrant(): void {
    let norm = ((this.targetRotationAngle % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
    this.rotationQuadrant = Math.round(norm / (Math.PI / 2)) % 4;
    this.targetRotationAngle = this.rotationQuadrant * (Math.PI / 2);
  }

  public panBy(dx: number, dy: number): void {
    this.followingCitizen = null; // Break follow tracking on manual pan
    const invZoom = this.zoom / this.canvas.clientHeight;
    const yaw = this.currentRotationAngle;
    const cosY = Math.cos(yaw);
    const sinY = Math.sin(yaw);

    // Unproject delta screen coordinates
    const wx = (dx * cosY + dy * sinY) * invZoom * 1.5;
    const wz = (-dx * sinY + dy * cosY) * invZoom * 1.5;

    this.targetPos.x += wx;
    this.targetPos.z += wz;
  }

  public zoomBy(factor: number): void {
    this.targetZoom = Math.max(8.0, Math.min(90.0, this.targetZoom * factor));
  }

  public jumpTo(x: number, z: number, zoomLevel?: number): void {
    this.followingCitizen = null;
    this.targetPos.set(x, 0, z);
    if (zoomLevel) this.targetZoom = zoomLevel;
  }

  /** Jump without the lerp (debug hook / screenshots). quadrant: 0=SW 1=NW 2=NE 3=SE. */
  public snapTo(x: number, z: number, zoomLevel?: number, quadrant?: number): void {
    this.jumpTo(x, z, zoomLevel);
    if (quadrant !== undefined) this.setRotationQuadrant(quadrant);
    this.currentPos.copy(this.targetPos);
    this.zoom = this.targetZoom;
    this.currentRotationAngle = this.targetRotationAngle;
    this.updateCameraTransform();
  }

  /** World positions of every placed instance of a model, in placement order. */
  public findInstances(model: string): { x: number; z: number; parcelId?: string }[] {
    return this.scene.children
      .filter((c) => c.name === model)
      .map((c) => ({ x: c.position.x, z: c.position.z, parcelId: c.userData?.parcelId }));
  }

  public updateDayNightLighting(hour: number): void {
    const preset =
      hour >= 5 && hour < 8 ? LIGHT_PRESETS.dawn
      : hour >= 8 && hour < 17 ? LIGHT_PRESETS.noon
      : hour >= 17 && hour < 21 ? LIGHT_PRESETS.dusk
      : LIGHT_PRESETS.night;
    if (preset !== this.activePreset) this.applyLightPreset(preset);
  }

  private activePreset: LightPreset | null = null;

  private applyLightPreset(p: LightPreset): void {
    this.activePreset = p;
    this.dirLight.color.setHex(p.sun);
    this.dirLight.intensity = p.sunI;
    this.hemiLight.color.setHex(p.sky);
    this.hemiLight.groundColor.setHex(p.ground);
    this.hemiLight.intensity = p.hemiI;
    this.ambientLight.color.setHex(p.amb);
    this.ambientLight.intensity = p.ambI;
    this.scene.background = new THREE.Color(p.bg);
  }

  public triggerSpeechBubble(citizenId: string, text: string, x: number, z: number): void {
    this.activeBubbles.push({
      id: citizenId,
      text,
      x,
      y: 2.2,
      z,
      timer: 4.5 // seconds
    });
  }

  public updateSpeechBubbles(dt: number): void {
    for (let i = this.activeBubbles.length - 1; i >= 0; i--) {
      this.activeBubbles[i].timer -= dt;
      if (this.activeBubbles[i].timer <= 0) {
        this.activeBubbles.splice(i, 1);
      }
    }
  }

  /**
   * Project 3D world position to 2D canvas screen coordinate
   */
  public worldToScreen(wx: number, wy: number, wz: number): { x: number; y: number } {
    const v = new THREE.Vector3(wx, wy, wz);
    v.project(this.camera);
    const x = (v.x * 0.5 + 0.5) * this.canvas.clientWidth;
    const y = (-(v.y * 0.5) + 0.5) * this.canvas.clientHeight;
    return { x, y };
  }

  /**
   * Unproject 2D screen coordinate to 3D world position on the ground plane (y = 0)
   */
  public screenToGround(screenX: number, screenY: number): THREE.Vector3 | null {
    const rect = this.canvas.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return null;
    this.ndcVec.x = ((screenX - rect.left) / rect.width) * 2 - 1;
    this.ndcVec.y = -(((screenY - rect.top) / rect.height) * 2 - 1);
    this.raycaster.setFromCamera(this.ndcVec, this.camera);
    const intersection = new THREE.Vector3();
    const hit = this.raycaster.ray.intersectPlane(this.groundPlaneMath, intersection);
    return hit ? intersection : null;
  }

  public render(): void {
    this.renderer.render(this.scene, this.camera);
  }

  public resize(width: number, height: number): void {
    const isMobile = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0) || window.innerWidth < 768;
    const maxDpr = isMobile ? 1.5 : 2.0;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, maxDpr));
    this.renderer.setSize(width, height, false);
    this.updateCameraTransform();
  }
}
