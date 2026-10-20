import { useEffect, useRef, useState } from 'react';
import { Music, Play, Pause, Check, RotateCcw, Volume2, Mic } from 'lucide-react';

export interface MusicTrack {
  id: string;
  title: string;
  category: string;
  duration: number;
  url: string;
}

export interface MusicSettings {
  enabled: boolean;
  track: string;      // track id, "" = none picked yet
  musicVolume: number; // % of the auto-balanced level (100 = auto)
  voiceVolume: number; // % of the normalised narration level
  ducking: boolean;
}

export const DEFAULT_MUSIC_SETTINGS: MusicSettings = {
  enabled: false,
  track: "",
  musicVolume: 100,
  voiceVolume: 100,
  ducking: true,
};

const formatTime = (sec: number) => {
  if (!Number.isFinite(sec) || sec <= 0) return "0:00";
  const s = Math.round(sec);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};

// Level relative to the auto balance, shown in dB so "louder/quieter" is concrete
const levelLabel = (pct: number) => {
  if (pct === 100) return "Auto";
  if (pct === 0) return "Muted";
  const db = 20 * Math.log10(pct / 100);
  return `${db > 0 ? "+" : ""}${db.toFixed(1)} dB`;
};

interface Props {
  apiBase: string;
  tracks: MusicTrack[];
  value: MusicSettings;
  onChange: (next: MusicSettings) => void;
  loadFailed?: boolean;
  onRetry?: () => void;
}

export default function BackgroundMusicPicker({ apiBase, tracks, value, onChange, loadFailed, onRetry }: Props) {
  const [category, setCategory] = useState<string>("All");
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [progress, setProgress] = useState({ current: 0, duration: 0 });
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const set = (patch: Partial<MusicSettings>) => onChange({ ...value, ...patch });

  const stopPreview = () => {
    audioRef.current?.pause();
    audioRef.current = null;
    setPreviewId(null);
    setProgress({ current: 0, duration: 0 });
  };

  // Stop previewing when the feature is switched off or the picker unmounts
  useEffect(() => { if (!value.enabled) stopPreview(); }, [value.enabled]);
  useEffect(() => () => { audioRef.current?.pause(); }, []);

  const togglePreview = (track: MusicTrack) => {
    if (previewId === track.id) { stopPreview(); return; }
    audioRef.current?.pause();
    const audio = new Audio(`${apiBase}${track.url}`);
    audio.volume = 0.8;
    audio.ontimeupdate = () => setProgress({ current: audio.currentTime, duration: audio.duration || track.duration });
    audio.onended = stopPreview;
    audio.onerror = stopPreview;
    audioRef.current = audio;
    setPreviewId(track.id);
    setProgress({ current: 0, duration: track.duration });
    audio.play().catch(stopPreview);
  };

  const seekPreview = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio || !progress.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    audio.currentTime = ((e.clientX - rect.left) / rect.width) * progress.duration;
  };

  const categories = ["All", ...Array.from(new Set(tracks.map(t => t.category)))];
  const visible = category === "All" ? tracks : tracks.filter(t => t.category === category);
  const selected = tracks.find(t => t.id === value.track);
  const isAuto = value.musicVolume === 100 && value.voiceVolume === 100 && value.ducking;

  return (
    <div className="music-picker">
      <div className="music-head">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
          <span className="music-head-icon"><Music size={15} /></span>
          <div style={{ minWidth: 0 }}>
            <div className="music-head-title">ব্যাকগ্রাউন্ড মিউজিক (No Copyright Music)</div>
            <div className="music-head-sub">
              {value.enabled
                ? (selected ? `Selected: ${selected.title}` : 'একটি ট্র্যাক বেছে নিন — না বাছলে ভিডিওতে মিউজিক থাকবে না')
                : 'ঐচ্ছিক — বন্ধ থাকলে ভিডিওতে শুধু কণ্ঠ থাকবে'}
            </div>
          </div>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={value.enabled}
          aria-label="Add background music"
          className={`switch ${value.enabled ? 'on' : ''}`}
          onClick={() => set({ enabled: !value.enabled })}
        >
          <span />
        </button>
      </div>

      {value.enabled && (
        <>
          {tracks.length === 0 ? (
            <div className="music-empty">
              {loadFailed
                ? 'Could not load the music library from the backend. Restart the backend if it was started before this feature was added.'
                : <>No tracks found. Add audio files to <code>VidForge/No_Copyright_Music/&lt;Category&gt;/</code>.</>}
              {onRetry && (
                <button type="button" className="chip-btn" style={{ marginLeft: 8 }} onClick={onRetry}>
                  <RotateCcw size={11} /> Retry
                </button>
              )}
            </div>
          ) : (
            <>
              <div className="music-categories">
                {categories.map(c => (
                  <button
                    key={c}
                    type="button"
                    className={`chip-btn ${category === c ? 'active' : ''}`}
                    onClick={() => setCategory(c)}
                  >
                    {c}
                    <span>{c === "All" ? tracks.length : tracks.filter(t => t.category === c).length}</span>
                  </button>
                ))}
              </div>

              <ul className="music-list">
                {visible.map(track => {
                  const isPreviewing = previewId === track.id;
                  const isSelected = value.track === track.id;
                  return (
                    <li key={track.id} className={`music-row ${isSelected ? 'selected' : ''} ${isPreviewing ? 'playing' : ''}`}>
                      <button
                        type="button"
                        className="music-play"
                        onClick={() => togglePreview(track)}
                        aria-label={isPreviewing ? `Stop preview of ${track.title}` : `Preview ${track.title}`}
                      >
                        {isPreviewing ? <Pause size={14} /> : <Play size={14} />}
                      </button>
                      <div className="music-info">
                        <div className="music-title" title={track.title}>{track.title}</div>
                        {isPreviewing ? (
                          <div className="music-progress-row">
                            <div className="music-progress" onClick={seekPreview} role="presentation">
                              <div style={{ width: `${progress.duration ? (progress.current / progress.duration) * 100 : 0}%` }} />
                            </div>
                            <span>{formatTime(progress.current)} / {formatTime(progress.duration)}</span>
                          </div>
                        ) : (
                          <div className="music-meta">{track.category} · {formatTime(track.duration)}</div>
                        )}
                      </div>
                      <button
                        type="button"
                        className={`btn ${isSelected ? 'btn-primary' : 'btn-ghost'} music-select`}
                        aria-pressed={isSelected}
                        onClick={() => set({ track: isSelected ? "" : track.id })}
                      >
                        {isSelected ? <><Check size={13} /> Selected</> : 'Use'}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </>
          )}

          {/* Mix balance */}
          <div className="music-mix">
            <div className="music-mix-head">
              <span>অডিও ব্যালান্স (Mix)</span>
              <button
                type="button"
                className={`chip-btn ${isAuto ? 'active' : ''}`}
                onClick={() => set({ musicVolume: 100, voiceVolume: 100, ducking: true })}
                title="Voice normalised to broadcast level, music placed well below it, ducked while the narrator speaks"
              >
                <RotateCcw size={11} /> Auto balance
              </button>
            </div>

            <label className="mix-row">
              <span className="mix-label"><Music size={13} /> Music</span>
              <input
                type="range"
                className="mix-range"
                min={0}
                max={200}
                step={5}
                value={value.musicVolume}
                onChange={e => set({ musicVolume: Number(e.target.value) })}
                style={{ '--fill': `${value.musicVolume / 2}%` } as React.CSSProperties}
              />
              <span className="mix-value">{levelLabel(value.musicVolume)}</span>
            </label>

            <label className="mix-row">
              <span className="mix-label"><Mic size={13} /> Voice</span>
              <input
                type="range"
                className="mix-range"
                min={50}
                max={150}
                step={5}
                value={value.voiceVolume}
                onChange={e => set({ voiceVolume: Number(e.target.value) })}
                style={{ '--fill': `${value.voiceVolume - 50}%` } as React.CSSProperties}
              />
              <span className="mix-value">{levelLabel(value.voiceVolume)}</span>
            </label>

            <label className="mix-toggle">
              <input type="checkbox" checked={value.ducking} onChange={e => set({ ducking: e.target.checked })} />
              <span>
                <strong><Volume2 size={12} /> Smart ducking</strong>
                কথা বলার সময় মিউজিক স্বয়ংক্রিয়ভাবে কমে যায়, যাতে কণ্ঠ পরিষ্কার থাকে
              </span>
            </label>
          </div>
        </>
      )}
    </div>
  );
}
