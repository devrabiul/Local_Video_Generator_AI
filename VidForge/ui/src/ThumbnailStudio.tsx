import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Image as ImageIcon, X, Sparkles, Wand2, Upload, Download, Save, RefreshCw,
  AlignLeft, AlignCenter, AlignRight, Check, AlertTriangle
} from 'lucide-react';

export interface StudioProject {
  id: string;
  title: string;
  aspect_ratio: string;
  thumbnail_design?: string;
  scenes?: { visual_prompt: string; image_url?: string }[];
}

type Format = "16:9" | "9:16";
type TextStyle = "outline" | "box" | "shadow";
type Position = "top" | "center" | "bottom";
type Align = "left" | "center" | "right";

interface ThumbDesign {
  format: Format;
  background: string;  // server path such as /jobs/<id>/image_x.png
  prompt: string;      // last AI background prompt, kept for further refinement
  headline: string;
  subline: string;
  fontSize: number;    // headline size as % of canvas width
  textColor: string;
  accentColor: string;
  textStyle: TextStyle;
  position: Position;
  align: Align;
  shade: number;       // 0-90, darkening behind the text
}

const CANVAS_SIZE: Record<Format, { w: number; h: number }> = {
  "16:9": { w: 1280, h: 720 },
  "9:16": { w: 1080, h: 1920 },
};

const FONT_STACK = `"Outfit", "Noto Sans Bengali", "Kohinoor Bangla", "Nirmala UI", sans-serif`;

const COLOR_PRESETS = ["#ffffff", "#facc15", "#f43f5e", "#22d3ee", "#34d399", "#111827"];

const REFINE_IDEAS = [
  "Make it darker and more dramatic",
  "Close-up of the main character's face",
  "Add a glowing sunset sky",
  "Leave empty space on the left for text",
];

const THUMB_PROMPT_SUFFIX = ", bold YouTube thumbnail composition, single clear focal subject, dramatic rim lighting, high contrast, vivid colors, clean negative space for a headline, no text";

function defaultDesign(project: StudioProject): ThumbDesign {
  const scenes = project.scenes || [];
  return {
    format: project.aspect_ratio === "9:16" ? "9:16" : "16:9",
    background: scenes.find(s => s.image_url)?.image_url || "",
    prompt: scenes[0]?.visual_prompt ? scenes[0].visual_prompt + THUMB_PROMPT_SUFFIX : "",
    headline: project.title,
    subline: "",
    fontSize: 9,
    textColor: "#ffffff",
    accentColor: "#facc15",
    textStyle: "outline",
    position: "bottom",
    align: "center",
    shade: 55,
  };
}

function loadDesign(project: StudioProject): ThumbDesign {
  const base = defaultDesign(project);
  try {
    return project.thumbnail_design ? { ...base, ...JSON.parse(project.thumbnail_design) } : base;
  } catch {
    return base;
  }
}

function wrapLines(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const lines: string[] = [];
  for (const paragraph of text.split("\n")) {
    let line = "";
    for (const word of paragraph.split(/\s+/).filter(Boolean)) {
      const next = line ? `${line} ${word}` : word;
      if (line && ctx.measureText(next).width > maxWidth) {
        lines.push(line);
        line = word;
      } else {
        line = next;
      }
    }
    if (line) lines.push(line);
  }
  return lines;
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    // CORS-enabled load keeps the canvas exportable; the query avoids a cached non-CORS copy
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Could not load the background image"));
    img.src = src + (src.includes("?") ? "&" : "?") + "cors=1";
  });
}

function drawThumbnail(canvas: HTMLCanvasElement, d: ThumbDesign, img: HTMLImageElement | null) {
  const { w, h } = CANVAS_SIZE[d.format];
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d")!;

  ctx.fillStyle = "#0b0f1a";
  ctx.fillRect(0, 0, w, h);
  if (img) {
    const scale = Math.max(w / img.naturalWidth, h / img.naturalHeight);
    const iw = img.naturalWidth * scale;
    const ih = img.naturalHeight * scale;
    ctx.drawImage(img, (w - iw) / 2, (h - ih) / 2, iw, ih);
  }

  // Darken the side of the frame that carries the text so it stays readable
  const shade = d.shade / 100;
  if (shade > 0) {
    let grad: CanvasGradient;
    if (d.position === "top") grad = ctx.createLinearGradient(0, 0, 0, h * 0.65);
    else if (d.position === "bottom") grad = ctx.createLinearGradient(0, h, 0, h * 0.35);
    else grad = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, Math.max(w, h) * 0.6);
    grad.addColorStop(0, `rgba(0,0,0,${shade})`);
    grad.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = d.position === "center" ? `rgba(0,0,0,${shade * 0.6})` : grad;
    ctx.fillRect(0, 0, w, h);
  }

  const pad = w * 0.06;
  const maxWidth = w - pad * 2;
  const headPx = Math.round(w * d.fontSize / 100);
  const subPx = Math.round(headPx * 0.42);
  ctx.font = `800 ${headPx}px ${FONT_STACK}`;
  const headLines = d.headline.trim() ? wrapLines(ctx, d.headline.trim(), maxWidth) : [];
  ctx.font = `700 ${subPx}px ${FONT_STACK}`;
  const subLines = d.subline.trim() ? wrapLines(ctx, d.subline.trim(), maxWidth) : [];

  const headLH = headPx * 1.18;
  const subLH = subPx * 1.3;
  const gap = headLines.length && subLines.length ? subPx * 0.6 : 0;
  const blockH = headLines.length * headLH + gap + subLines.length * subLH;
  let y = d.position === "top" ? pad : d.position === "bottom" ? h - pad - blockH : (h - blockH) / 2;

  const x = d.align === "left" ? pad : d.align === "right" ? w - pad : w / 2;
  ctx.textAlign = d.align;
  ctx.textBaseline = "top";
  ctx.lineJoin = "round";

  // Headline: text color (on an accent box in "box" style). Sub-headline: accent color (on a dark box).
  const drawLine = (text: string, role: "head" | "sub") => {
    const px = role === "head" ? headPx : subPx;
    const lh = role === "head" ? headLH : subLH;
    const color = role === "head" ? d.textColor : d.accentColor;
    ctx.font = `${role === "head" ? 800 : 700} ${px}px ${FONT_STACK}`;
    const ty = y + (lh - px) / 2;
    ctx.save();
    if (d.textStyle === "box") {
      const tw = ctx.measureText(text).width;
      const bx = d.align === "left" ? x : d.align === "right" ? x - tw : x - tw / 2;
      const padX = px * 0.28;
      ctx.fillStyle = role === "head" ? d.accentColor : "rgba(0,0,0,0.75)";
      ctx.beginPath();
      ctx.roundRect(bx - padX, y + lh * 0.04, tw + padX * 2, lh * 0.94, px * 0.14);
      ctx.fill();
      ctx.fillStyle = role === "head" && d.textColor === d.accentColor ? "#111827" : color;
      ctx.fillText(text, x, ty);
    } else {
      if (d.textStyle === "shadow") {
        ctx.shadowColor = "rgba(0,0,0,0.85)";
        ctx.shadowBlur = px * 0.35;
        ctx.shadowOffsetY = px * 0.06;
      } else {
        ctx.strokeStyle = "#000000";
        ctx.lineWidth = Math.max(4, px * 0.14);
        ctx.strokeText(text, x, ty);
      }
      ctx.fillStyle = color;
      ctx.fillText(text, x, ty);
    }
    ctx.restore();
    y += lh;
  };

  headLines.forEach(line => drawLine(line, "head"));
  y += gap;
  subLines.forEach(line => drawLine(line, "sub"));
}

interface Props {
  apiBase: string;
  project: StudioProject;
  onClose: () => void;
  onSaved: () => void;
}

export default function ThumbnailStudio({ apiBase, project, onClose, onSaved }: Props) {
  const [design, setDesign] = useState<ThumbDesign>(() => loadDesign(project));
  const [savedBackgrounds, setSavedBackgrounds] = useState<string[]>([]);
  const [bgImage, setBgImage] = useState<HTMLImageElement | null>(null);
  const [bgError, setBgError] = useState<string | null>(null);
  const [instruction, setInstruction] = useState("");
  const [aiBusy, setAiBusy] = useState<"generate" | "refine" | "headlines" | null>(null);
  const [headlineIdeas, setHeadlineIdeas] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  const set = (patch: Partial<ThumbDesign>) => setDesign(d => ({ ...d, ...patch }));
  const endpoint = `${apiBase}/api/jobs/${project.id}/thumbnail`;

  const sceneBackgrounds = useMemo(
    () => [...new Set((project.scenes || []).map(s => s.image_url).filter((u): u is string => !!u))],
    [project.scenes]
  );

  useEffect(() => {
    fetch(`${endpoint}/backgrounds`)
      .then(r => (r.ok ? r.json() : { backgrounds: [] }))
      .then(data => setSavedBackgrounds(data.backgrounds || []))
      .catch(() => setSavedBackgrounds([]));
  }, [endpoint]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape" && !isSaving) onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, isSaving]);

  useEffect(() => {
    let cancelled = false;
    setBgError(null);
    if (!design.background) {
      setBgImage(null);
      return;
    }
    loadImage(`${apiBase}${design.background}`)
      .then(img => { if (!cancelled) setBgImage(img); })
      .catch(e => { if (!cancelled) { setBgImage(null); setBgError(e.message); } });
    return () => { cancelled = true; };
  }, [apiBase, design.background]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    let cancelled = false;
    const text = `${design.headline} ${design.subline}`;
    // Wait for the web fonts so Bengali glyphs aren't drawn with a fallback face
    Promise.all([
      document.fonts.load(`800 40px ${FONT_STACK}`, text),
      document.fonts.load(`700 40px ${FONT_STACK}`, text),
    ]).catch(() => undefined).then(() => {
      if (!cancelled) drawThumbnail(canvas, design, bgImage);
    });
    return () => { cancelled = true; };
  }, [design, bgImage]);

  const requestBackground = async (mode: "generate" | "refine") => {
    setAiBusy(mode);
    setError(null);
    try {
      const res = await fetch(`${endpoint}/backgrounds`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: design.prompt,
          instruction: mode === "refine" ? instruction : "",
          aspect_ratio: design.format,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Background generation failed");
      setSavedBackgrounds(prev => [data.url, ...prev]);
      set({ background: data.url, prompt: data.prompt });
      if (mode === "refine") setInstruction("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Background generation failed");
    } finally {
      setAiBusy(null);
    }
  };

  const uploadBackground = async (file: File) => {
    setError(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${endpoint}/backgrounds/upload`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      setSavedBackgrounds(prev => [data.url, ...prev]);
      set({ background: data.url });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    }
  };

  const suggestHeadlines = async () => {
    setAiBusy("headlines");
    setError(null);
    try {
      const res = await fetch(`${endpoint}/headlines`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not suggest headlines");
      setHeadlineIdeas(data.headlines || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not suggest headlines");
    } finally {
      setAiBusy(null);
    }
  };

  const exportBlob = () => new Promise<Blob>((resolve, reject) => {
    const canvas = canvasRef.current;
    if (!canvas) return reject(new Error("Preview is not ready"));
    try {
      canvas.toBlob(b => (b ? resolve(b) : reject(new Error("Could not export the thumbnail"))), "image/jpeg", 0.92);
    } catch {
      reject(new Error("This background can't be exported. Pick or generate another one."));
    }
  });

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const blob = await exportBlob();
      const form = new FormData();
      form.append("file", blob, "thumbnail.jpg");
      form.append("design", JSON.stringify(design));
      const res = await fetch(endpoint, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Saving failed");
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Saving failed");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDownload = async () => {
    try {
      const url = URL.createObjectURL(await exportBlob());
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project.title.replace(/[\\/:*?"<>|.]+/g, "").trim() || "thumbnail"}_thumbnail.jpg`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed");
    }
  };

  const backgroundTile = (url: string) => (
    <button
      key={url}
      type="button"
      className={`thumb-bg-tile ${design.background === url ? 'active' : ''}`}
      onClick={() => set({ background: url })}
      aria-label="Use this background"
      aria-pressed={design.background === url}
    >
      <img src={`${apiBase}${url}`} alt="" loading="lazy" />
      {design.background === url && <span className="thumb-bg-check"><Check size={12} /></span>}
    </button>
  );

  const preview = CANVAS_SIZE[design.format];

  return (
    <div className="studio-overlay" role="dialog" aria-modal="true" aria-label="Thumbnail Studio">
      <div className="glass-panel modal-panel thumb-studio">
        <div className="studio-head">
          <div className="studio-head-title">
            <span className="studio-head-icon"><ImageIcon size={17} /></span>
            <div>
              <h3>Thumbnail Studio</h3>
              <p title={project.title}>{project.title}</p>
            </div>
          </div>
          <button type="button" className="btn btn-icon btn-ghost" onClick={onClose} aria-label="Close" disabled={isSaving}>
            <X size={16} />
          </button>
        </div>

        <div className="thumb-studio-body">
          <div className="thumb-preview-col">
            <div className="thumb-preview-frame" style={{ aspectRatio: `${preview.w} / ${preview.h}` }}>
              <canvas ref={canvasRef} className="thumb-canvas" />
            </div>
            {bgError && <div className="studio-note studio-note-warn"><AlertTriangle size={13} /> {bgError}</div>}
            <div className="segmented" role="group" aria-label="Thumbnail format">
              {(["16:9", "9:16"] as Format[]).map(f => (
                <button key={f} type="button" className={`segmented-btn ${design.format === f ? 'active' : ''}`} onClick={() => set({ format: f })}>
                  {f === "16:9" ? "16:9 · YouTube" : "9:16 · Shorts / Reels"}
                </button>
              ))}
            </div>
          </div>

          <div className="thumb-controls">
            <section className="studio-section">
              <div className="studio-section-title">Background</div>
              {sceneBackgrounds.length + savedBackgrounds.length > 0 ? (
                <div className="thumb-bg-grid">
                  {[...savedBackgrounds, ...sceneBackgrounds].map(backgroundTile)}
                </div>
              ) : (
                <div className="studio-note">No images yet. Generate one with AI or upload your own.</div>
              )}
              <input
                ref={fileRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                hidden
                onChange={e => { const f = e.target.files?.[0]; if (f) uploadBackground(f); e.target.value = ""; }}
              />
              <button type="button" className="btn btn-ghost" onClick={() => fileRef.current?.click()}>
                <Upload size={14} /> Upload image
              </button>
            </section>

            <section className="studio-section">
              <div className="studio-section-title">AI background</div>
              <label className="studio-label" htmlFor="thumb-prompt">Image prompt</label>
              <textarea
                id="thumb-prompt"
                rows={3}
                value={design.prompt}
                onChange={e => set({ prompt: e.target.value })}
                placeholder="Describe the image you want behind the headline"
              />
              <button type="button" className="btn btn-primary" onClick={() => requestBackground("generate")} disabled={!!aiBusy || !design.prompt.trim()}>
                {aiBusy === "generate" ? <><RefreshCw size={14} className="animate-spin" /> Generating…</> : <><Sparkles size={14} /> {savedBackgrounds.length ? "Regenerate" : "Generate"} background</>}
              </button>

              <label className="studio-label" htmlFor="thumb-refine">Not quite right? Describe the change</label>
              <div className="studio-inline">
                <input
                  id="thumb-refine"
                  value={instruction}
                  onChange={e => setInstruction(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter" && instruction.trim() && !aiBusy) requestBackground("refine"); }}
                  placeholder="e.g. make the sky stormy and add a castle"
                />
                <button type="button" className="btn btn-secondary-soft" onClick={() => requestBackground("refine")} disabled={!!aiBusy || !instruction.trim()}>
                  {aiBusy === "refine" ? <RefreshCw size={14} className="animate-spin" /> : <Wand2 size={14} />} Refine
                </button>
              </div>
              <div className="studio-chips">
                {REFINE_IDEAS.map(idea => (
                  <button key={idea} type="button" className="chip chip-click" onClick={() => setInstruction(idea)}>{idea}</button>
                ))}
              </div>
              {aiBusy && aiBusy !== "headlines" && (
                <div className="studio-note">Ollama rewrites the prompt, then ComfyUI renders it. This can take up to a minute.</div>
              )}
            </section>

            <section className="studio-section">
              <div className="studio-section-title">Text</div>
              <label className="studio-label" htmlFor="thumb-headline">Headline</label>
              <div className="studio-inline">
                <textarea id="thumb-headline" rows={2} value={design.headline} onChange={e => set({ headline: e.target.value })} placeholder="Big, short, curiosity-driven" />
                <button type="button" className="btn btn-ghost" onClick={suggestHeadlines} disabled={!!aiBusy} title="Suggest headlines with AI">
                  {aiBusy === "headlines" ? <RefreshCw size={14} className="animate-spin" /> : <Sparkles size={14} />} Suggest
                </button>
              </div>
              {headlineIdeas.length > 0 && (
                <div className="studio-chips">
                  {headlineIdeas.map(h => (
                    <button key={h} type="button" className={`chip chip-click ${design.headline === h ? 'chip-primary' : ''}`} onClick={() => set({ headline: h })}>{h}</button>
                  ))}
                </div>
              )}
              <label className="studio-label" htmlFor="thumb-subline">Sub-headline (optional)</label>
              <input id="thumb-subline" value={design.subline} onChange={e => set({ subline: e.target.value })} placeholder="e.g. PART 1 · The untold story" />

              <div className="studio-grid-2">
                <div>
                  <span className="studio-label">Style</span>
                  <div className="segmented" role="group" aria-label="Text style">
                    {(["outline", "box", "shadow"] as TextStyle[]).map(s => (
                      <button key={s} type="button" className={`segmented-btn ${design.textStyle === s ? 'active' : ''}`} onClick={() => set({ textStyle: s })}>{s[0].toUpperCase() + s.slice(1)}</button>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="studio-label">Position</span>
                  <div className="segmented" role="group" aria-label="Text position">
                    {(["top", "center", "bottom"] as Position[]).map(p => (
                      <button key={p} type="button" className={`segmented-btn ${design.position === p ? 'active' : ''}`} onClick={() => set({ position: p })}>{p[0].toUpperCase() + p.slice(1)}</button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="studio-grid-2">
                <div>
                  <span className="studio-label">Alignment</span>
                  <div className="segmented" role="group" aria-label="Text alignment">
                    {([["left", AlignLeft], ["center", AlignCenter], ["right", AlignRight]] as const).map(([a, Icon]) => (
                      <button key={a} type="button" className={`segmented-btn ${design.align === a ? 'active' : ''}`} onClick={() => set({ align: a })} aria-label={`Align ${a}`}><Icon size={14} /></button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="studio-label" htmlFor="thumb-size">Text size · {design.fontSize}%</label>
                  <input id="thumb-size" type="range" min={4} max={16} step={0.5} value={design.fontSize} onChange={e => set({ fontSize: Number(e.target.value) })} />
                </div>
              </div>

              <div className="studio-grid-2">
                {([["textColor", "Headline color"], ["accentColor", "Accent color"]] as const).map(([key, label]) => (
                  <div key={key}>
                    <span className="studio-label">{label}</span>
                    <div className="swatch-row">
                      {COLOR_PRESETS.map(c => (
                        <button
                          key={c}
                          type="button"
                          className={`swatch ${design[key] === c ? 'active' : ''}`}
                          style={{ background: c }}
                          onClick={() => set({ [key]: c })}
                          aria-label={`${label} ${c}`}
                        />
                      ))}
                      <input type="color" value={design[key]} onChange={e => set({ [key]: e.target.value })} aria-label={`Custom ${label.toLowerCase()}`} />
                    </div>
                  </div>
                ))}
              </div>

              <label className="studio-label" htmlFor="thumb-shade">Background shade · {design.shade}%</label>
              <input id="thumb-shade" type="range" min={0} max={90} step={5} value={design.shade} onChange={e => set({ shade: Number(e.target.value) })} />
            </section>
          </div>
        </div>

        {error && <div className="studio-error"><AlertTriangle size={14} /> {error}</div>}

        <div className="studio-foot">
          <button type="button" className="btn btn-ghost" onClick={() => setDesign(defaultDesign(project))} disabled={isSaving}>
            Reset
          </button>
          <div style={{ flex: 1 }} />
          <button type="button" className="btn btn-ghost" onClick={handleDownload} disabled={isSaving}>
            <Download size={14} /> Download
          </button>
          <button type="button" className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
            {isSaving ? <><RefreshCw size={14} className="animate-spin" /> Saving…</> : <><Save size={14} /> Save to project</>}
          </button>
        </div>
      </div>
    </div>
  );
}
