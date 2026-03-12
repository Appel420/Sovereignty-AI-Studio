/**
 * useRealFocus.ts — GrokEdu v2.0
 * Real Muse 2 BLE via Web Bluetooth API
 * + SSE relay from eeg_streaming.py
 * + MediaPipe pose fusion
 * + Attention · Meditation · Drift · Distraction · Nudge
 */

import { useState, useEffect, useRef, useCallback } from "react";

// ── Muse 2 GATT UUIDs ─────────────────────────────────────────────────────────
const MUSE_SERVICE      = "0000fe8d-0000-1000-8000-00805f9b34fb";
const MUSE_CONTROL      = "273e0001-4c4d-454d-96be-f03bac821358";
const MUSE_EEG          = "273e0003-4c4d-454d-96be-f03bac821358";
const MUSE_ACCEL        = "273e000a-4c4d-454d-96be-f03bac821358";
const MUSE_GYRO         = "273e0009-4c4d-454d-96be-f03bac821358";
const MUSE_PPG          = "273e000f-4c4d-454d-96be-f03bac821358";
const MUSE_TELEMETRY    = "273e0006-4c4d-454d-96be-f03bac821358";

const CHANNELS          = ["TP9", "AF7", "AF8", "TP10"] as const;
type Channel            = (typeof CHANNELS)[number];

const BANDS = {
  delta: [0.5,  4.0],
  theta: [4.0,  8.0],
  alpha: [8.0,  13.0],
  beta:  [13.0, 30.0],
  gamma: [30.0, 45.0],
} as const;
type Band = keyof typeof BANDS;

// ── Types ─────────────────────────────────────────────────────────────────────
export interface EEGBands {
  delta: number;
  theta: number;
  alpha: number;
  beta:  number;
  gamma: number;
}

export interface EEGChannels {
  TP9:  number;
  AF7:  number;
  AF8:  number;
  TP10: number;
}

export interface PoseKeypoint {
  x: number;
  y: number;
  z?: number;
  score: number;
  name: string;
}

export interface PoseState {
  keypoints: PoseKeypoint[];
  score: number;
  posture_score: number;      // 0–1, 1 = upright
  head_tilt: number;          // degrees
  lean_forward: number;       // 0–1
}

export interface FocusState {
  // Connection
  connected:       boolean;
  connecting:      boolean;
  deviceName:      string | null;
  mode:            "idle" | "scanning" | "connecting" | "streaming" | "error" | "sse";
  error:           string | null;
  battery:         number | null;

  // Raw EEG
  channels:        EEGChannels;
  bands:           EEGBands;
  channelBands:    Record<Channel, EEGBands>;
  quality:         Record<Channel, number>;   // 0–1 signal quality

  // Processed
  attention:       number;   // 0–1
  meditation:      number;   // 0–1
  engagementIndex: number;   // beta / (alpha + theta)

  // States
  drifting:        boolean;
  distracted:      boolean;
  blink:           boolean;
  jawClench:       boolean;

  // Actions
  nudge:           boolean;   // pulse true when nudge should fire
  nudgeMessage:    string;

  // Sensors
  heartRate:       number | null;
  accel:           { x: number; y: number; z: number; magnitude: number } | null;
  pose:            PoseState | null;

  // History (last 60 s at 10 Hz = 600 samples)
  attentionHistory: number[];
  meditationHistory: number[];

  // Calibration
  calibrated:      boolean;
  calibrationProgress: number;  // 0–1

  // Session
  sessionId:       string;
  sessionDuration: number;    // seconds
}

export interface UseFocusOptions {
  sseUrl?:           string;   // fallback SSE from Python backend
  onNudge?:          (msg: string) => void;
  onDrift?:          () => void;
  onDistraction?:    () => void;
  calibrationSecs?:  number;   // default 20
  usePose?:          boolean;  // enable MediaPipe pose
  poseVideoEl?:      HTMLVideoElement | null;
}

// ── Band power DSP (runs in browser) ─────────────────────────────────────────
class BandProcessor {
  private readonly sr = 256;
  private readonly N  = 256;
  private buffers: Record<Channel, Float32Array>;
  private positions: Record<Channel, number>;
  private readonly freqs: number[];
  private readonly bandMasks: Record<Band, boolean[]>;

  constructor() {
    this.buffers   = {} as Record<Channel, Float32Array>;
    this.positions = {} as Record<Channel, number>;
    for (const ch of CHANNELS) {
      this.buffers[ch]   = new Float32Array(this.N);
      this.positions[ch] = 0;
    }
    this.freqs = Array.from({ length: Math.floor(this.N / 2) + 1 }, (_, i) =>
      (i * this.sr) / this.N
    );
    this.bandMasks = {} as Record<Band, boolean[]>;
    for (const [name, [lo, hi]] of Object.entries(BANDS)) {
      this.bandMasks[name as Band] = this.freqs.map((f) => f >= lo && f <= hi);
    }
  }

  push(ch: Channel, µv: number) {
    const pos = this.positions[ch];
    this.buffers[ch][pos % this.N] = µv;
    this.positions[ch]++;
  }

  compute(ch: Channel): EEGBands {
    const buf = this.buffers[ch];
    if (this.positions[ch] < this.N) return zeroEEGBands();

    // Apply Hanning window
    const windowed = new Float32Array(this.N);
    const mean = buf.reduce((a, b) => a + b, 0) / this.N;
    for (let i = 0; i < this.N; i++) {
      windowed[i] = (buf[i] - mean) * (0.5 - 0.5 * Math.cos((2 * Math.PI * i) / this.N));
    }

    // Real FFT (Cooley-Tukey)
    const mag = fftMag(windowed);
    const total = mag.reduce((a, b) => a + b * b, 0) + 1e-10;
    const out = {} as EEGBands;
    for (const [name, mask] of Object.entries(this.bandMasks)) {
      let power = 0;
      for (let i = 0; i < mask.length; i++) {
        if (mask[i]) power += mag[i] * mag[i];
      }
      out[name as Band] = power / total;
    }
    return out;
  }

  quality(ch: Channel): number {
    const buf = this.buffers[ch];
    if (this.positions[ch] < 32) return 0;
    const n = Math.min(this.positions[ch], this.N);
    let mean = 0;
    for (let i = 0; i < n; i++) mean += buf[i];
    mean /= n;
    let std = 0;
    for (let i = 0; i < n; i++) std += (buf[i] - mean) ** 2;
    std = Math.sqrt(std / n);
    if (std < 2)   return 0.1;
    if (std > 500) return Math.max(0, 1 - (std - 500) / 1000);
    return Math.min(1, std / 50);
  }

  meanBands(): EEGBands {
    const all = CHANNELS.map((ch) => this.compute(ch));
    const out = {} as EEGBands;
    for (const b of Object.keys(BANDS) as Band[]) {
      out[b] = all.reduce((s, x) => s + x[b], 0) / CHANNELS.length;
    }
    return out;
  }
}

// ── Attention model ───────────────────────────────────────────────────────────
class AttentionModel {
  private history:    number[] = [];
  private lastNudge:  number   = 0;
  private driftCount: number   = 0;
  private baselines:  { attention: number; meditation: number } | null = null;
  private calBuf:     number[] = [];

  addCalibrationSample(attention: number) {
    this.calBuf.push(attention);
  }

  finishCalibration() {
    if (this.calBuf.length > 0) {
      const mean = this.calBuf.reduce((a, b) => a + b, 0) / this.calBuf.length;
      this.baselines = { attention: mean, meditation: 0.5 };
    }
  }

  estimate(bands: EEGBands): {
    attention: number;
    meditation: number;
    engagementIndex: number;
    drifting: boolean;
    distracted: boolean;
    nudge: boolean;
    nudgeMessage: string;
  } {
    const attention = Math.min(1, Math.max(0,
      (bands.beta + bands.gamma * 0.5) / (bands.alpha + bands.theta + 1e-6) / 3
    ));
    const meditation = Math.min(1, Math.max(0,
      (bands.alpha) / (bands.beta + bands.gamma + 1e-6) / 4
    ));
    const engagementIndex = (bands.beta) / (bands.alpha + bands.theta + 1e-6);

    this.history.push(attention);
    if (this.history.length > 600) this.history.shift();

    const recent   = this.history.slice(-10);
    const recentMu = recent.reduce((a, b) => a + b, 0) / (recent.length || 1);
    const drifting = recent.length >= 10 && recentMu < 0.35;
    this.driftCount = drifting ? this.driftCount + 1 : 0;

    const older = this.history.slice(-20, -10);
    const olderMu = older.length ? older.reduce((a, b) => a + b, 0) / older.length : 0.5;
    const distracted = older.length >= 5 && (olderMu - recentMu) > 0.25;

    const now = Date.now() / 1000;
    let nudge = false;
    let nudgeMessage = "";
    if ((drifting || distracted) && now - this.lastNudge > 45) {
      if (this.driftCount > 30 || distracted) {
        nudge = true;
        this.lastNudge = now;
        this.driftCount = 0;
        nudgeMessage = drifting
          ? "Hey — your focus is drifting. Take a breath and refocus! 🧠"
          : "Something pulled your attention. Come back! 👀";
      }
    }

    return { attention, meditation, engagementIndex, drifting, distracted, nudge, nudgeMessage };
  }

  getHistory() { return [...this.history]; }
}

// ── Muse packet parser ────────────────────────────────────────────────────────
function parseEEGPacket(data: DataView): Array<Record<Channel, number>> {
  const frames: Array<Record<Channel, number>> = [];
  const rawBytes: number[] = [];
  for (let i = 0; i < data.byteLength; i++) rawBytes.push(data.getUint8(i));

  // Skip 2 header bytes; 12-bit samples packed, 4 channels interleaved
  const bitArray: number[] = [];
  for (let i = 2; i < rawBytes.length; i++) {
    for (let b = 7; b >= 0; b--) {
      bitArray.push((rawBytes[i] >> b) & 1);
    }
  }

  const numSamples = Math.floor(bitArray.length / 12);
  const rawVals: number[] = [];
  for (let i = 0; i < numSamples; i++) {
    let val = 0;
    for (let b = 0; b < 12; b++) val = (val << 1) | bitArray[i * 12 + b];
    rawVals.push((val - 2048) * 0.48828125);
  }

  for (let i = 0; i + 3 < rawVals.length; i += 4) {
    frames.push({
      TP9:  rawVals[i],
      AF7:  rawVals[i + 1],
      AF8:  rawVals[i + 2],
      TP10: rawVals[i + 3],
    });
  }
  return frames;
}

function parseAccelPacket(data: DataView): { x: number; y: number; z: number; magnitude: number } {
  const x = data.getInt16(2, false) / 16384.0;
  const y = data.getInt16(4, false) / 16384.0;
  const z = data.getInt16(6, false) / 16384.0;
  return { x, y, z, magnitude: Math.sqrt(x * x + y * y + z * z) };
}

// ── Minimal real FFT (DFT for correctness, swap for FFT lib in production) ───
function fftMag(signal: Float32Array): number[] {
  const N = signal.length;
  const half = Math.floor(N / 2) + 1;
  const mag: number[] = new Array(half).fill(0);
  for (let k = 0; k < half; k++) {
    let re = 0, im = 0;
    for (let n = 0; n < N; n++) {
      const angle = (2 * Math.PI * k * n) / N;
      re += signal[n] * Math.cos(angle);
      im -= signal[n] * Math.sin(angle);
    }
    mag[k] = Math.sqrt(re * re + im * im) / N;
  }
  return mag;
}

function zeroEEGBands(): EEGBands {
  return { delta: 0, theta: 0, alpha: 0, beta: 0, gamma: 0 };
}

function zeroChannels(): EEGChannels {
  return { TP9: 0, AF7: 0, AF8: 0, TP10: 0 };
}

// ── Pose estimation via MediaPipe (loaded from CDN) ──────────────────────────
interface MediaPipePose {
  close(): void;
  onResults(cb: (results: any) => void): void;
  send(input: { image: HTMLVideoElement }): Promise<void>;
  setOptions(opts: any): Promise<void>;
}

async function loadMediaPipePose(): Promise<MediaPipePose | null> {
  try {
    if (!(window as any).Pose) {
      await new Promise<void>((res, rej) => {
        const s = document.createElement("script");
        s.src = "https://cdn.jsdelivr.net/npm/@mediapipe/pose/pose.js";
        s.onload = () => res();
        s.onerror = () => rej(new Error("Failed to load MediaPipe"));
        document.head.appendChild(s);
      });
    }
    const pose: MediaPipePose = new (window as any).Pose({
      locateFile: (file: string) =>
        `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`,
    });
    await pose.setOptions({
      modelComplexity: 1,
      smoothLandmarks: true,
      enableSegmentation: false,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });
    return pose;
  } catch {
    console.warn("[Pose] MediaPipe unavailable");
    return null;
  }
}

function parsePoseResults(results: any): PoseState | null {
  if (!results?.poseLandmarks) return null;
  const lm = results.poseLandmarks;

  const keypoints: PoseKeypoint[] = lm.map((p: any, i: number) => ({
    x: p.x, y: p.y, z: p.z,
    score: p.visibility ?? 0,
    name: POSE_LANDMARK_NAMES[i] ?? `kp${i}`,
  }));

  // Posture: compare nose Y to shoulder midpoint Y
  const nose     = lm[0];
  const lShoulder = lm[11];
  const rShoulder = lm[12];
  const lEar     = lm[7];
  const rEar     = lm[8];

  if (!nose || !lShoulder || !rShoulder) return null;

  const shoulderMidY = (lShoulder.y + rShoulder.y) / 2;
  const headY        = nose.y;
  const posture_score = Math.min(1, Math.max(0, 1 - (headY - shoulderMidY + 0.3) * 2));

  // Head tilt: ear-to-ear angle
  const dx = rEar?.x - lEar?.x || 0.1;
  const dy = rEar?.y - lEar?.y || 0;
  const head_tilt = (Math.atan2(dy, dx) * 180) / Math.PI;

  // Lean forward: nose Z vs shoulder Z
  const lean_forward = Math.min(1, Math.max(0, (nose.z ?? 0) - 0.2));

  return { keypoints, score: 1, posture_score, head_tilt, lean_forward };
}

const POSE_LANDMARK_NAMES = [
  "nose","left_eye_inner","left_eye","left_eye_outer",
  "right_eye_inner","right_eye","right_eye_outer",
  "left_ear","right_ear","mouth_left","mouth_right",
  "left_shoulder","right_shoulder","left_elbow","right_elbow",
  "left_wrist","right_wrist","left_pinky","right_pinky",
  "left_index","right_index","left_thumb","right_thumb",
  "left_hip","right_hip","left_knee","right_knee",
  "left_ankle","right_ankle","left_heel","right_heel",
  "left_foot_index","right_foot_index",
];

// ── Main hook ─────────────────────────────────────────────────────────────────
export function useRealFocus(opts: UseFocusOptions = {}): {
  focus: FocusState;
  connect: () => Promise<void>;
  disconnect: () => void;
  startCalibration: () => void;
  sendNudge: (msg?: string) => void;
  connectSSE: () => void;
} {
  const {
    sseUrl          = "http://localhost:5000/api/eeg/live",
    onNudge,
    onDrift,
    onDistraction,
    calibrationSecs = 20,
    usePose         = true,
    poseVideoEl     = null,
  } = opts;

  const [focus, setFocus] = useState<FocusState>(defaultFocusState());
  const deviceRef    = useRef<BluetoothDevice | null>(null);
  const sseRef       = useRef<EventSource | null>(null);
  const processor    = useRef(new BandProcessor());
  const attModel     = useRef(new AttentionModel());
  const poseRef      = useRef<MediaPipePose | null>(null);
  const poseInterval = useRef<number | null>(null);
  const calTimer     = useRef<ReturnType<typeof setInterval> | null>(null);
  const sessionStart = useRef(Date.now());
  const sessionTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const calProgress  = useRef(0);

  // ── Session timer ──────────────────────────────────────────────────────────
  useEffect(() => {
    sessionTimer.current = setInterval(() => {
      setFocus((f) => ({
        ...f,
        sessionDuration: Math.round((Date.now() - sessionStart.current) / 1000),
      }));
    }, 1000);
    return () => {
      if (sessionTimer.current) clearInterval(sessionTimer.current);
    };
  }, []);

  // ── Pose ───────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!usePose || !poseVideoEl) return;
    let running = true;
    (async () => {
      poseRef.current = await loadMediaPipePose();
      if (!poseRef.current || !running) return;
      poseRef.current.onResults((results) => {
        const pose = parsePoseResults(results);
        setFocus((f) => ({ ...f, pose }));
      });
      const tick = async () => {
        if (!running || !poseRef.current) return;
        if (poseVideoEl.readyState >= 2) {
          await poseRef.current.send({ image: poseVideoEl });
        }
        poseInterval.current = window.setTimeout(tick, 100);
      };
      tick();
    })();
    return () => {
      running = false;
      if (poseInterval.current) clearTimeout(poseInterval.current);
      poseRef.current?.close();
    };
  }, [usePose, poseVideoEl]);

  // ── Process EEG frame ──────────────────────────────────────────────────────
  const processEEGFrame = useCallback(
    (frame: Record<Channel, number>) => {
      const proc = processor.current;
      const model = attModel.current;

      for (const ch of CHANNELS) {
        proc.push(ch, frame[ch] ?? 0);
      }

      const channelBands = {} as Record<Channel, EEGBands>;
      for (const ch of CHANNELS) channelBands[ch] = proc.compute(ch);

      const bands   = proc.meanBands();
      const quality = {} as Record<Channel, number>;
      for (const ch of CHANNELS) quality[ch] = proc.quality(ch);

      const est = model.estimate(bands);

      if (est.drifting && onDrift)         onDrift();
      if (est.distracted && onDistraction) onDistraction();
      if (est.nudge && onNudge)            onNudge(est.nudgeMessage);

      setFocus((f) => ({
        ...f,
        channels:          frame as unknown as EEGChannels,
        bands,
        channelBands,
        quality,
        attention:         est.attention,
        meditation:        est.meditation,
        engagementIndex:   est.engagementIndex,
        drifting:          est.drifting,
        distracted:        est.distracted,
        nudge:             est.nudge,
        nudgeMessage:      est.nudgeMessage,
        attentionHistory:  model.getHistory().slice(-600),
        meditationHistory: [],
      }));
    },
    [onNudge, onDrift, onDistraction]
  );

  // ── Web Bluetooth connect ──────────────────────────────────────────────────
  const connect = useCallback(async () => {
    if (!navigator.bluetooth) {
      setFocus((f) => ({
        ...f,
        mode:  "error",
        error: "Web Bluetooth not supported. Use Chrome/Edge on HTTPS.",
      }));
      return;
    }

    setFocus((f) => ({ ...f, connecting: true, mode: "scanning", error: null }));

    try {
      const device = await navigator.bluetooth.requestDevice({
        filters: [
          { namePrefix: "Muse" },
          { services: [MUSE_SERVICE] },
        ],
        optionalServices: [MUSE_SERVICE],
      });

      deviceRef.current = device;
      setFocus((f) => ({ ...f, mode: "connecting", deviceName: device.name ?? null }));

      const server = await device.gatt!.connect();
      const service = await server.getPrimaryService(MUSE_SERVICE);

      // Control
      const control = await service.getCharacteristic(MUSE_CONTROL);

      // EEG notifications
      const eeg = await service.getCharacteristic(MUSE_EEG);
      await eeg.startNotifications();
      eeg.addEventListener("characteristicvaluechanged", (e: Event) => {
        const view = (e.target as BluetoothRemoteGATTCharacteristic).value!;
        const frames = parseEEGPacket(view);
        for (const f of frames) processEEGFrame(f as Record<Channel, number>);
      });

      // Accelerometer
      try {
        const accel = await service.getCharacteristic(MUSE_ACCEL);
        await accel.startNotifications();
        accel.addEventListener("characteristicvaluechanged", (e: Event) => {
          const view = (e.target as BluetoothRemoteGATTCharacteristic).value!;
          const a = parseAccelPacket(view);
          setFocus((f) => ({ ...f, accel: a }));
        });
      } catch { /* optional */ }

      // Telemetry (battery)
      try {
        const telem = await service.getCharacteristic(MUSE_TELEMETRY);
        await telem.startNotifications();
        telem.addEventListener("characteristicvaluechanged", (e: Event) => {
          const view = (e.target as BluetoothRemoteGATTCharacteristic).value!;
          const batt = view.getUint16(0, false) / 512.0 * 100;
          setFocus((f) => ({ ...f, battery: Math.round(batt) }));
        });
      } catch { /* optional */ }

      // Start streaming command
      const startCmd = new TextEncoder().encode("d\n");
      await control.writeValue(startCmd);

      device.addEventListener("gattserverdisconnected", () => {
        setFocus((f) => ({ ...f, connected: false, mode: "idle" }));
      });

      setFocus((f) => ({
        ...f,
        connected: true,
        connecting: false,
        mode: "streaming",
        deviceName: device.name ?? null,
      }));

    } catch (err: any) {
      setFocus((f) => ({
        ...f,
        connecting: false,
        mode: "error",
        error: err.message ?? "BLE connection failed",
      }));
    }
  }, [processEEGFrame]);

  // ── SSE fallback (Python backend) ─────────────────────────────────────────
  const connectSSE = useCallback(() => {
    if (sseRef.current) sseRef.current.close();
    setFocus((f) => ({ ...f, mode: "sse", error: null }));

    const es = new EventSource(sseUrl);
    sseRef.current = es;

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === "status" || data.type === "heartbeat") {
          setFocus((f) => ({
            ...f,
            connected: data.connected ?? f.connected,
            mode: data.mode ?? f.mode,
            error: data.error ?? null,
          }));
          return;
        }
        if (data.type === "nudge") {
          if (onNudge) onNudge(data.message ?? "Stay focused!");
          setFocus((f) => ({ ...f, nudge: true, nudgeMessage: data.message ?? "" }));
          setTimeout(() => setFocus((f) => ({ ...f, nudge: false })), 1000);
          return;
        }

        // Full EEGFrame from Python
        const channels: EEGChannels = data.channels ?? zeroChannels();
        const bands: EEGBands       = data.mean_bands ?? zeroEEGBands();
        const channelBands          = data.bands ?? {};
        const quality               = data.quality ?? {};

        const model = attModel.current;
        const est   = model.estimate(bands);

        if (est.nudge && onNudge) onNudge(est.nudgeMessage);

        setFocus((f) => ({
          ...f,
          connected:         true,
          channels,
          bands,
          channelBands,
          quality,
          attention:         data.attention ?? est.attention,
          meditation:        data.meditation ?? est.meditation,
          engagementIndex:   est.engagementIndex,
          drifting:          data.drift ?? est.drifting,
          distracted:        data.distracted ?? est.distracted,
          nudge:             data.nudge ?? est.nudge,
          nudgeMessage:      est.nudgeMessage,
          blink:             data.blink ?? false,
          jawClench:         data.jaw_clench ?? false,
          heartRate:         data.heart_rate ?? null,
          accel:             data.accel ?? null,
          attentionHistory:  model.getHistory().slice(-600),
        }));
      } catch { /* malformed frame */ }
    };

    es.onerror = () => {
      setFocus((f) => ({
        ...f,
        connected: false,
        mode: "error",
        error: "SSE connection lost. Is eeg_streaming.py running on :5000?",
      }));
    };
  }, [sseUrl, onNudge]);

  // ── Disconnect ─────────────────────────────────────────────────────────────
  const disconnect = useCallback(() => {
    deviceRef.current?.gatt?.disconnect();
    sseRef.current?.close();
    setFocus((f) => ({ ...f, connected: false, mode: "idle", error: null }));
  }, []);

  // ── Calibration ───────────────────────────────────────────────────────────
  const startCalibration = useCallback(() => {
    calProgress.current = 0;
    setFocus((f) => ({ ...f, calibrated: false, calibrationProgress: 0 }));
    const interval = 500;
    const steps    = (calibrationSecs * 1000) / interval;
    let step       = 0;

    calTimer.current = setInterval(() => {
      step++;
      calProgress.current = step / steps;
      attModel.current.addCalibrationSample(
        (focus as any)?.attention ?? 0.5
      );
      setFocus((f) => ({ ...f, calibrationProgress: step / steps }));
      if (step >= steps) {
        clearInterval(calTimer.current!);
        attModel.current.finishCalibration();
        setFocus((f) => ({ ...f, calibrated: true, calibrationProgress: 1 }));
      }
    }, interval);
  }, [calibrationSecs]);

  // ── Manual nudge ──────────────────────────────────────────────────────────
  const sendNudge = useCallback((msg = "Stay focused! 🧠") => {
    if (onNudge) onNudge(msg);
    setFocus((f) => ({ ...f, nudge: true, nudgeMessage: msg }));
    setTimeout(() => setFocus((f) => ({ ...f, nudge: false })), 1500);
  }, [onNudge]);

  // ── Cleanup ────────────────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      disconnect();
      if (calTimer.current) clearInterval(calTimer.current);
    };
  }, [disconnect]);

  return { focus, connect, disconnect, startCalibration, sendNudge, connectSSE };
}

// ── Default state ─────────────────────────────────────────────────────────────
function defaultFocusState(): FocusState {
  return {
    connected: false, connecting: false, deviceName: null,
    mode: "idle", error: null, battery: null,
    channels: zeroChannels(),
    bands: zeroEEGBands(),
    channelBands: Object.fromEntries(CHANNELS.map((c) => [c, zeroEEGBands()])) as Record<Channel, EEGBands>,
    quality: Object.fromEntries(CHANNELS.map((c) => [c, 0])) as Record<Channel, number>,
    attention: 0, meditation: 0, engagementIndex: 0,
    drifting: false, distracted: false, nudge: false, nudgeMessage: "",
    blink: false, jawClench: false,
    heartRate: null, accel: null, pose: null,
    attentionHistory: [], meditationHistory: [],
    calibrated: false, calibrationProgress: 0,
    sessionId: Math.random().toString(36).slice(2, 10),
    sessionDuration: 0,
  };
}
