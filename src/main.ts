import type { CityPlan } from './types';
import { ThreeIsometricRenderer } from './engine/three-renderer';
import { SpatialHashGrid } from './engine/spatial-hash';
import { SimulationEngine } from './engine/simulation';
import { ProceduralAudioEngine } from './engine/audio';
import { UIController } from './ui/inspector';
import { IsometricCamera } from './engine/camera';

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
  const sim = new SimulationEngine(plan, spatialGrid);
  const audio = new ProceduralAudioEngine();

  // Dummy fallback camera for UIController
  const dummyCamera = new IsometricCamera(window.innerWidth, window.innerHeight);
  const ui = new UIController(sim, dummyCamera);

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

  // Cluster fair citizens in Market Square around stalls (matching reference images)
  for (let i = 0; i < Math.min(80, sim.citizens.length); i++) {
    const c = sim.citizens[i];
    c.currentX = (Math.random() - 0.5) * 36.0;
    c.currentZ = (Math.random() - 0.5) * 32.0;
    c.targetX = c.currentX + (Math.random() - 0.5) * 8.0;
    c.targetZ = c.currentZ + (Math.random() - 0.5) * 8.0;
  }

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

  // Mouse / Pointer Interaction for Camera Pan, Zoom, and Selection
  let isDragging = false;
  let dragStartX = 0;
  let dragStartY = 0;
  let totalDragDist = 0;

  window.addEventListener('mousedown', (e) => {
    if ((e.target as HTMLElement).tagName !== 'CANVAS') return;
    audio.init();
    isDragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    totalDragDist = 0;
  });

  window.addEventListener('mousemove', (e) => {
    if (isDragging) {
      const dx = e.clientX - dragStartX;
      const dy = e.clientY - dragStartY;
      dragStartX = e.clientX;
      dragStartY = e.clientY;
      totalDragDist += Math.hypot(dx, dy);

      threeRenderer.panBy(-dx, -dy);
    } else {
      // Hover check for citizen prompt (matching image 3)
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
    }
  });

  window.addEventListener('mouseup', () => {
    if (!isDragging) return;
    isDragging = false;

    if (totalDragDist < 5.0) {
      // Clicked on a character or building
      if (threeRenderer.hoveredCitizen) {
        ui.inspectCitizen(threeRenderer.hoveredCitizen);
      } else {
        // Check nearest parcel
        const hitParcel = spatialGrid.findParcelAt(threeRenderer.targetPos.x, threeRenderer.targetPos.z);
        if (hitParcel) {
          ui.inspectParcel(hitParcel);
        } else {
          ui.closeInspector();
        }
      }
    }
  });

  // Wheel zoom
  window.addEventListener('wheel', (e) => {
    if ((e.target as HTMLElement).tagName !== 'CANVAS') return;
    const factor = e.deltaY < 0 ? 0.9 : 1.11;
    threeRenderer.zoomBy(factor);
  }, { passive: true });

  // Camera buttons
  document.getElementById('btn-rotate-cw')?.addEventListener('click', () => {
    threeRenderer.rotateClockwise();
    updateCompassUI();
  });
  document.getElementById('btn-rotate-ccw')?.addEventListener('click', () => {
    threeRenderer.rotateCounterClockwise();
    updateCompassUI();
  });
  document.getElementById('btn-zoom-in')?.addEventListener('click', () => {
    threeRenderer.zoomBy(0.8);
  });
  document.getElementById('btn-zoom-out')?.addEventListener('click', () => {
    threeRenderer.zoomBy(1.25);
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
  });

  // Main Loop
  let lastTime = performance.now();

  function animate(now: number) {
    const dt = Math.min((now - lastTime) / 1000.0, 0.1);
    lastTime = now;

    // 1. Update Simulation
    sim.update(dt);

    // 2. Update Three.js camera & lighting
    threeRenderer.updateCamera(dt);
    threeRenderer.updateDayNightLighting(sim.simTimeHours);
    threeRenderer.updateCitizens(sim.citizens, dt);
    threeRenderer.updateSpeechBubbles(dt);

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
  console.log('[Lublin 1392] High-fidelity simulation running with Blender 3D assets & soft shadows!');
}

window.addEventListener('DOMContentLoaded', bootstrap);
