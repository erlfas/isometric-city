import type { CityPlan, Citizen } from './types';
import { ThreeIsometricRenderer } from './engine/three-renderer';
import { SpatialHashGrid } from './engine/spatial-hash';
import { SimulationEngine } from './engine/simulation';
import { NavGrid } from './engine/nav-grid';
import { BuildingIndex } from './engine/building-anchors';
import { Soundscape, type Listener } from './engine/audio';
import { UIController } from './ui/inspector';
import { IsometricCamera } from './engine/camera';
import { TouchGestureManager } from './engine/touch';

async function bootstrap() {
  console.log('[Lublin 1392] Bootstrapping high-fidelity 3D medieval city simulation...');

  // 1. Fetch decoupled city plan IR
  const response = await fetch('/city_plan.json');
  if (!response.ok) {
    throw new Error(`Failed to load city_plan.json: ${response.statusText}`);
  }
  const plan: CityPlan = await response.json();

  // 2. Setup Canvases
  const webglCanvas = document.getElementById('webgl-canvas') as HTMLCanvasElement;
  const overlayCanvas = document.getElementById('overlay-canvas') as HTMLCanvasElement;
  const overlayCtx = overlayCanvas.getContext('2d')!;

  // 3. Initialize Three.js Isometric Renderer
  const threeRenderer = new ThreeIsometricRenderer(webglCanvas);

  // Show loading indicator
  const tickerEl = document.getElementById('event-ticker-text');
  if (tickerEl) tickerEl.textContent = 'Loading 31 Blender-compiled 3D GLB models into GPU memory...';

  // Load all 31 Blender-authored GLB assets
  await threeRenderer.loadAllModels();

  // Populate city scene with Town Hall, Cloth Hall, Market Stalls, Curtain Walls, 580 Parcels, and Trees
  threeRenderer.populateCityScene(plan);

  if (tickerEl) {
    tickerEl.textContent = 'King Władysław II Jagiełło confirms the royal fair privileges. Over 1,500 burghers and foreign merchants gather at the Market Square.';
  }

  // 4. Initialize Simulation & Audio Engines
  const spatialGrid = new SpatialHashGrid(24.0);
  const placed = threeRenderer.placedModels();
  const buildings = new BuildingIndex(placed);
  threeRenderer.setBuildings(buildings.all);
  // Ground plane is 700 x 550 m around the origin; seed the market square as open ground too.
  const nav = new NavGrid(-350, -275, 350, 275, placed, [...buildings.seeds(), { x: -15.5, z: -25.5 }]);
  console.log(`[Lublin 1392] Navigation grid ${nav.w}x${nav.h} built in ${nav.buildMs.toFixed(0)} ms (${buildings.all.length} buildings with doors/spots).`);
  const sim = new SimulationEngine(plan, spatialGrid, nav, buildings);
  const audio = new Soundscape();
  audio.configure(plan);
  const listener: Listener = {
    x: 0, z: 0, zoom: 40,
    pan: (x, z) => (threeRenderer.worldToScreen(x, 0, z).x / webglCanvas.clientWidth) * 2 - 1,
  };

  // Dummy fallback camera for UIController
  const dummyCamera = new IsometricCamera(window.innerWidth, window.innerHeight);
  const ui = new UIController(sim, dummyCamera);
  ui.onFollowToggle = (c) => {
    threeRenderer.followingCitizen = c;
  };

  // Bell Toll notification binding
  sim.onBellToll = (bellName: string, hour: number) => {
    audio.tollHour(hour);
    ui.showEventNotification(`🔔 Church Bells Toll: ${bellName} — All burghers proceed according to civic duty.`);
  };

  sim.onDoor = (d, opening) => audio.door(d.x, d.z, opening);

  // Systemic Fair Event notification binding
  sim.onEventTriggered = (event) => {
    audio.herald();
    ui.showEventNotification(`📜 [Royal Fair Event] ${event.name}: ${event.description}`);
  };

  // Audio Toggle (Desktop & Mobile buttons)
  const audioBtn = document.getElementById('btn-audio-mute');
  const mobileAudioBtn = document.getElementById('btn-mobile-audio');
  const musicBtns = [document.getElementById('btn-music'), document.getElementById('btn-mobile-music')];
  const showAudioState = () => {
    const muted = audio.isMuted;
    if (audioBtn) {
      audioBtn.textContent = muted ? '🔇 Muted' : '🔊 Sound';
      audioBtn.classList.toggle('active', !muted);
    }
    if (mobileAudioBtn) {
      mobileAudioBtn.textContent = muted ? '🔇' : '🔊';
      mobileAudioBtn.classList.toggle('active', !muted);
    }
    for (const b of musicBtns) b?.classList.toggle('active', audio.musicOn && !muted);
  };
  const toggleAudio = () => { audio.toggleMute(); showAudioState(); };
  const toggleMusic = () => { audio.toggleMusic(); showAudioState(); };
  audioBtn?.addEventListener('click', toggleAudio);
  mobileAudioBtn?.addEventListener('click', toggleAudio);
  for (const b of musicBtns) b?.addEventListener('click', toggleMusic);
  showAudioState();

  // Initial speech bubbles (matching images 3 & 4)
  threeRenderer.triggerSpeechBubble('b1', 'Hello, carpenter!', -12, -14);
  threeRenderer.triggerSpeechBubble('b2', 'Crossbows! They\'re shooting crossbows!', -4, 4);
  threeRenderer.triggerSpeechBubble('b3', 'Town watch! Halt, you villains!', 6, 8);

  // Setup periodic medieval dialogue shouts (matching images 3 & 4)
  const medievalBarks = [
    'Hello, carpenter!',
    'Fine Flemish broadcloth here!',
    'Tokaji wine fresh from Hungary!',
    'Crossbows! They\'re shooting crossbows!',
    'Run!',
    'You want me? Come on, then!',
    'Murderers on the square!',
    'Town watch! Halt, you villains!',
    'Smoked herring and Baltic amber!',
    'God give you good day, master smith!',
    'Praise King Jagiełło for this fair!'
  ];

  window.setInterval(() => {
    if (sim.citizens.length === 0) return;
    const randCit = sim.citizens[Math.floor(Math.random() * sim.citizens.length)];
    const text = medievalBarks[Math.floor(Math.random() * medievalBarks.length)];
    threeRenderer.triggerSpeechBubble(randCit.id, text, randCit.currentX ?? 0, randCit.currentZ ?? 0);
    audio.voice(randCit.currentX ?? 0, randCit.currentZ ?? 0, randCit.gender === 'female');
  }, 3800);

  // Resize handler
  function handleResize() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    overlayCanvas.width = w * dpr;
    overlayCanvas.height = h * dpr;
    overlayCanvas.style.width = `${w}px`;
    overlayCanvas.style.height = `${h}px`;
    overlayCtx.scale(dpr, dpr);

    threeRenderer.resize(w, h);
  }
  window.addEventListener('resize', handleResize);
  handleResize();

  // -------------------------------------------------------------
  // Touch Gestures & Pointer Interaction (Mobile + Desktop)
  // -------------------------------------------------------------
  const viewportContainer = document.getElementById('viewport-container') || webglCanvas;

  function handleSelection(screenX: number, screenY: number) {
    audio.init();
    const rect = webglCanvas.getBoundingClientRect();
    const mouseX = screenX - rect.left;
    const mouseY = screenY - rect.top;

    // 1. Check if tapped on a citizen (touch tolerance radius 36px)
    let closestCit: any = null;
    let closestDist = 36; // pixels

    for (let i = 0; i < sim.citizens.length; i++) {
      const c = sim.citizens[i];
      const sp = threeRenderer.worldToScreen(c.currentX ?? 0, 1.2, c.currentZ ?? 0);
      const dist = Math.hypot(sp.x - mouseX, sp.y - mouseY);
      if (dist < closestDist) {
        closestDist = dist;
        closestCit = c;
      }
    }

    if (closestCit) {
      threeRenderer.hoveredCitizen = closestCit;
      ui.inspectCitizen(closestCit);
      if ('vibrate' in navigator) navigator.vibrate?.(15);
      return;
    }

    // 2. A building under the pointer: look inside (tap it again to close it), inspect its parcel.
    //    Otherwise raycast to the ground plane for parcel picking.
    const picked = threeRenderer.pickBuilding(screenX, screenY, sim.buildings.all);
    // Tapping the open building again goes up a storey, and closes it from the top one.
    const storeys = picked?.interior?.rooms.length ?? 1;
    if (picked && picked === threeRenderer.peek && threeRenderer.peekStorey + 1 < storeys) threeRenderer.peekStorey++;
    else {
      threeRenderer.peek = picked && picked !== threeRenderer.peek ? picked : null;
      threeRenderer.peekStorey = 0;
    }
    const groundHit = threeRenderer.screenToGround(screenX, screenY);
    if (picked || groundHit) {
      const hitParcel = (picked?.parcelId ? sim.parcelMap.get(picked.parcelId) : undefined)
        ?? (groundHit ? spatialGrid.findParcelAt(groundHit.x, groundHit.z) : null);
      if (hitParcel) {
        threeRenderer.hoveredCitizen = null;
        ui.inspectParcel(hitParcel);
        if ('vibrate' in navigator) navigator.vibrate?.(10);
        return;
      }
    }

    // 3. Tapped empty ground
    ui.closeInspector();
    threeRenderer.hoveredCitizen = null;
  }

  function handleDoubleTap(screenX: number, screenY: number) {
    const groundHit = threeRenderer.screenToGround(screenX, screenY);
    if (groundHit) {
      // Smoothly focus on tapped ground point and zoom in
      threeRenderer.jumpTo(groundHit.x, groundHit.z, Math.max(16.0, threeRenderer.targetZoom * 0.75));
      if ('vibrate' in navigator) navigator.vibrate?.(25);
    }
  }

  // Initialize unified TouchGestureManager for single/multi-touch and clicks
  new TouchGestureManager(viewportContainer, {
    onPan: (dx, dy) => {
      threeRenderer.panBy(-dx, -dy);
    },
    onPinch: (factor) => {
      threeRenderer.zoomBy(factor);
    },
    onRotateAngle: (deltaRad) => {
      threeRenderer.rotateByAngle(deltaRad);
      updateCompassUI();
    },
    onRotateStep: (dir) => {
      if (dir > 0) threeRenderer.rotateClockwise();
      else threeRenderer.rotateCounterClockwise();
      updateCompassUI();
      if ('vibrate' in navigator) navigator.vibrate?.(12);
    },
    onTap: (screenX, screenY) => {
      handleSelection(screenX, screenY);
    },
    onDoubleTap: (screenX, screenY) => {
      handleDoubleTap(screenX, screenY);
    },
    onInteractionStart: () => {
      audio.init();
    }
  });

  // Desktop hover check (only when using a mouse pointer)
  const mouse = { x: 0, y: 0 };
  window.addEventListener('pointermove', (e) => {
    if (e.pointerType !== 'mouse') return;
    mouse.x = e.clientX; mouse.y = e.clientY;
    const rect = webglCanvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    let closestCit: any = null;
    let closestDist = 28; // pixels

    for (let i = 0; i < sim.citizens.length; i++) {
      const c = sim.citizens[i];
      const sp = threeRenderer.worldToScreen(c.currentX ?? 0, 1.2, c.currentZ ?? 0);
      const dist = Math.hypot(sp.x - mouseX, sp.y - mouseY);
      if (dist < closestDist) {
        closestDist = dist;
        closestCit = c;
      }
    }
    threeRenderer.hoveredCitizen = closestCit;
  });

  // Wheel zoom for mouse
  window.addEventListener('wheel', (e) => {
    const target = e.target as HTMLElement;
    if (target.tagName !== 'CANVAS' && target.id !== 'viewport-container') return;
    const factor = e.deltaY < 0 ? 0.9 : 1.11;
    threeRenderer.zoomBy(factor);
  }, { passive: true });

  // Camera buttons
  document.getElementById('btn-rotate-cw')?.addEventListener('click', () => {
    threeRenderer.rotateClockwise();
    updateCompassUI();
    if ('vibrate' in navigator) navigator.vibrate?.(10);
  });
  document.getElementById('btn-rotate-ccw')?.addEventListener('click', () => {
    threeRenderer.rotateCounterClockwise();
    updateCompassUI();
    if ('vibrate' in navigator) navigator.vibrate?.(10);
  });
  document.getElementById('btn-zoom-in')?.addEventListener('click', () => {
    threeRenderer.zoomBy(0.8);
    if ('vibrate' in navigator) navigator.vibrate?.(10);
  });
  document.getElementById('btn-zoom-out')?.addEventListener('click', () => {
    threeRenderer.zoomBy(1.25);
    if ('vibrate' in navigator) navigator.vibrate?.(10);
  });
  document.getElementById('btn-recenter')?.addEventListener('click', () => {
    threeRenderer.jumpTo(0, 0, 24);
    if ('vibrate' in navigator) navigator.vibrate?.(15);
  });

  function updateCompassUI() {
    const headings = ['SW (Kraków Rd)', 'NW (Czechówka Valley)', 'NE (Castle Hill)', 'SE (Bystrzyca)'];
    const el = document.getElementById('compass-heading');
    if (el) el.textContent = headings[threeRenderer.rotationQuadrant];
  }

  // Landmark Quick Jumps
  document.querySelectorAll('[data-landmark]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const landmark = (e.currentTarget as HTMLElement).getAttribute('data-landmark');
      if (landmark === 'rynek') threeRenderer.jumpTo(0, 0, 24);
      else if (landmark === 'krakow_gate') threeRenderer.jumpTo(-160, -80, 28);
      else if (landmark === 'grodzka_gate') threeRenderer.jumpTo(190, 20, 28);
      else if (landmark === 'castle') threeRenderer.jumpTo(275, 85, 32);
      else if (landmark === 'workshop') threeRenderer.jumpTo(-235, -120, 22);
      if ('vibrate' in navigator) navigator.vibrate?.(12);
    });
  });

  // Keyboard navigation
  window.addEventListener('keydown', (e) => {
    const panStep = threeRenderer.zoom * 0.4;
    if (e.key === 'w' || e.key === 'W' || e.key === 'ArrowUp') threeRenderer.panBy(0, -panStep);
    else if (e.key === 's' || e.key === 'S' || e.key === 'ArrowDown') threeRenderer.panBy(0, panStep);
    else if (e.key === 'a' || e.key === 'A' || e.key === 'ArrowLeft') threeRenderer.panBy(-panStep, 0);
    else if (e.key === 'd' || e.key === 'D' || e.key === 'ArrowRight') threeRenderer.panBy(panStep, 0);
    else if (e.key === 'q' || e.key === 'Q') { threeRenderer.rotateCounterClockwise(); updateCompassUI(); }
    else if (e.key === 'e' || e.key === 'E') { threeRenderer.rotateClockwise(); updateCompassUI(); }
    else if (e.key === ' ') sim.togglePause();
    else if ((e.key === 'c' || e.key === 'C') && !e.repeat) {
      // Hold C: look into the building under the mouse.
      threeRenderer.peek = threeRenderer.pickBuilding(mouse.x, mouse.y, sim.buildings.all);
      peekByKey = true;
    }
  });
  let peekByKey = false;
  window.addEventListener('keyup', (e) => {
    if ((e.key === 'c' || e.key === 'C') && peekByKey) { threeRenderer.peek = null; peekByKey = false; }
  });

  // Main Loop
  let lastTime = performance.now();
  const shownInside: Citizen[] = [];
  const awake = new Set<number>();
  let windowsT = 0;

  function animate(now: number) {
    const dt = Math.min((now - lastTime) / 1000.0, 0.1);
    lastTime = now;

    // 1. Update Simulation
    sim.update(dt);

    // 2. Update Three.js camera & lighting
    threeRenderer.updateCamera(dt);
    threeRenderer.updateDayNightLighting(sim.simTimeHours);
    // Cutaway: the followed citizen's building (or the peeked one) opens up, and the people
    // inside it - hidden while indoors - are drawn for this frame.
    const followed = threeRenderer.followingCitizen;
    const inside = followed ? sim.insideOf(followed) : null;
    threeRenderer.updateCutaway(dt, inside);
    const room = inside?.b ?? threeRenderer.peek;
    shownInside.length = 0;
    if (room) sim.occupants(room, shownInside);
    // Only the open storey and those below (people upstairs would float above the cut walls).
    for (let k = shownInside.length - 1; k >= 0; k--) {
      if ((shownInside[k].y ?? 0) > threeRenderer.cutY - 0.5) shownInside.splice(k, 1);
    }
    for (const c of shownInside) c.hidden = false;
    threeRenderer.updateCitizens(sim.citizens, dt);
    for (const c of shownInside) c.hidden = true;
    threeRenderer.updateDoors(sim.activeDoors, sim.simTimeHours);
    windowsT -= dt;
    if (windowsT <= 0) {
      windowsT = 0.5;
      threeRenderer.updateWindows(sim.awakeInside(awake), sim.simTimeHours);
    }
    threeRenderer.updateSpeechBubbles(dt);
    listener.x = threeRenderer.targetPos.x;
    listener.z = threeRenderer.targetPos.z;
    listener.zoom = threeRenderer.zoom;
    audio.update(listener, sim.simTimeHours, sim.citizens);

    // 3. Render 3D Scene with PCF soft shadows
    threeRenderer.render();

    // 4. Render 2.5D Speech Bubbles and Hover Prompt on Overlay Canvas
    renderOverlayUI(overlayCtx, threeRenderer);

    // 5. Update HUD
    ui.updateHUD();

    requestAnimationFrame(animate);
  }

  function renderOverlayUI(ctx: CanvasRenderingContext2D, renderer: ThreeIsometricRenderer) {
    ctx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

    // Render Speech Bubbles (exact styling from images 3 & 4)
    for (let i = 0; i < renderer.activeBubbles.length; i++) {
      const b = renderer.activeBubbles[i];
      const sp = renderer.worldToScreen(b.x, b.y, b.z);

      ctx.save();
      ctx.font = 'bold 12px sans-serif';
      const textWidth = ctx.measureText(b.text).width;
      const padX = 10;
      const bw = textWidth + padX * 2;
      const bh = 22;
      const bx = sp.x - bw * 0.5;
      const by = sp.y - 28;

      // Dark brown speech bubble background with golden border
      ctx.fillStyle = 'rgba(26, 18, 12, 0.92)';
      ctx.strokeStyle = '#c5a059';
      ctx.lineWidth = 1.5;

      ctx.beginPath();
      ctx.roundRect(bx, by, bw, bh, 4);
      ctx.fill();
      ctx.stroke();

      // Tail pointer
      ctx.beginPath();
      ctx.moveTo(sp.x - 4, by + bh);
      ctx.lineTo(sp.x, by + bh + 5);
      ctx.lineTo(sp.x + 4, by + bh);
      ctx.fill();
      ctx.stroke();

      // Text
      ctx.fillStyle = '#f8f4e6';
      ctx.textAlign = 'center';
      ctx.fillText(b.text, sp.x, by + 15);
      ctx.restore();
    }

    // Render Hover Interaction Prompt (matching image 3 & 4: "[E] Stach z Ponikwody, visitor to the fair")
    if (renderer.hoveredCitizen) {
      const c = renderer.hoveredCitizen;
      const sp = renderer.worldToScreen(c.currentX ?? 0, 1.8, c.currentZ ?? 0);

      ctx.save();
      // Draw indicator circle under feet
      ctx.strokeStyle = '#ffd700';
      ctx.lineWidth = 2;
      const groundPos = renderer.worldToScreen(c.currentX ?? 0, 0.05, c.currentZ ?? 0);
      ctx.beginPath();
      ctx.ellipse(groundPos.x, groundPos.y, 14, 7, 0, 0, Math.PI * 2);
      ctx.stroke();

      // Draw bottom pill prompt: [E] Name, trade
      const labelText = `[E] ${c.name}, ${c.trade.toLowerCase()}`;
      ctx.font = '600 13px serif';
      const tw = ctx.measureText(labelText).width;
      const pw = tw + 20;
      const ph = 26;
      const px = sp.x - pw * 0.5;
      const py = sp.y - 35;

      ctx.fillStyle = 'rgba(15, 12, 10, 0.95)';
      ctx.strokeStyle = '#e6be60';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.roundRect(px, py, pw, ph, 4);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = '#ffffff';
      ctx.textAlign = 'center';
      ctx.fillText(labelText, sp.x, py + 18);
      ctx.restore();
    }
  }

  requestAnimationFrame(animate);
  if (import.meta.env.DEV) {
    const { installDebugHooks } = await import('./debug-hooks');
    installDebugHooks(threeRenderer, sim, audio);
  }
  console.log('[Lublin 1392] High-fidelity simulation running with Blender 3D assets & soft shadows!');
}

window.addEventListener('DOMContentLoaded', bootstrap);
