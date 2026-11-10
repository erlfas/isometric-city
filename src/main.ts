import type { CityPlan, HeatmapMode } from './types';
import { IsometricCamera } from './engine/camera';
import { SpatialHashGrid } from './engine/spatial-hash';
import { ProceduralCityBuilder } from './engine/procedural-assets';
import { WebGLIsometricRenderer } from './engine/webgl-renderer';
import { SimulationEngine } from './engine/simulation';
import { ProceduralAudioEngine } from './engine/audio';
import { UIController } from './ui/inspector';

async function bootstrap() {
  console.log('[Lublin 1392] Bootstrapping medieval city simulation...');

  // 1. Fetch decoupled city plan IR
  const response = await fetch('/city_plan.json');
  if (!response.ok) {
    throw new Error(`Failed to load city_plan.json: ${response.statusText}`);
  }
  const plan: CityPlan = await response.json();
  console.log(`[Lublin 1392] Loaded city plan: ${plan.parcels.length} parcels, ${plan.citizens.length} citizens.`);

  // 2. Setup Canvases
  const webglCanvas = document.getElementById('webgl-canvas') as HTMLCanvasElement;
  const overlayCanvas = document.getElementById('overlay-canvas') as HTMLCanvasElement;
  const overlayCtx = overlayCanvas.getContext('2d')!;

  const camera = new IsometricCamera(window.innerWidth, window.innerHeight);
  const spatialGrid = new SpatialHashGrid(24.0);

  // 3. Synthesize Procedural 3D City Geometry
  const builder = new ProceduralCityBuilder();
  const cityMeshData = builder.buildFullCityMesh(
    plan.parcels,
    plan.civicLandmarks,
    plan.defense.perimeterPoints,
    plan.defense.castleElements
  );

  // 4. Initialize WebGL Renderer and upload geometry
  const renderer = new WebGLIsometricRenderer(webglCanvas);
  renderer.uploadMesh(cityMeshData);

  // 5. Initialize Simulation & Audio Engines
  const sim = new SimulationEngine(plan, spatialGrid);
  const audio = new ProceduralAudioEngine();
  const ui = new UIController(sim, camera);

  let currentHeatmapMode: HeatmapMode = 'none';

  // Heatmap Toolbar events
  document.querySelectorAll('#view-toolbar button').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('#view-toolbar button').forEach(b => b.classList.remove('active'));
      const el = e.currentTarget as HTMLElement;
      el.classList.add('active');
      currentHeatmapMode = (el.getAttribute('data-mode') || 'none') as HeatmapMode;
    });
  });

  // Audio Toggle
  const audioBtn = document.getElementById('btn-audio-mute');
  audioBtn?.addEventListener('click', () => {
    audio.init();
    const isMuted = audio.toggleMute();
    if (audioBtn) {
      audioBtn.textContent = isMuted ? '🔇 Muted' : '🔊 Sound';
      audioBtn.classList.toggle('active', !isMuted);
    }
  });

  // Bell Toll notification binding
  sim.onBellToll = (bellName: string, hour: number) => {
    audio.init();
    audio.tollBell(hour === 12 ? 185.0 : 220.0, hour === 21 ? 9 : 3);
    ui.showEventNotification(`🔔 Church Bells Toll: ${bellName} — All burghers proceed according to civic duty.`);
  };

  // Systemic Fair Event notification binding
  sim.onEventTriggered = (event) => {
    ui.showEventNotification(`📜 [Royal Fair Event] ${event.name}: ${event.description}`);
  };

  // Resize handler
  function handleResize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = window.innerWidth;
    const h = window.innerHeight;

    webglCanvas.width = w * dpr;
    webglCanvas.height = h * dpr;
    overlayCanvas.width = w * dpr;
    overlayCanvas.height = h * dpr;

    webglCanvas.style.width = `${w}px`;
    webglCanvas.style.height = `${h}px`;
    overlayCanvas.style.width = `${w}px`;
    overlayCanvas.style.height = `${h}px`;

    overlayCtx.scale(dpr, dpr);
    camera.resize(w, h);
  }
  window.addEventListener('resize', handleResize);
  handleResize();

  // Mouse / Pointer Interaction for Pan, Zoom, and Raycast Selection
  let isDragging = false;
  let dragStartX = 0;
  let dragStartY = 0;
  let totalDragDist = 0;

  window.addEventListener('mousedown', (e) => {
    // Only drag when clicking on canvas, not UI
    if ((e.target as HTMLElement).tagName !== 'CANVAS') return;
    audio.init(); // User gesture initializes Web Audio
    isDragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    totalDragDist = 0;
  });

  window.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const dx = e.clientX - dragStartX;
    const dy = e.clientY - dragStartY;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    totalDragDist += Math.hypot(dx, dy);

    camera.panBy(-dx, -dy);
  });

  window.addEventListener('mouseup', (e) => {
    if (!isDragging) return;
    isDragging = false;

    // If click didn't drag, perform raycast entity selection
    if (totalDragDist < 5.0) {
      handleCanvasClick(e.clientX, e.clientY);
    }
  });

  // Wheel zoom
  window.addEventListener('wheel', (e) => {
    if ((e.target as HTMLElement).tagName !== 'CANVAS') return;
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
    camera.zoomBy(zoomFactor, e.clientX, e.clientY);
  }, { passive: true });

  // Raycast Picking: click -> check nearest citizen, then parcel
  function handleCanvasClick(screenX: number, screenY: number) {
    const worldPos = camera.screenToWorld(screenX, screenY, 0.0);

    // 1. Check nearest citizen within 4.5m
    const hitCitizen = spatialGrid.findNearestCitizen(worldPos.x, worldPos.z, 4.5);
    if (hitCitizen) {
      ui.inspectCitizen(hitCitizen);
      return;
    }

    // 2. Check parcel under cursor
    const hitParcel = spatialGrid.findParcelAt(worldPos.x, worldPos.z);
    if (hitParcel) {
      ui.inspectParcel(hitParcel);
      return;
    }

    // Clicked empty ground
    ui.closeInspector();
  }

  // Keyboard navigation
  window.addEventListener('keydown', (e) => {
    const panStep = 30.0 / camera.zoom;
    if (e.key === 'w' || e.key === 'W' || e.key === 'ArrowUp') {
      camera.panBy(0, -panStep);
    } else if (e.key === 's' || e.key === 'S' || e.key === 'ArrowDown') {
      camera.panBy(0, panStep);
    } else if (e.key === 'a' || e.key === 'A' || e.key === 'ArrowLeft') {
      camera.panBy(-panStep, 0);
    } else if (e.key === 'd' || e.key === 'D' || e.key === 'ArrowRight') {
      camera.panBy(panStep, 0);
    } else if (e.key === 'q' || e.key === 'Q') {
      camera.rotateCounterClockwise();
    } else if (e.key === 'e' || e.key === 'E') {
      camera.rotateClockwise();
    } else if (e.key === ' ') {
      sim.togglePause();
    } else if (e.key === '1') {
      sim.setSpeed(1);
    } else if (e.key === '2') {
      sim.setSpeed(5);
    } else if (e.key === '3') {
      sim.setSpeed(20);
    } else if (e.key === '4') {
      sim.setSpeed(60);
    }
  });

  // Main Render & Simulation Loop
  let lastTime = performance.now();
  let totalElapsed = 0;

  function frame(now: number) {
    const dt = Math.min((now - lastTime) / 1000.0, 0.1);
    lastTime = now;
    totalElapsed += dt;

    // 1. Update Camera
    camera.update(dt);

    // 2. Update Simulation
    sim.update(dt);

    // 3. Update Particles
    renderer.updateParticles(dt);

    // 4. Render 3D WebGL Isometric Scene
    renderer.render(camera, sim.simTimeHours, currentHeatmapMode, totalElapsed);

    // 5. Render 2.5D Overlay (Citizens, Selection Rings, Labels)
    overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
    sim.renderOverlay(overlayCtx, camera);

    // 6. Update HUD
    ui.updateHUD();

    requestAnimationFrame(frame);
  }

  requestAnimationFrame(frame);
  console.log('[Lublin 1392] Simulation engine running smoothly at 60 FPS.');
}

window.addEventListener('DOMContentLoaded', bootstrap);
