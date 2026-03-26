#!/usr/bin/env python3
"""
GrokEdu EEG Streaming Server — v2.0
Real Muse 2 BLE via muselsl + bleak
Flask SSE at /api/eeg/live
Attention · Meditation · Drift · Distraction Detection
"""

import asyncio
import json
import math
import queue
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass
from typing import Optional

import numpy as np
from flask import Flask, Response, jsonify, request
from flask_cors import CORS

# ── Optional BLE imports (graceful degradation) ──────────────────────────────
try:
    from muselsl import stream as muse_stream
    from muselsl.muse import Muse
    HAS_MUSELSL = True
except ImportError:
    HAS_MUSELSL = False

try:
    from bleak import BleakClient, BleakScanner
    HAS_BLEAK = True
except ImportError:
    HAS_BLEAK = False

try:
    from pylsl import StreamInlet, resolve_byprop
    HAS_LSL = True
except ImportError:
    HAS_LSL = False

# ── Constants ─────────────────────────────────────────────────────────────────
MUSE_SERVICE_UUID        = "0000fe8d-0000-1000-8000-00805f9b34fb"
MUSE_CONTROL_CHAR        = "273e0001-4c4d-454d-96be-f03bac821358"
MUSE_EEG_CHAR            = "273e0003-4c4d-454d-96be-f03bac821358"
MUSE_ACCEL_CHAR          = "273e000a-4c4d-454d-96be-f03bac821358"
MUSE_GYRO_CHAR           = "273e0009-4c4d-454d-96be-f03bac821358"
MUSE_PPG_CHAR            = "273e000f-4c4d-454d-96be-f03bac821358"
MUSE_TELEMETRY_CHAR      = "273e0006-4c4d-454d-96be-f03bac821358"

SAMPLE_RATE              = 256   # Hz — Muse 2 native
FFT_WINDOW               = 256   # samples per FFT
CHANNELS                 = ["TP9", "AF7", "AF8", "TP10"]
ATTENTION_HISTORY_LEN    = 60    # seconds of history
DRIFT_THRESHOLD          = 0.35  # attention below this = drifting
DISTRACT_THRESHOLD       = 0.25  # rapid drop = distraction event
NUDGE_COOLDOWN_SECS      = 45    # min seconds between nudges

# Frequency bands (Hz)
BANDS = {
    "delta": (0.5, 4.0),
    "theta": (4.0, 8.0),
    "alpha": (8.0, 13.0),
    "beta":  (13.0, 30.0),
    "gamma": (30.0, 45.0),
}

app = Flask(__name__)
CORS(app, origins="*")

# ── Shared state ──────────────────────────────────────────────────────────────
_eeg_queue: queue.Queue = queue.Queue(maxsize=512)
_accel_queue: queue.Queue = queue.Queue(maxsize=128)
_ppg_queue: queue.Queue = queue.Queue(maxsize=128)
_subscribers: list = []
_subscribers_lock = threading.Lock()

_device_status = {
    "connected": False,
    "device_name": None,
    "battery": None,
    "mode": "searching",   # searching | connecting | streaming | error
    "error": None,
}

@dataclass
class EEGFrame:
    ts:          float
    session_id:  str
    channels:    dict        # {TP9, AF7, AF8, TP10} raw µV
    bands:       dict        # per-channel band powers
    mean_bands:  dict        # averaged across channels
    attention:   float       # 0–1
    meditation:  float       # 0–1
    drift:       bool
    distracted:  bool
    nudge:       bool
    blink:       bool
    jaw_clench:  bool
    heart_rate:  Optional[float]
    pose:        Optional[dict]
    accel:       Optional[dict]
    quality:     dict        # per-channel signal quality 0–1


# ── Signal Processing ─────────────────────────────────────────────────────────
class BandPowerProcessor:
    def __init__(self, sample_rate=SAMPLE_RATE, window=FFT_WINDOW):
        self.sr = sample_rate
        self.win = window
        self.buffers = {ch: deque(maxlen=window) for ch in CHANNELS}
        freqs = np.fft.rfftfreq(window, d=1.0/sample_rate)
        self._band_masks = {}
        for name, (lo, hi) in BANDS.items():
            self._band_masks[name] = (freqs >= lo) & (freqs <= hi)

    def push(self, samples: dict):
        """samples: {TP9: float, AF7: float, AF8: float, TP10: float}"""
        for ch in CHANNELS:
            if ch in samples:
                self.buffers[ch].append(samples[ch])

    def compute(self) -> dict:
        result = {}
        for ch in CHANNELS:
            buf = np.array(self.buffers[ch])
            if len(buf) < self.win:
                result[ch] = {b: 0.0 for b in BANDS}
                continue
            buf = buf - np.mean(buf)
            buf *= np.hanning(len(buf))
            fft_mag = np.abs(np.fft.rfft(buf)) ** 2
            total = np.sum(fft_mag) + 1e-10
            result[ch] = {
                name: float(np.sum(fft_mag[mask]) / total)
                for name, mask in self._band_masks.items()
            }
        return result

    def signal_quality(self) -> dict:
        """Return 0–1 quality per channel (based on variance heuristic)"""
        q = {}
        for ch in CHANNELS:
            buf = np.array(self.buffers[ch])
            if len(buf) < 32:
                q[ch] = 0.0
                continue
            std = np.std(buf)
            # Good EEG: 10–100 µV RMS. Too flat = poor contact, too noisy = artifact
            if std < 2:
                q[ch] = 0.1
            elif std > 500:
                q[ch] = max(0.0, 1.0 - (std - 500) / 1000.0)
            else:
                q[ch] = min(1.0, std / 50.0)
        return q


class AttentionEstimator:
    def __init__(self):
        self.history = deque(maxlen=ATTENTION_HISTORY_LEN * 10)  # 10 Hz updates
        self._last_nudge = 0.0
        self._drift_counter = 0
        self._distract_counter = 0

    def estimate(self, bands: dict) -> tuple[float, float, bool, bool, bool]:
        """
        Returns: attention, meditation, is_drifting, is_distracted, send_nudge
        
        Attention model (NeuroSky-inspired, adapted):
          - High beta + gamma relative to alpha → focused
          - High alpha + theta relative to beta → relaxed/unfocused
        
        Meditation model:
          - High alpha, low beta, low gamma
        """
        # Average frontal channels (AF7, AF8) for attention
        frontal = ["AF7", "AF8"]
        temporal = ["TP9", "TP10"]

        def avg_band(chs, band):
            vals = [bands[ch][band] for ch in chs if ch in bands]
            return float(np.mean(vals)) if vals else 0.0

        f_alpha = avg_band(frontal, "alpha")
        f_beta  = avg_band(frontal, "beta")
        f_gamma = avg_band(frontal, "gamma")
        f_theta = avg_band(frontal, "theta")

        t_alpha = avg_band(temporal, "alpha")
        t_theta = avg_band(temporal, "theta")

        # Attention: beta+gamma engagement ratio
        attention_raw = (f_beta + f_gamma * 0.5) / (f_alpha + f_theta + 1e-6)
        attention = float(np.clip(attention_raw / 3.0, 0.0, 1.0))

        # Meditation: alpha dominance
        meditation_raw = (f_alpha + t_alpha) / (f_beta + f_gamma + 1e-6)
        meditation = float(np.clip(meditation_raw / 4.0, 0.0, 1.0))

        self.history.append(attention)

        # Drift: sustained low attention
        if len(self.history) >= 10:
            recent = list(self.history)[-10:]
            drift = bool(np.mean(recent) < DRIFT_THRESHOLD)
            self._drift_counter = self._drift_counter + 1 if drift else 0
        else:
            drift = False

        # Distraction: sudden drop in attention
        if len(self.history) >= 5:
            old_avg = np.mean(list(self.history)[-10:-5]) if len(self.history) >= 10 else 0.5
            new_avg = np.mean(list(self.history)[-5:])
            distracted = bool((old_avg - new_avg) > DISTRACT_THRESHOLD)
        else:
            distracted = False

        # Nudge: drift or distraction sustained, respecting cooldown
        now = time.time()
        nudge = False
        if (drift or distracted) and (now - self._last_nudge) > NUDGE_COOLDOWN_SECS:
            if self._drift_counter > 30 or distracted:
                nudge = True
                self._last_nudge = now
                self._drift_counter = 0

        return attention, meditation, drift, distracted, nudge


class ArtifactDetector:
    """Simple threshold-based blink and jaw-clench detection"""
    def __init__(self, sample_rate=SAMPLE_RATE):
        self.sr = sample_rate
        self._af7_buf = deque(maxlen=64)
        self._af8_buf = deque(maxlen=64)

    def push(self, af7: float, af8: float):
        self._af7_buf.append(af7)
        self._af8_buf.append(af8)

    def detect(self) -> tuple[bool, bool]:
        """Returns: blink, jaw_clench"""
        if len(self._af7_buf) < 32:
            return False, False

        af7 = np.array(self._af7_buf)
        af8 = np.array(self._af8_buf)

        # Blink: large symmetric spike in frontal channels
        af7_std = np.std(af7[-8:])
        af8_std = np.std(af8[-8:])
        blink = bool(af7_std > 150 and af8_std > 150)

        # Jaw clench: broad high-frequency burst
        af7_rms = np.sqrt(np.mean(af7[-16:] ** 2))
        jaw = bool(af7_rms > 300)

        return blink, jaw


# ── BLE Connection Layer ──────────────────────────────────────────────────────
class MuseBLEStreamer:
    """
    Direct Muse 2 BLE streaming via bleak.
    Parses raw 20-byte EEG packets from the Muse GATT EEG characteristic.
    """
    def __init__(self):
        self.client: Optional[BleakClient] = None
        self._running = False
        self._processor = BandPowerProcessor()
        self._attention = AttentionEstimator()
        self._artifacts = ArtifactDetector()
        self._session_id = str(uuid.uuid4())[:8]
        self._heart_rate: Optional[float] = None
        self._accel: Optional[dict] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def scan_and_connect(self) -> bool:
        _device_status["mode"] = "searching"
        print("[BLE] Scanning for Muse 2...")
        devices = await BleakScanner.discover(timeout=10.0)
        muse_device = None
        for d in devices:
            name = d.name or ""
            if "Muse" in name or "muse" in name:
                muse_device = d
                print(f"[BLE] Found: {d.name} ({d.address})")
                break

        if not muse_device:
            print("[BLE] No Muse device found.")
            _device_status["mode"] = "error"
            _device_status["error"] = "No Muse device found. Ensure headband is on and BLE is enabled."
            return False

        _device_status["mode"] = "connecting"
        _device_status["device_name"] = muse_device.name

        self.client = BleakClient(muse_device.address, timeout=20.0)
        try:
            await self.client.connect()
            _device_status["connected"] = True
            _device_status["mode"] = "streaming"
            print(f"[BLE] Connected to {muse_device.name}")
            return True
        except Exception as e:
            _device_status["mode"] = "error"
            _device_status["error"] = str(e)
            print(f"[BLE] Connection failed: {e}")
            return False

    def _parse_eeg_packet(self, data: bytearray) -> list[list[float]]:
        """
        Muse EEG packet format (20 bytes):
        [0-1] sequence, [2-19] 12-bit samples, 3 samples per channel × 4 channels × 2 timestamps
        Returns list of {TP9, AF7, AF8, TP10} sample dicts
        """
        n = (len(data) - 2) * 8 // 12
        samples = []
        bit_offset = 16  # skip 2 header bytes
        raw_bits = int.from_bytes(data, "big")
        for i in range(n):
            shift = (len(data) * 8) - bit_offset - 12
            val = (raw_bits >> max(0, shift)) & 0xFFF
            bit_offset += 12
            # Convert 12-bit ADC to µV (Muse calibration: LSB = 0.48828125 µV, offset = -2048)
            uv = (val - 2048) * 0.48828125
            samples.append(uv)

        # Interleaved: TP9, AF7, AF8, TP10 (2 samples each in 12-byte payload)
        frames = []
        ch_names = ["TP9", "AF7", "AF8", "TP10"]
        for i in range(0, len(samples) - 3, 4):
            frame = {ch_names[j]: samples[i + j] for j in range(4)}
            frames.append(frame)
        return frames

    def _parse_accel_packet(self, data: bytearray) -> dict:
        """3-axis accelerometer, big-endian int16 × 3, scale = 1/16384 g"""
        if len(data) < 8:
            return {}
        x = int.from_bytes(data[2:4], "big", signed=True) / 16384.0
        y = int.from_bytes(data[4:6], "big", signed=True) / 16384.0
        z = int.from_bytes(data[6:8], "big", signed=True) / 16384.0
        return {"x": x, "y": y, "z": z, "magnitude": math.sqrt(x**2 + y**2 + z**2)}

    def _parse_ppg_packet(self, data: bytearray) -> Optional[float]:
        """PPG channel 0 (infrared) → crude HR estimation"""
        if len(data) < 4:
            return None
        val = int.from_bytes(data[2:4], "big")
        return float(val)

    def _eeg_callback(self, sender, data: bytearray):
        frames = self._parse_eeg_packet(data)
        for f in frames:
            self._processor.push(f)
            if "AF7" in f and "AF8" in f:
                self._artifacts.push(f["AF7"], f["AF8"])
        _eeg_queue.put_nowait(frames)

    def _accel_callback(self, sender, data: bytearray):
        self._accel = self._parse_accel_packet(data)

    def _ppg_callback(self, sender, data: bytearray):
        val = self._parse_ppg_packet(data)
        if val is not None:
            self._heart_rate = val  # raw — downstream can compute BPM

    async def _subscribe_all(self):
        char_map = {
            MUSE_EEG_CHAR:   self._eeg_callback,
            MUSE_ACCEL_CHAR: self._accel_callback,
            MUSE_PPG_CHAR:   self._ppg_callback,
        }
        for char_uuid, cb in char_map.items():
            try:
                await self.client.start_notify(char_uuid, cb)
                print(f"[BLE] Subscribed to {char_uuid[:8]}...")
            except Exception as e:
                print(f"[BLE] Could not subscribe to {char_uuid[:8]}: {e}")

        # Send Muse control command to start EEG streaming
        try:
            cmd = bytearray([0x02, 0x64, 0x0a])  # "d\n" — start data
            await self.client.write_gatt_char(MUSE_CONTROL_CHAR, cmd)
        except Exception as e:
            print(f"[BLE] Control command failed: {e}")

    async def _publish_loop(self):
        """10 Hz publish loop — compute bands and push to SSE subscribers"""
        while self._running and self.client and self.client.is_connected:
            try:
                bands = self._processor.compute()
                quality = self._processor.signal_quality()
                attention, meditation, drift, distracted, nudge = self._attention.estimate(bands)
                blink, jaw = self._artifacts.detect()

                mean_bands = {}
                for band in BANDS:
                    vals = [bands[ch][band] for ch in CHANNELS if ch in bands]
                    mean_bands[band] = float(np.mean(vals)) if vals else 0.0

                frame = EEGFrame(
                    ts=time.time(),
                    session_id=self._session_id,
                    channels={ch: float(list(self._processor.buffers[ch])[-1])
                               if self._processor.buffers[ch] else 0.0
                               for ch in CHANNELS},
                    bands=bands,
                    mean_bands=mean_bands,
                    attention=attention,
                    meditation=meditation,
                    drift=drift,
                    distracted=distracted,
                    nudge=nudge,
                    blink=blink,
                    jaw_clench=jaw,
                    heart_rate=self._heart_rate,
                    pose=None,   # filled by pose fusion layer
                    accel=self._accel,
                    quality=quality,
                )

                payload = json.dumps(asdict(frame))
                _broadcast(payload)

            except Exception as e:
                print(f"[Publish] Error: {e}")

            await asyncio.sleep(0.1)

    async def run(self):
        self._running = True
        ok = await self.scan_and_connect()
        if not ok:
            return
        await self._subscribe_all()
        print("[BLE] Streaming started.")
        await self._publish_loop()

    def stop(self):
        self._running = False


# ── muselsl fallback (uses pylsl) ─────────────────────────────────────────────
class MuseLSLStreamer:
    """Use muselsl to manage BLE and expose via LSL, then consume LSL inlet."""

    def __init__(self):
        self._processor = BandPowerProcessor()
        self._attention = AttentionEstimator()
        self._artifacts = ArtifactDetector()
        self._session_id = str(uuid.uuid4())[:8]
        self._running = False

    def _find_muse_lsl(self):
        print("[LSL] Resolving EEG stream...")
        streams = resolve_byprop("type", "EEG", timeout=10)
        if not streams:
            return None
        return StreamInlet(streams[0])

    def run(self):
        self._running = True
        inlet = self._find_muse_lsl()
        if not inlet:
            _device_status["mode"] = "error"
            _device_status["error"] = "No LSL EEG stream. Run: python -m muselsl stream"
            return

        info = inlet.info()
        _device_status["connected"] = True
        _device_status["device_name"] = info.name()
        _device_status["mode"] = "streaming"
        print(f"[LSL] Connected: {info.name()}")

        buf = []
        CHUNK = 12  # samples per LSL pull
        while self._running:
            samples, _ = inlet.pull_chunk(timeout=0.1, max_samples=CHUNK)
            for s in samples:
                frame = dict(zip(CHANNELS, s[:4]))
                buf.append(frame)
                self._processor.push(frame)
                if "AF7" in frame and "AF8" in frame:
                    self._artifacts.push(frame["AF7"], frame["AF8"])

            if len(buf) >= 26:  # publish at ~10 Hz
                buf = []
                bands = self._processor.compute()
                quality = self._processor.signal_quality()
                attention, meditation, drift, distracted, nudge = self._attention.estimate(bands)
                blink, jaw = self._artifacts.detect()

                mean_bands = {
                    b: float(np.mean([bands[ch][b] for ch in CHANNELS if ch in bands]))
                    for b in BANDS
                }
                eeg_frame = EEGFrame(
                    ts=time.time(),
                    session_id=self._session_id,
                    channels={ch: float(list(self._processor.buffers[ch])[-1])
                               if self._processor.buffers[ch] else 0.0
                               for ch in CHANNELS},
                    bands=bands,
                    mean_bands=mean_bands,
                    attention=attention,
                    meditation=meditation,
                    drift=drift,
                    distracted=distracted,
                    nudge=nudge,
                    blink=blink,
                    jaw_clench=jaw,
                    heart_rate=None,
                    pose=None,
                    accel=None,
                    quality=quality,
                )
                _broadcast(json.dumps(asdict(eeg_frame)))

    def stop(self):
        self._running = False


# ── SSE broadcast ─────────────────────────────────────────────────────────────
def _broadcast(payload: str):
    msg = f"data: {payload}\n\n"
    dead = []
    with _subscribers_lock:
        for q in _subscribers:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _subscribers.remove(q)


# ── Flask routes ──────────────────────────────────────────────────────────────
@app.route("/api/eeg/live")
def eeg_live():
    """Server-Sent Events endpoint — real-time EEG frames at 10 Hz"""
    q = queue.Queue(maxsize=200)
    with _subscribers_lock:
        _subscribers.append(q)

    def generate():
        # Send device status immediately
        yield f"data: {json.dumps({'type': 'status', **_device_status})}\n\n"
        try:
            while True:
                try:
                    msg = q.get(timeout=15)
                    yield msg
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'heartbeat', 'ts': time.time()})}\n\n"
        finally:
            with _subscribers_lock:
                if q in _subscribers:
                    _subscribers.remove(q)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.route("/api/eeg/status")
def eeg_status():
    return jsonify(_device_status)


@app.route("/api/eeg/nudge", methods=["POST"])
def manual_nudge():
    """Manually trigger a nudge broadcast (teacher can push to student)"""
    data = request.json or {}
    student_id = data.get("student_id", "all")
    message = data.get("message", "Stay focused!")
    payload = json.dumps({
        "type": "nudge",
        "ts": time.time(),
        "student_id": student_id,
        "message": message,
        "manual": True,
    })
    _broadcast(payload)
    return jsonify({"ok": True, "nudged": student_id})


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "device": _device_status,
        "has_muselsl": HAS_MUSELSL,
        "has_bleak": HAS_BLEAK,
        "has_lsl": HAS_LSL,
        "subscribers": len(_subscribers),
    })


# ── Startup ───────────────────────────────────────────────────────────────────
def _start_ble_thread():
    """Run BLE in a dedicated thread with its own event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if HAS_BLEAK:
        streamer = MuseBLEStreamer()
        loop.run_until_complete(streamer.run())
    elif HAS_MUSELSL and HAS_LSL:
        streamer = MuseLSLStreamer()
        streamer.run()
    else:
        _device_status["mode"] = "error"
        _device_status["error"] = (
            "No BLE library found. Install: pip install bleak muselsl pylsl numpy"
        )
        print("[ERROR]", _device_status["error"])


if __name__ == "__main__":
    print("=" * 60)
    print("  GrokEdu EEG Streaming Server v2.0")
    print("  Real Muse 2 BLE  |  Port :9898")
    print("=" * 60)
    print(f"  bleak:    {'✓' if HAS_BLEAK else '✗  pip install bleak'}")
    print(f"  muselsl:  {'✓' if HAS_MUSELSL else '✗  pip install muselsl'}")
    print(f"  pylsl:    {'✓' if HAS_LSL else '✗  pip install pylsl'}")
    print()

    ble_thread = threading.Thread(target=_start_ble_thread, daemon=True)
    ble_thread.start()

    app.run(host="0.0.0.0", port=9898, threaded=True, debug=False)
