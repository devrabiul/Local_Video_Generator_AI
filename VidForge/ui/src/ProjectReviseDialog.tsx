import { useEffect, useState } from 'react';
import { Wand2, RefreshCw, X, AlertTriangle, FileText, Mic, ImageIcon } from 'lucide-react';

export interface RevisableProject {
  id: string;
  title: string;
  status: string;
  scenes?: unknown[];
}

type Mode = "refine" | "regenerate";
type RegenerateMode = "visuals" | "media" | "script";

const REFINE_IDEAS = [
  "Make the opening hook more dramatic",
  "Make the narration shorter and punchier",
  "Change all visuals to a cinematic anime style",
  "Add a stronger ending with a call to action",
];

const REGENERATE_OPTIONS: { id: RegenerateMode; title: string; desc: string; Icon: typeof FileText }[] = [
  { id: "visuals", title: "New visuals", desc: "Keep the script and voiceover. Render fresh images and camera motion.", Icon: ImageIcon },
  { id: "media", title: "New voiceover & visuals", desc: "Keep the script. Re-record the narration and render new images.", Icon: Mic },
  { id: "script", title: "Start over", desc: "Write a brand-new script from your original prompt, then render everything again.", Icon: FileText },
];

interface Props {
  apiBase: string;
  project: RevisableProject;
  initialMode?: Mode;
  onClose: () => void;
  onQueued: () => void;
}

export default function ProjectReviseDialog({ apiBase, project, initialMode = "refine", onClose, onQueued }: Props) {
  const canRefine = (project.scenes?.length || 0) > 0;
  const [mode, setMode] = useState<Mode>(canRefine ? initialMode : "regenerate");
  const [instruction, setInstruction] = useState("");
  const [regenMode, setRegenMode] = useState<RegenerateMode>("visuals");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape" && !isSubmitting) onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, isSubmitting]);

  const submit = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/jobs/${project.id}/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(mode === "refine" ? { instruction: instruction.trim() } : { mode: regenMode }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const detail = Array.isArray(data.detail) ? "Please write a longer instruction." : data.detail;
        throw new Error(detail || "Could not queue the new version");
      }
      onQueued();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not queue the new version");
    } finally {
      setIsSubmitting(false);
    }
  };

  const canSubmit = mode === "regenerate" || instruction.trim().length >= 3;

  return (
    <div className="studio-overlay" role="dialog" aria-modal="true" aria-label="Improve video">
      <div className="glass-panel modal-panel revise-dialog">
        <div className="studio-head">
          <div className="studio-head-title">
            <span className="studio-head-icon"><Wand2 size={17} /></span>
            <div>
              <h3>Improve this video</h3>
              <p title={project.title}>{project.title}</p>
            </div>
          </div>
          <button type="button" className="btn btn-icon btn-ghost" onClick={onClose} aria-label="Close" disabled={isSubmitting}>
            <X size={16} />
          </button>
        </div>

        <div className="revise-body">
          <div className="segmented" role="tablist" aria-label="How to improve">
            <button type="button" role="tab" aria-selected={mode === "refine"} className={`segmented-btn ${mode === "refine" ? 'active' : ''}`} onClick={() => setMode("refine")} disabled={!canRefine}>
              <Wand2 size={13} /> Refine with a prompt
            </button>
            <button type="button" role="tab" aria-selected={mode === "regenerate"} className={`segmented-btn ${mode === "regenerate" ? 'active' : ''}`} onClick={() => setMode("regenerate")}>
              <RefreshCw size={13} /> Regenerate
            </button>
          </div>

          {mode === "refine" ? (
            <>
              <label className="studio-label" htmlFor="refine-instruction">What should change?</label>
              <textarea
                id="refine-instruction"
                rows={4}
                autoFocus
                value={instruction}
                onChange={e => setInstruction(e.target.value)}
                placeholder="e.g. Scene 3 should show the battle at night, and make the narration in the last scene more emotional"
              />
              <div className="studio-chips">
                {REFINE_IDEAS.map(idea => (
                  <button key={idea} type="button" className="chip chip-click" onClick={() => setInstruction(idea)}>{idea}</button>
                ))}
              </div>
              <div className="studio-note">
                The AI edits the script, then only the scenes that changed are re-voiced and re-rendered. Everything else is reused.
              </div>
            </>
          ) : (
            <div className="regen-options" role="radiogroup" aria-label="What to regenerate">
              {REGENERATE_OPTIONS.map(({ id, title, desc, Icon }) => (
                <button
                  key={id}
                  type="button"
                  role="radio"
                  aria-checked={regenMode === id}
                  className={`regen-option ${regenMode === id ? 'active' : ''}`}
                  onClick={() => setRegenMode(id)}
                >
                  <span className="regen-option-icon"><Icon size={16} /></span>
                  <span>
                    <strong>{title}</strong>
                    <span>{desc}</span>
                  </span>
                </button>
              ))}
            </div>
          )}

          <div className="studio-note">Your current video stays available to watch and download until the new version is ready.</div>
        </div>

        {error && <div className="studio-error"><AlertTriangle size={14} /> {error}</div>}

        <div className="studio-foot">
          <div style={{ flex: 1 }} />
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={isSubmitting}>Cancel</button>
          <button type="button" className="btn btn-primary" onClick={submit} disabled={isSubmitting || !canSubmit}>
            {isSubmitting ? <><RefreshCw size={14} className="animate-spin" /> Queuing…</> : mode === "refine" ? <><Wand2 size={14} /> Refine video</> : <><RefreshCw size={14} /> Regenerate video</>}
          </button>
        </div>
      </div>
    </div>
  );
}
