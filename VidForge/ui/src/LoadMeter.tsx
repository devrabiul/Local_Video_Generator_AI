import { Gauge } from 'lucide-react';

export type LoadLevel = "low" | "med" | "high";

export interface LoadOptions {
  duration: number;
  motion: "kenburns" | "wan" | "static";
  resolution: 480 | 720 | 1080 | 1440;
  fps: 24 | 25 | 30 | 60;
  voice: "gemini" | "elevenlabs" | "f5tts";
  subtitles: boolean;
}

interface LoadFactor {
  key: string;
  label: string;
  choice: string;
  points: number;
  max: number;
}

// Relative weights tuned so the heaviest combination totals 100. Cloud voices cost nothing locally;
// Wan 2.1 animates every scene on the GPU, so its cost grows with duration.
const RES_POINTS = { 480: 2, 720: 5, 1080: 9, 1440: 15 } as const;
const FPS_POINTS = { 24: 3, 25: 3, 30: 5, 60: 12 } as const;
const VOICE_POINTS = { gemini: 1, elevenlabs: 1, f5tts: 10 } as const;
const VOICE_LABELS = { gemini: 'Gemini (cloud)', elevenlabs: 'ElevenLabs (cloud)', f5tts: 'Local voice (GPU)' } as const;
const MOTION_LABELS = { kenburns: 'Ken Burns', wan: 'Wan 2.1 AI', static: 'Static' } as const;

const durationFrac = (sec: number) => Math.min(1, Math.max(0, (sec - 15) / 345));

export const durationPoints = (sec: number) => Math.round(2 + durationFrac(sec) * 23);
export const motionPoints = (motion: LoadOptions["motion"], sec: number) =>
  motion === 'wan' ? Math.round(20 + durationFrac(sec) * 15) : motion === 'kenburns' ? 8 : 2;

/** Per-option load level, for the coloured dot next to each choice. */
export const optionLoad = {
  duration: (sec: number): LoadLevel => (sec <= 60 ? 'low' : sec <= 180 ? 'med' : 'high'),
  motion: (m: LoadOptions["motion"]): LoadLevel => (m === 'wan' ? 'high' : 'low'),
  resolution: (r: LoadOptions["resolution"]): LoadLevel => (r <= 720 ? 'low' : r === 1080 ? 'med' : 'high'),
  fps: (f: LoadOptions["fps"]): LoadLevel => (f <= 25 ? 'low' : f === 30 ? 'med' : 'high'),
  voice: (v: LoadOptions["voice"]): LoadLevel => (v === 'f5tts' ? 'med' : 'low'),
};

export function LoadDot({ level }: { level: LoadLevel }) {
  const text = level === 'low' ? 'Low system load' : level === 'med' ? 'Medium system load' : 'High system load';
  return <span className={`load-dot load-dot-${level}`} title={text} aria-label={text} role="img" />;
}

export function estimateLoad(o: LoadOptions) {
  const factors: LoadFactor[] = [
    { key: 'motion', label: 'Motion', choice: MOTION_LABELS[o.motion], points: motionPoints(o.motion, o.duration), max: 35 },
    { key: 'duration', label: 'Duration', choice: o.duration >= 60 ? `${Math.round(o.duration / 6) / 10} min` : `${o.duration}s`, points: durationPoints(o.duration), max: 25 },
    { key: 'resolution', label: 'Resolution', choice: `${o.resolution}p`, points: RES_POINTS[o.resolution], max: 15 },
    { key: 'fps', label: 'Frame rate', choice: `${o.fps} fps`, points: FPS_POINTS[o.fps], max: 12 },
    { key: 'voice', label: 'Voice', choice: VOICE_LABELS[o.voice], points: VOICE_POINTS[o.voice], max: 10 },
    { key: 'subtitles', label: 'Subtitles', choice: o.subtitles ? 'Burned in' : 'Off', points: o.subtitles ? 3 : 0, max: 3 },
  ];
  const score = Math.min(100, factors.reduce((sum, f) => sum + f.points, 0));
  return { score, factors };
}

// Six-step scale, light green → dark red; `ink` is the label text colour on that background
const LEVELS = [
  { upTo: 20, label: 'Very light', note: 'Quick render; barely touches the GPU', color: 'var(--load-1)', ink: '#052e16' },
  { upTo: 35, label: 'Light', note: 'Runs comfortably alongside other apps', color: 'var(--load-2)', ink: '#ffffff' },
  { upTo: 50, label: 'Moderate', note: 'Typical render; GPU busy for a while', color: 'var(--load-3)', ink: '#422006' },
  { upTo: 65, label: 'Heavy', note: 'Long render; avoid other GPU work meanwhile', color: 'var(--load-4)', ink: '#ffffff' },
  { upTo: 80, label: 'Very heavy', note: 'Very long render; GPU fully loaded', color: 'var(--load-5)', ink: '#ffffff' },
  { upTo: 101, label: 'Extreme', note: 'Slowest render; may run out of VRAM', color: 'var(--load-6)', ink: '#ffffff' },
];

const levelFor = (percent: number) => LEVELS.find(l => percent < l.upTo)!;

export function LoadMeter({ options, vramTotalGb }: { options: LoadOptions; vramTotalGb?: number | null }) {
  const { score, factors } = estimateLoad(options);
  const level = levelFor(score);
  const top = [...factors].sort((a, b) => b.points / b.max - a.points / a.max)[0];
  const lowVramWan = options.motion === 'wan' && vramTotalGb != null && vramTotalGb < 16;

  return (
    <div className="load-meter" role="status" aria-live="polite">
      <div className="load-meter-head">
        <span className="load-meter-title"><Gauge size={14} /> System load</span>
        <span className="load-meter-level" style={{ background: level.color, color: level.ink }}>{level.label} · {score}%</span>
      </div>
      <div className="load-meter-track">
        <div className="load-meter-fill" style={{ width: `${Math.max(4, score)}%`, background: level.color }} />
      </div>
      <div className="load-meter-note">
        {level.note}
        {score >= 50 && top.points / top.max >= 0.5 && <> · Biggest factor: <strong>{top.label} ({top.choice})</strong></>}
      </div>
      {lowVramWan && (
        <div className="load-meter-warn">Wan 2.1 on a {vramTotalGb} GB GPU will offload to system RAM and render much slower.</div>
      )}
      <div className="load-meter-factors">
        {factors.map(f => (
          <div key={f.key} className="load-factor" title={`${f.label}: ${f.choice}`}>
            <span className="load-factor-label">{f.label}</span>
            <span className="load-factor-bar">
              <span style={{ width: `${(f.points / f.max) * 100}%`, background: levelFor((f.points / f.max) * 100).color }} />
            </span>
          </div>
        ))}
      </div>
      <div className="load-meter-legend">
        <span><LoadDot level="low" /> Low</span>
        <span><LoadDot level="med" /> Medium</span>
        <span><LoadDot level="high" /> High</span>
        <span className="load-meter-legend-hint">dots mark each option's load</span>
      </div>
    </div>
  );
}
