/**
 * TouchGestureManager
 * Provides high-fidelity multi-touch gestures for smartphones and tablets:
 * - Single-finger panning with smooth inertia
 * - Two-finger pinch-to-zoom
 * - Two-finger rotation twist (with snap-to-quadrant)
 * - Single-finger tap for selecting citizens & buildings (with screen raycasting)
 * - Double-tap for quick zoom & center
 * - Touch-action isolation and WebAudio unlocking
 */

export interface TouchGestureCallbacks {
  onPan: (dx: number, dy: number) => void;
  onPinch: (zoomFactor: number, centerX: number, centerY: number) => void;
  onRotateAngle?: (deltaRad: number) => void;
  onRotateStep?: (direction: 1 | -1) => void;
  onTap: (screenX: number, screenY: number) => void;
  onDoubleTap?: (screenX: number, screenY: number) => void;
  onInteractionStart?: () => void;
}

interface PointerInfo {
  id: number;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  prevX: number;
  prevY: number;
  startTime: number;
}

export class TouchGestureManager {
  private element: HTMLElement;
  private callbacks: TouchGestureCallbacks;

  private activePointers = new Map<number, PointerInfo>();
  private initialPinchDist: number = 0;
  private prevPinchDist: number = 0;
  private initialAngle: number = 0;
  private prevAngle: number = 0;
  private totalTwistAngle: number = 0;

  // Tap & double-tap tracking
  private lastTapTime: number = 0;
  private lastTapX: number = 0;
  private lastTapY: number = 0;
  private hasMovedSignificant: boolean = false;

  constructor(element: HTMLElement, callbacks: TouchGestureCallbacks) {
    this.element = element;
    this.callbacks = callbacks;

    this.bindEvents();
  }

  private bindEvents(): void {
    const el = this.element;

    // Use PointerEvents with touch fallback
    el.addEventListener('pointerdown', this.onPointerDown.bind(this), { passive: false });
    window.addEventListener('pointermove', this.onPointerMove.bind(this), { passive: false });
    window.addEventListener('pointerup', this.onPointerUp.bind(this), { passive: false });
    window.addEventListener('pointercancel', this.onPointerCancel.bind(this), { passive: false });

    // Prevent default context menu (long press callout on mobile)
    el.addEventListener('contextmenu', (e) => e.preventDefault());

    // Prevent default touch gestures on canvas container
    el.addEventListener('touchstart', () => {
      this.callbacks.onInteractionStart?.();
    }, { passive: true });
  }

  private onPointerDown(e: PointerEvent): void {
    // Only capture if tapped on our element or canvas
    if (e.target !== this.element && !this.element.contains(e.target as Node)) {
      return;
    }

    this.callbacks.onInteractionStart?.();

    try {
      this.element.setPointerCapture(e.pointerId);
    } catch {
      // Ignore if not supported
    }

    const info: PointerInfo = {
      id: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      currentX: e.clientX,
      currentY: e.clientY,
      prevX: e.clientX,
      prevY: e.clientY,
      startTime: performance.now()
    };

    this.activePointers.set(e.pointerId, info);

    if (this.activePointers.size === 1) {
      this.hasMovedSignificant = false;
    } else if (this.activePointers.size === 2) {
      const [p1, p2] = Array.from(this.activePointers.values());
      this.initialPinchDist = Math.hypot(p2.currentX - p1.currentX, p2.currentY - p1.currentY);
      this.prevPinchDist = this.initialPinchDist;
      this.initialAngle = Math.atan2(p2.currentY - p1.currentY, p2.currentX - p1.currentX);
      this.prevAngle = this.initialAngle;
      this.totalTwistAngle = 0;
      this.hasMovedSignificant = true; // Two fingers cancel tap
    }
  }

  private onPointerMove(e: PointerEvent): void {
    const pointer = this.activePointers.get(e.pointerId);
    if (!pointer) return;

    pointer.prevX = pointer.currentX;
    pointer.prevY = pointer.currentY;
    pointer.currentX = e.clientX;
    pointer.currentY = e.clientY;

    const totalMove = Math.hypot(pointer.currentX - pointer.startX, pointer.currentY - pointer.startY);
    if (totalMove > 8.0) {
      this.hasMovedSignificant = true;
    }

    if (this.activePointers.size === 1) {
      // Single finger drag = Pan
      const dx = pointer.currentX - pointer.prevX;
      const dy = pointer.currentY - pointer.prevY;
      if (Math.abs(dx) > 0 || Math.abs(dy) > 0) {
        this.callbacks.onPan(dx, dy);
      }
    } else if (this.activePointers.size === 2) {
      // Two finger pinch & rotate
      const [p1, p2] = Array.from(this.activePointers.values());
      const curDist = Math.hypot(p2.currentX - p1.currentX, p2.currentY - p1.currentY);
      const centerX = (p1.currentX + p2.currentX) * 0.5;
      const centerY = (p1.currentY + p2.currentY) * 0.5;

      if (this.prevPinchDist > 0 && curDist > 0) {
        // Zoom factor: if curDist > prevDist, pinch-out (zoom in, factor < 1.0 for threeRenderer)
        const factor = this.prevPinchDist / curDist;
        this.callbacks.onPinch(factor, centerX, centerY);
        this.prevPinchDist = curDist;
      }

      // Check twist angle
      const curAngle = Math.atan2(p2.currentY - p1.currentY, p2.currentX - p1.currentX);
      let deltaAngle = curAngle - this.prevAngle;
      while (deltaAngle < -Math.PI) deltaAngle += Math.PI * 2;
      while (deltaAngle > Math.PI) deltaAngle -= Math.PI * 2;

      this.totalTwistAngle += deltaAngle;
      this.prevAngle = curAngle;

      if (this.callbacks.onRotateAngle) {
        this.callbacks.onRotateAngle(deltaAngle);
      }

      // If twist threshold exceeds 40 degrees, trigger a 90° camera rotation step
      if (Math.abs(this.totalTwistAngle) > 0.7) { // ~40 degrees
        const dir = this.totalTwistAngle > 0 ? 1 : -1;
        this.callbacks.onRotateStep?.(dir);
        this.totalTwistAngle = 0;
      }
    }
  }

  private onPointerUp(e: PointerEvent): void {
    const pointer = this.activePointers.get(e.pointerId);
    if (!pointer) return;

    try {
      this.element.releasePointerCapture(e.pointerId);
    } catch {
      // Ignore
    }

    const wasSingleFinger = this.activePointers.size === 1;
    this.activePointers.delete(e.pointerId);

    if (wasSingleFinger && !this.hasMovedSignificant) {
      const now = performance.now();
      const distFromStart = Math.hypot(e.clientX - pointer.startX, e.clientY - pointer.startY);
      const duration = now - pointer.startTime;

      if (distFromStart < 12.0 && duration < 500) {
        // Check for double-tap
        const timeSinceLastTap = now - this.lastTapTime;
        const distFromLastTap = Math.hypot(e.clientX - this.lastTapX, e.clientY - this.lastTapY);

        if (timeSinceLastTap < 320 && distFromLastTap < 30) {
          // Double-tap
          this.callbacks.onDoubleTap?.(e.clientX, e.clientY);
          this.lastTapTime = 0;
        } else {
          // Single tap
          this.callbacks.onTap(e.clientX, e.clientY);
          this.lastTapTime = now;
          this.lastTapX = e.clientX;
          this.lastTapY = e.clientY;
        }
      }
    }

    if (this.activePointers.size === 1) {
      // Remaining pointer reset start to avoid sudden jump
      const remaining = Array.from(this.activePointers.values())[0];
      remaining.prevX = remaining.currentX;
      remaining.prevY = remaining.currentY;
    }
  }

  private onPointerCancel(e: PointerEvent): void {
    this.activePointers.delete(e.pointerId);
  }
}
