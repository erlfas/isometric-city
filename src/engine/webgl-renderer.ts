import { IsometricCamera } from './camera';
import type { MeshBufferData } from './procedural-assets';
import type { HeatmapMode } from '../types';

export class WebGLIsometricRenderer {
  private canvas: HTMLCanvasElement;
  private gl: WebGL2RenderingContext | WebGLRenderingContext | null = null;

  // Shader program & attributes
  private program: WebGLProgram | null = null;
  private posBuffer: WebGLBuffer | null = null;
  private normalBuffer: WebGLBuffer | null = null;
  private colorBuffer: WebGLBuffer | null = null;
  private indexBuffer: WebGLBuffer | null = null;
  private indexCount: number = 0;

  // Uniform locations
  private uViewProjLoc: WebGLUniformLocation | null = null;
  private uLightDirLoc: WebGLUniformLocation | null = null;
  private uSunColorLoc: WebGLUniformLocation | null = null;
  private uAmbientColorLoc: WebGLUniformLocation | null = null;
  private uHeatmapModeLoc: WebGLUniformLocation | null = null;
  private uTimeLoc: WebGLUniformLocation | null = null;

  // Mat4 scratch buffer (zero GC)
  private mvpMatrix = new Float32Array(16);

  // Particle systems (Chimney smoke, night embers, fair flags)
  private smokeParticles: { x: number; y: number; z: number; vy: number; vx: number; vz: number; life: number; maxLife: number; size: number }[] = [];
  private maxSmokeParticles = 250;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    this.initGL();
    this.initSmokeParticles();
  }

  private initGL(): void {
    const gl = this.canvas.getContext('webgl2', { antialias: true, alpha: false, depth: true }) ||
               this.canvas.getContext('webgl', { antialias: true, alpha: false, depth: true });

    if (!gl) {
      console.warn('[WebGLRenderer] WebGL not supported, falling back to 2D context.');
      return;
    }
    this.gl = gl;

    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    gl.enable(gl.CULL_FACE);
    gl.cullFace(gl.BACK);

    // Shaders
    const vsSource = `
      attribute vec3 aPosition;
      attribute vec3 aNormal;
      attribute vec4 aColor;

      uniform mat4 uViewProj;
      uniform vec3 uLightDir;
      uniform vec3 uSunColor;
      uniform vec3 uAmbientColor;
      uniform int uHeatmapMode;
      uniform float uTime;

      varying vec4 vColor;
      varying vec3 vNormal;
      varying float vHeight;

      void main() {
        vNormal = aNormal;
        vHeight = aPosition.y;

        // Diffuse directional light
        float diff = max(dot(aNormal, normalize(uLightDir)), 0.0);
        vec3 litColor = aColor.rgb * (uAmbientColor + uSunColor * diff);

        // Ground ambient occlusion / depth fog tint
        float ao = clamp(aPosition.y * 0.04 + 0.75, 0.6, 1.0);
        litColor *= ao;

        vColor = vec4(litColor, aColor.a);
        gl_Position = uViewProj * vec4(aPosition, 1.0);
      }
    `;

    const fsSource = `
      precision mediump float;

      varying vec4 vColor;
      varying vec3 vNormal;
      varying float vHeight;

      void main() {
        gl_FragColor = vColor;
      }
    `;

    const vs = this.compileShader(gl.VERTEX_SHADER, vsSource);
    const fs = this.compileShader(gl.FRAGMENT_SHADER, fsSource);
    if (!vs || !fs) return;

    const prog = gl.createProgram();
    if (!prog) return;
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);

    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      console.error('[WebGLRenderer] Program link failed:', gl.getProgramInfoLog(prog));
      return;
    }

    this.program = prog;
    gl.useProgram(prog);

    this.uViewProjLoc = gl.getUniformLocation(prog, 'uViewProj');
    this.uLightDirLoc = gl.getUniformLocation(prog, 'uLightDir');
    this.uSunColorLoc = gl.getUniformLocation(prog, 'uSunColor');
    this.uAmbientColorLoc = gl.getUniformLocation(prog, 'uAmbientColor');
    this.uHeatmapModeLoc = gl.getUniformLocation(prog, 'uHeatmapMode');
    this.uTimeLoc = gl.getUniformLocation(prog, 'uTime');
  }

  private compileShader(type: number, src: string): WebGLShader | null {
    if (!this.gl) return null;
    const s = this.gl.createShader(type);
    if (!s) return null;
    this.gl.shaderSource(s, src);
    this.gl.compileShader(s);
    if (!this.gl.getShaderParameter(s, this.gl.COMPILE_STATUS)) {
      console.error('[WebGLRenderer] Shader compile error:', this.gl.getShaderInfoLog(s));
      this.gl.deleteShader(s);
      return null;
    }
    return s;
  }

  public uploadMesh(data: MeshBufferData): void {
    if (!this.gl || !this.program) return;
    const gl = this.gl;

    this.indexCount = data.indices.length;

    // Positions
    this.posBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.posBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, data.positions, gl.STATIC_DRAW);
    const aPos = gl.getAttribLocation(this.program, 'aPosition');
    gl.enableVertexAttribArray(aPos);
    gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);

    // Normals
    this.normalBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.normalBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, data.normals, gl.STATIC_DRAW);
    const aNorm = gl.getAttribLocation(this.program, 'aNormal');
    gl.enableVertexAttribArray(aNorm);
    gl.vertexAttribPointer(aNorm, 3, gl.FLOAT, false, 0, 0);

    // Colors
    this.colorBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.colorBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, data.colors, gl.STATIC_DRAW);
    const aCol = gl.getAttribLocation(this.program, 'aColor');
    gl.enableVertexAttribArray(aCol);
    gl.vertexAttribPointer(aCol, 4, gl.FLOAT, false, 0, 0);

    // Indices
    this.indexBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.indexBuffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, data.indices, gl.STATIC_DRAW);

    console.log(`[WebGLRenderer] Uploaded ${this.indexCount / 3} triangles to GPU buffers.`);
  }

  private initSmokeParticles(): void {
    const chimneySpawners = [
      { x: 0, y: 18, z: 0 },
      { x: -25, y: 14, z: -15 },
      { x: 35, y: 12, z: 25 },
      { x: -80, y: 10, z: -40 },
      { x: 90, y: 11, z: 30 }
    ];

    for (let i = 0; i < this.maxSmokeParticles; i++) {
      const sp = chimneySpawners[i % chimneySpawners.length];
      this.smokeParticles.push({
        x: sp.x + (Math.random() - 0.5) * 2,
        y: sp.y + Math.random() * 8,
        z: sp.z + (Math.random() - 0.5) * 2,
        vx: (Math.random() - 0.5) * 0.4 + 0.3, // East wind
        vy: 1.2 + Math.random() * 1.5,
        vz: (Math.random() - 0.5) * 0.4,
        life: Math.random() * 5.0,
        maxLife: 4.5 + Math.random() * 2.0,
        size: 0.8 + Math.random() * 1.2
      });
    }
  }

  public updateParticles(dt: number): void {
    for (let i = 0; i < this.smokeParticles.length; i++) {
      const p = this.smokeParticles[i];
      p.life += dt;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.z += p.vz * dt;
      p.size += dt * 0.4;

      if (p.life >= p.maxLife) {
        // Reset near chimney base
        p.life = 0;
        p.y = 12 + Math.random() * 4;
        p.size = 0.8 + Math.random() * 0.6;
      }
    }
  }

  /**
   * Constructs the Orthographic Axonometric Dimetric MVP Matrix:
   * Fixed 2:1 isometric angle with 4 quadrant view rotations.
   */
  private updateMVPMatrix(camera: IsometricCamera): void {
    const w = this.canvas.width;
    const h = this.canvas.height;
    const zoom = camera.zoom;

    // View bounds in world units
    const orthoW = (w / zoom) * 0.5;
    const orthoH = (h / zoom) * 0.5;
    const near = -800.0;
    const far = 800.0;

    // 1. Orthographic Projection Matrix:
    // [ 1/orthoW,    0,           0,               0 ]
    // [ 0,        1/orthoH,       0,               0 ]
    // [ 0,           0,       -2/(far-near),       0 ]
    // [ 0,           0,    -(far+near)/(far-near), 1 ]

    // 2. Isometric Camera Orientation:
    // Fixed Dimetric angle: pitch = 30° (0.523599 rad) or 35.264°
    // Yaw = currentRotationAngle (SW, NW, NE, SE)
    const pitch = 0.523599; // 30° classic isometric slope
    const yaw = camera.currentRotationAngle;

    const cosP = Math.cos(pitch);
    const sinP = Math.sin(pitch);
    const cosY = Math.cos(yaw);
    const sinY = Math.sin(yaw);

    // Compute combined rotation & projection
    const m = this.mvpMatrix;

    // R_pitch * R_yaw
    const r00 = cosY;
    const r01 = 0.0;
    const r02 = -sinY;

    const r10 = sinY * sinP;
    const r11 = cosP;
    const r12 = cosY * sinP;

    const r20 = sinY * cosP;
    const r21 = -sinP;
    const r22 = cosY * cosP;

    // Scale by orthographic bounds
    const sx = 1.0 / orthoW;
    const sy = 1.0 / orthoH;
    const sz = -2.0 / (far - near);

    m[0] = r00 * sx;
    m[1] = r10 * sy;
    m[2] = r20 * sz;
    m[3] = 0.0;

    m[4] = r01 * sx;
    m[5] = r11 * sy;
    m[6] = r21 * sz;
    m[7] = 0.0;

    m[8] = r02 * sx;
    m[9] = r12 * sy;
    m[10] = r22 * sz;
    m[11] = 0.0;

    // Translation relative to camera center (cx, 0, cz)
    const tx = -camera.x;
    const ty = 0.0;
    const tz = -camera.z;

    const tPrimeX = r00 * tx + r01 * ty + r02 * tz;
    const tPrimeY = r10 * tx + r11 * ty + r12 * tz;
    const tPrimeZ = r20 * tx + r21 * ty + r22 * tz;

    m[12] = tPrimeX * sx;
    m[13] = tPrimeY * sy;
    m[14] = tPrimeZ * sz;
    m[15] = 1.0;
  }

  public render(
    camera: IsometricCamera,
    timeOfDayHours: number, // 0.0 to 24.0
    heatmapMode: HeatmapMode,
    elapsedSec: number
  ): void {
    if (!this.gl || !this.program || this.indexCount === 0) return;
    const gl = this.gl;

    gl.viewport(0, 0, this.canvas.width, this.canvas.height);

    // Day/Night Lighting Colors
    // Dawn (5-8h), Midday Fair (9-16h), Dusk (17-20h), Night (21-4h)
    let sunR = 1.0, sunG = 0.95, sunB = 0.85;
    let ambR = 0.45, ambG = 0.48, ambB = 0.52;
    let skyR = 0.55, skyG = 0.68, skyB = 0.82;
    let lightDirX = 0.6, lightDirY = 0.8, lightDirZ = 0.4;

    if (timeOfDayHours >= 5.0 && timeOfDayHours < 8.0) {
      // Dawn / Matins: warm rosy golden light
      const t = (timeOfDayHours - 5.0) / 3.0;
      sunR = 1.0; sunG = 0.72 + t * 0.2; sunB = 0.45 + t * 0.35;
      ambR = 0.40; ambG = 0.35; ambB = 0.42;
      skyR = 0.62; skyG = 0.48; skyB = 0.55;
      lightDirY = 0.4 + t * 0.4;
    } else if (timeOfDayHours >= 8.0 && timeOfDayHours < 17.0) {
      // High Fair Noon: bright warm sunlight
      sunR = 1.05; sunG = 1.0; sunB = 0.92;
      ambR = 0.55; ambG = 0.56; ambB = 0.58;
      skyR = 0.50; skyG = 0.68; skyB = 0.88;
      lightDirY = 0.9;
    } else if (timeOfDayHours >= 17.0 && timeOfDayHours < 21.0) {
      // Dusk / Vespers: amber and violet twilight
      const t = (timeOfDayHours - 17.0) / 4.0;
      sunR = 0.95 - t * 0.35; sunG = 0.55 - t * 0.3; sunB = 0.25 + t * 0.1;
      ambR = 0.32 - t * 0.15; ambG = 0.28 - t * 0.12; ambB = 0.38 - t * 0.1;
      skyR = 0.45 - t * 0.3; skyG = 0.35 - t * 0.25; skyB = 0.55 - t * 0.3;
      lightDirY = 0.4 - t * 0.3;
    } else {
      // Night Curfew (21.0 - 5.0): deep royal navy moonlight + glowing lantern accents
      sunR = 0.20; sunG = 0.25; sunB = 0.42;
      ambR = 0.12; ambG = 0.14; ambB = 0.22;
      skyR = 0.08; skyG = 0.10; skyB = 0.16;
      lightDirY = 0.5;
    }

    gl.clearColor(skyR, skyG, skyB, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

    gl.useProgram(this.program);

    this.updateMVPMatrix(camera);

    gl.uniformMatrix4fv(this.uViewProjLoc, false, this.mvpMatrix);
    gl.uniform3f(this.uLightDirLoc, lightDirX, lightDirY, lightDirZ);
    gl.uniform3f(this.uSunColorLoc, sunR, sunG, sunB);
    gl.uniform3f(this.uAmbientColorLoc, ambR, ambG, ambB);
    gl.uniform1i(this.uHeatmapModeLoc, heatmapMode === 'none' ? 0 : 1);
    gl.uniform1f(this.uTimeLoc, elapsedSec);

    // Draw static city mesh
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.indexBuffer);
    gl.drawElements(gl.TRIANGLES, this.indexCount, gl.UNSIGNED_INT, 0);
  }
}
