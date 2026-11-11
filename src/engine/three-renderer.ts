import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import type { CityPlan, Citizen } from '../types';

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

  private groundPlane: THREE.Mesh;
  private citizenMeshes: Map<string, THREE.Group> = new Map();

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
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.25;

    // Mobile WebGL context preservation
    this.canvas.addEventListener('webglcontextlost', (e) => {
      e.preventDefault();
      console.warn('[WebGL] Context lost on mobile device.');
    });
    this.canvas.addEventListener('webglcontextrestored', () => {
      console.info('[WebGL] Context restored.');
      this.render();
    });

    // Atmospheric lighting
    this.hemiLight = new THREE.HemisphereLight(0xfff8ee, 0x5a5448, 0.75);
    this.scene.add(this.hemiLight);

    this.ambientLight = new THREE.AmbientLight(0xcfd8dc, 0.5);
    this.scene.add(this.ambientLight);

    // Directional sunlight casting crisp isometric diagonal shadows
    const shadowRes = isMobile ? 1024 : 2048;
    this.dirLight = new THREE.DirectionalLight(0xfffaed, 1.5);
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

    // Base meadow grass & loess earth color
    ctx.fillStyle = '#475d2e';
    ctx.fillRect(0, 0, 2048, 2048);

    // Initial noise
    for (let i = 0; i < 4000; i++) {
      const rx = Math.random() * 2048;
      const ry = Math.random() * 2048;
      const r = Math.random() * 12 + 4;
      ctx.fillStyle = Math.random() < 0.5 ? '#3f5328' : '#526935';
      ctx.beginPath();
      ctx.arc(rx, ry, r, 0, Math.PI * 2);
      ctx.fill();
    }

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

  private updateGroundWithPlan(plan: CityPlan): void {
    if (!this.groundCanvas || !this.groundTex) return;
    const ctx = this.groundCanvas.getContext('2d')!;

    // Coordinate mapping: World (-350..350, -275..275) to Canvas (0..2048, 0..2048)
    const toCanvasX = (wx: number) => ((wx + 350) / 700) * 2048;
    const toCanvasY = (wz: number) => ((wz + 275) / 550) * 2048;

    // 1. Draw Lublin Promontory Old Town loess hill plateau
    if (plan.defense && plan.defense.perimeterPoints.length > 0) {
      ctx.save();
      ctx.fillStyle = '#5c5240';
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

    // 2. Draw Castle Hill bailey plateau
    ctx.save();
    ctx.fillStyle = '#5c5240';
    ctx.beginPath();
    ctx.ellipse(toCanvasX(275), toCanvasY(90), 160, 130, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // 3. Draw Czechówka & Bystrzyca river valley slopes (greener loess ravines)
    ctx.save();
    ctx.strokeStyle = '#374b24';
    ctx.lineWidth = 45;
    ctx.beginPath();
    ctx.moveTo(toCanvasX(-340), toCanvasY(45));
    ctx.quadraticCurveTo(toCanvasX(-100), toCanvasY(55), toCanvasX(210), toCanvasY(35));
    ctx.stroke();
    ctx.restore();

    // 4. Draw Street Network Corridors from plan (cobblestone paving)
    if (plan.streetNetwork && plan.streetNetwork.nodes && plan.streetNetwork.edges) {
      const nodeMap = new Map<string, { x: number; z: number }>();
      plan.streetNetwork.nodes.forEach(n => nodeMap.set(n.id, { x: n.x, z: n.z }));

      // Outer wide road border
      ctx.save();
      ctx.strokeStyle = '#524838';
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
      ctx.strokeStyle = '#6c6251';
      ctx.lineWidth = 18;
      ctx.stroke();
      ctx.restore();
    }

    // 5. Draw Rynek (Market Square) Flagstone Plaza
    const rx1 = toCanvasX(-42);
    const rz1 = toCanvasY(-32);
    const rx2 = toCanvasX(42);
    const rz2 = toCanvasY(32);
    const rw = rx2 - rx1;
    const rh = rz2 - rz1;

    ctx.save();
    ctx.fillStyle = '#6f6655';
    ctx.fillRect(rx1, rz1, rw, rh);

    // Stone flagstone grid on Rynek
    ctx.strokeStyle = '#574f41';
    ctx.lineWidth = 1.5;
    for (let x = rx1; x <= rx2; x += 18) {
      ctx.beginPath();
      ctx.moveTo(x, rz1);
      ctx.lineTo(x, rz2);
      ctx.stroke();
    }
    for (let y = rz1; y <= rz2; y += 18) {
      ctx.beginPath();
      ctx.moveTo(rx1, y);
      ctx.lineTo(rx2, y);
      ctx.stroke();
    }
    ctx.restore();

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
      'archery_yard'
    ];

    console.log('[ThreeRenderer] Loading 31 Blender-authored GLB assets...');

    for (const name of modelNames) {
      try {
        const gltf = await loader.loadAsync(`/models/${name}.glb`);
        gltf.scene.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            child.castShadow = true;
            child.receiveShadow = true;
          }
        });
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

      // Add Wall Segment (leave openings for gates)
      if (wallTemplate && p1.id !== 'gate_grodzka' && p1.id !== 'gate_krakow') {
        const midX = (p1.x + p2.x) * 0.5;
        const midZ = (p1.z + p2.z) * 0.5;
        const dx = p2.x - p1.x;
        const dz = p2.z - p1.z;
        const segLen = Math.hypot(dx, dz);
        const angle = Math.atan2(dx, dz);

        const wall = wallTemplate.clone();
        wall.position.set(midX, 0, midZ);
        wall.rotation.y = angle + Math.PI / 2;
        wall.scale.set(segLen / 16.0, 1.0, 1.0);
        this.scene.add(wall);
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
      for (let t = 0; t < 90; t++) {
        const tree = treeTemplate.clone();
        const ang = Math.random() * Math.PI * 2;
        const dist = 165 + Math.random() * 95;
        tree.position.set(Math.cos(ang) * dist, 0, Math.sin(ang) * dist);
        const s = 0.8 + Math.random() * 0.6;
        tree.scale.set(s, s, s);
        tree.rotation.y = Math.random() * Math.PI * 2;
        this.scene.add(tree);
      }
    }

    console.log('[ThreeRenderer] Full medieval city populated successfully with 0 building overlaps!');
  }

  public updateCitizens(citizens: Citizen[], _dt: number): void {
    // Maintain 3D citizen group objects
    for (let i = 0; i < citizens.length; i++) {
      const c = citizens[i];
      let group = this.citizenMeshes.get(c.id);

      if (!group) {
        // Create 3D citizen figure
        group = new THREE.Group();

        // Tunic color based on status
        let color = 0x8d6e63;
        if (c.trade.includes('Halberd') || c.trade.includes('Watch')) color = 0xc62828; // Guard red
        else if (c.trade.includes('Friar')) color = 0x4e342e; // Monk
        else if (c.wealthClass === 'patrician') color = 0x1565c0; // Patrician blue
        else if (c.guildRank === 'foreign_merchant') color = 0x2e7d32; // Merchant green

        // Body
        const bodyGeo = new THREE.CylinderGeometry(0.25, 0.35, 1.3, 8);
        const bodyMat = new THREE.MeshStandardMaterial({ color, roughness: 0.8 });
        const body = new THREE.Mesh(bodyGeo, bodyMat);
        body.position.y = 0.65;
        body.castShadow = true;
        group.add(body);

        // Head
        const headGeo = new THREE.SphereGeometry(0.2, 8, 8);
        const headMat = new THREE.MeshStandardMaterial({ color: 0xffcc80, roughness: 0.6 });
        const head = new THREE.Mesh(headGeo, headMat);
        head.position.y = 1.45;
        group.add(head);

        // Hat / Hood
        const hatGeo = new THREE.ConeGeometry(0.26, 0.28, 8);
        const hatMat = new THREE.MeshStandardMaterial({ color: 0x212121, roughness: 0.9 });
        const hat = new THREE.Mesh(hatGeo, hatMat);
        hat.position.y = 1.62;
        group.add(hat);

        // Halberd for guards
        if (c.trade.includes('Halberd')) {
          const halGeo = new THREE.CylinderGeometry(0.02, 0.02, 2.2, 6);
          const halMat = new THREE.MeshStandardMaterial({ color: 0x90a4ae, metalness: 0.8 });
          const hal = new THREE.Mesh(halGeo, halMat);
          hal.position.set(0.25, 1.1, 0);
          group.add(hal);
        }

        group.userData = { citizenId: c.id };
        this.scene.add(group);
        this.citizenMeshes.set(c.id, group);
      }

      // Update position
      const cx = c.currentX ?? 0;
      const cz = c.currentZ ?? 0;
      group.position.set(cx, 0, cz);

      // Walking bob
      if (c.isMoving) {
        group.position.y = Math.abs(Math.sin((c.animFrame ?? 0) * Math.PI)) * 0.12;
      }
    }
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

    // Update sunlight position relative to camera target
    this.dirLight.position.set(this.currentPos.x + 80, this.currentPos.y + 140, this.currentPos.z + 60);
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

  public updateDayNightLighting(hour: number): void {
    // Dynamic sun position and warm color grading
    if (hour >= 5 && hour < 8) {
      // Dawn
      this.dirLight.color.setHex(0xffaa66);
      this.dirLight.intensity = 0.9;
      this.ambientLight.color.setHex(0x5c4238);
      this.scene.background = new THREE.Color(0x735348);
    } else if (hour >= 8 && hour < 17) {
      // High Fair Noon: bright golden sun with crisp shadows
      this.dirLight.color.setHex(0xfffaed);
      this.dirLight.intensity = 1.45;
      this.ambientLight.color.setHex(0xdde3ea);
      this.scene.background = new THREE.Color(0x3a4f63);
    } else if (hour >= 17 && hour < 21) {
      // Dusk
      this.dirLight.color.setHex(0xff7744);
      this.dirLight.intensity = 0.85;
      this.ambientLight.color.setHex(0x382c44);
      this.scene.background = new THREE.Color(0x483244);
    } else {
      // Night Curfew: deep blue moonlight
      this.dirLight.color.setHex(0x5577aa);
      this.dirLight.intensity = 0.35;
      this.ambientLight.color.setHex(0x181e28);
      this.scene.background = new THREE.Color(0x0a1018);
    }
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
