import type React from 'react';
import {
  Workflow, PenLine, Bot, Mic, Image as ImageIcon, Clapperboard, Music, CheckCircle2,
  RefreshCw, Layers, Trash2, AlertTriangle, ArrowRight, Repeat, type LucideIcon,
} from 'lucide-react';

interface Stage {
  status: string;
  title: string;
  engine: string;
  short: string;
  output: string;
  range: [number, number];
  color: string;
  Icon: LucideIcon;
  points: string[];
}

// Mirrors the order and progress bands that backend/worker.py reports for every job
const STAGES: Stage[] = [
  {
    status: 'QUEUED',
    title: 'Your prompt',
    engine: 'Production form or Story Studio',
    short: 'Studio form',
    output: 'Job in the queue',
    range: [0, 10],
    color: 'var(--a-violet)',
    Icon: PenLine,
    points: [
      'You pick the video type, language, length, aspect ratio, voice, motion style, music and subtitles.',
      'The job joins the queue; the worker renders one project at a time.',
      'Scenes already planned in Story & Script Studio skip straight to the voiceover.',
    ],
  },
  {
    status: 'SCRIPTING',
    title: 'Script plan',
    engine: 'Ollama (local LLM)',
    short: 'Ollama LLM',
    output: 'Title + scene list',
    range: [10, 25],
    color: 'var(--a-blue)',
    Icon: Bot,
    points: [
      'The LLM writes a title, narrator style and a list of scenes sized to the target duration.',
      'Each scene gets narration, delivery cues, an image prompt, a camera-motion prompt and a pause.',
      'A revise instruction rewrites only the scenes it touches.',
    ],
  },
  {
    status: 'VOICEOVER',
    title: 'Voiceover',
    engine: 'Gemini TTS · ElevenLabs · F5-TTS / local clone',
    short: 'Gemini · ElevenLabs · F5',
    output: 'Narration audio',
    range: [30, 45],
    color: 'var(--a-green)',
    Icon: Mic,
    points: [
      'Continuous engines read the whole story as one take, then it is split back into scenes at the silences.',
      'Local cloning voices every scene in one batch so the voice stays consistent.',
      'Each clip is padded with its pause and snapped to the video frame grid. Its length sets the scene length.',
    ],
  },
  {
    status: 'GENERATING_IMAGES',
    title: 'Scene images',
    engine: 'ComfyUI · Z-Image-Turbo',
    short: 'ComfyUI · Z-Image-Turbo',
    output: 'Scene still',
    range: [50, 70],
    color: 'var(--a-amber)',
    Icon: ImageIcon,
    points: [
      'One photorealistic still per scene, rendered at the chosen aspect ratio.',
      'The first image also becomes the default thumbnail.',
    ],
  },
  {
    status: 'ANIMATING_VIDEO',
    title: 'Camera motion',
    engine: 'Ultra HD Ken Burns · Wan 2.1 AI motion',
    short: 'Ken Burns · Wan 2.1',
    output: 'Scene clip',
    range: [72, 92],
    color: 'var(--a-rose)',
    Icon: Clapperboard,
    points: [
      'Ken Burns pans and zooms each still with FFmpeg: fast and light on the GPU.',
      'Wan 2.1 generates real AI motion in ComfyUI: slower and needs more VRAM.',
      'Each clip runs exactly as long as its scene audio.',
    ],
  },
  {
    status: 'COMPOSING',
    title: 'Final mix',
    engine: 'FFmpeg',
    short: 'FFmpeg',
    output: 'Video + subtitles',
    range: [94, 99],
    color: 'var(--a-cyan)',
    Icon: Music,
    points: [
      'Clips and narration are joined in order, with transitions.',
      'Background music is mixed under the voice and ducks while someone speaks.',
      'Subtitles are burned in and also saved as a separate .srt file.',
    ],
  },
  {
    status: 'DONE',
    title: 'Ready to watch',
    engine: 'Projects tab',
    short: 'Projects tab',
    output: 'MP4 · SRT · thumbnail',
    range: [100, 100],
    color: 'var(--a-green-bright)',
    Icon: CheckCircle2,
    points: [
      'You get the MP4, the subtitle file and a thumbnail, all saved in the project folder.',
      'Edit the thumbnail in Thumbnail Studio, or revise the script and render again.',
    ],
  },
];

function FlowNode({ stage, step }: { stage: Stage; step: number }) {
  const { Icon } = stage;
  const pct = stage.range[0] === stage.range[1] ? `${stage.range[0]}%` : `${stage.range[0]}–${stage.range[1]}%`;
  return (
    <div className="wf-flow-node" style={{ '--c': stage.color } as React.CSSProperties}>
      <div className="wf-flow-icon"><Icon size={20} strokeWidth={2} /></div>
      <div className="wf-flow-text">
        <div className="wf-flow-title">
          <span className="wf-flow-step">{String(step).padStart(2, '0')}</span>
          {stage.title}
        </div>
        <div className="wf-flow-engine">{stage.short}</div>
        <div className="wf-flow-output"><ArrowRight size={11} /> {stage.output}</div>
      </div>
      <span className="wf-flow-pct">{pct}</span>
    </div>
  );
}

function Link({ vertical, label }: { vertical?: boolean; label?: string }) {
  return (
    <div className={`wf-link ${vertical ? 'vertical' : ''}`} aria-hidden="true">
      <span className="wf-link-line" />
      {label && <span className="wf-link-label">{label}</span>}
    </div>
  );
}

function Phase({ num, title, sub, children, stacked }: { num: string; title: string; sub: string; children: React.ReactNode; stacked?: boolean }) {
  return (
    <div className={`wf-phase ${stacked ? 'stacked' : ''}`}>
      <div className="wf-phase-head">
        <span className="wf-phase-num">{num}</span>
        <div>
          <div className="wf-phase-title">{title}</div>
          <div className="wf-phase-sub">{sub}</div>
        </div>
        {stacked && <span className="wf-phase-badge"><Repeat size={11} /> × N scenes</span>}
      </div>
      <div className="wf-phase-body">{children}</div>
    </div>
  );
}

function PipelineDiagram() {
  const [prompt, script, voice, image, motion, compose, done] = STAGES;
  return (
    <div className="wf-flow" role="img" aria-label="Video generation pipeline: plan (prompt, script), produce for each scene (voiceover, image, camera motion), deliver (final mix, finished video)">
      <Phase num="1" title="Plan" sub="Turn your idea into scenes">
        <FlowNode stage={prompt} step={1} />
        <Link vertical />
        <FlowNode stage={script} step={2} />
      </Phase>

      <Link label="scenes" />

      <Phase num="2" title="Produce" sub="Cached per scene, reused on re-render" stacked>
        <FlowNode stage={voice} step={3} />
        <Link vertical label="sets scene length" />
        <FlowNode stage={image} step={4} />
        <Link vertical />
        <FlowNode stage={motion} step={5} />
      </Phase>

      <Link label="clips" />

      <Phase num="3" title="Deliver" sub="Mix, export and save">
        <FlowNode stage={compose} step={6} />
        <Link vertical />
        <FlowNode stage={done} step={7} />
      </Phase>
    </div>
  );
}

const NOTES: { Icon: LucideIcon; title: string; text: string }[] = [
  {
    Icon: Layers,
    title: 'Smart re-renders',
    text: 'Every audio clip, image and motion clip is saved under a key built from its inputs. When you revise a project, only the scenes whose text, voice or settings changed are rendered again; everything else is reused.',
  },
  {
    Icon: RefreshCw,
    title: 'Resume after a failure',
    text: 'If a step fails (for example ComfyUI or Ollama is not running), the project is marked FAILED with the error. Fix the cause and press Resume; finished assets are kept.',
  },
  {
    Icon: Trash2,
    title: 'Delete mid-render',
    text: 'The worker checks between steps whether the project still exists. Deleting it stops the render and removes its files.',
  },
  {
    Icon: AlertTriangle,
    title: 'What must be running',
    text: 'Ollama for the script, ComfyUI for images and Wan 2.1 motion, and an API key or local model for the voice you picked. FFmpeg handles Ken Burns motion and the final mix.',
  },
];

export default function WorkflowPage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div className="glass-panel page-head">
        <div>
          <h2 className="page-title"><Workflow size={18} color="var(--a-blue)" /> How Video Generation Works</h2>
          <p className="page-sub">
            Every project goes through the same pipeline, from your prompt to a finished MP4.
            The status and percentage you see on a project card tell you which stage it is in.
          </p>
        </div>
      </div>

      <section className="glass-panel wf-diagram-panel">
        <PipelineDiagram />

        <div className="wf-timeline">
          <div className="wf-timeline-head">
            <span>Progress on the project card</span>
            <div className="wf-timeline-legend">
              {STAGES.map(s => (
                <span key={s.status}><i style={{ background: s.color }} />{s.title}</span>
              ))}
            </div>
          </div>
          <div className="wf-progress">
            {STAGES.map(s => (
              <div
                key={s.status}
                className="wf-progress-band"
                style={{ flexGrow: Math.max(s.range[1] - s.range[0], 3), background: s.color }}
                title={`${s.title}: ${s.range[0]}–${s.range[1]}%`}
              />
            ))}
          </div>
          <div className="wf-progress-scale"><span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>
        </div>
      </section>

      <div className="wf-stage-grid">
        {STAGES.map((s, i) => (
          <article key={s.status} className="glass-panel wf-stage" style={{ borderTopColor: s.color }}>
            <header>
              <span className="wf-stage-num" style={{ '--c': s.color } as React.CSSProperties}>{String(i + 1).padStart(2, '0')}</span>
              <div>
                <h3>{s.title}</h3>
                <span className="wf-stage-engine">{s.engine}</span>
              </div>
              <s.Icon size={18} color={s.color} style={{ marginLeft: 'auto', flexShrink: 0 }} />
            </header>
            <code className="wf-stage-status">{s.status}</code>
            <ul>
              {s.points.map(p => <li key={p}>{p}</li>)}
            </ul>
          </article>
        ))}
      </div>

      <div className="wf-notes">
        {NOTES.map(({ Icon, title, text }) => (
          <div key={title} className="glass-panel wf-note-card">
            <Icon size={16} color="var(--a-blue)" />
            <div>
              <strong>{title}</strong>
              <p>{text}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
