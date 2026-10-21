import type React from 'react';
import {
  Workflow, PenLine, Bot, Mic, Image as ImageIcon, Clapperboard, Music, CheckCircle2,
  RefreshCw, Layers, Trash2, AlertTriangle, ArrowRight, Repeat, Globe, Mail, Briefcase, UserRound, Film, Languages, ShieldCheck, Sparkles, FolderOpen, Wand2, type LucideIcon,
} from 'lucide-react';
import authorPhoto from './assets/author.webp';

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
    title: 'Master Audio First',
    engine: 'Gemini TTS · ElevenLabs · OmniVoice / F5-TTS',
    short: 'Master Audio First',
    output: 'Master Audio Track',
    range: [30, 45],
    color: 'var(--a-green)',
    Icon: Mic,
    points: [
      'The entire story narrative and dialogue are recorded as ONE complete, continuous master audio performance first.',
      'Natural conversational cadence: no robotic stop-start line-by-line takes or artificial dead silences between scenes.',
      'The master audio track drives the video: each scene visual and AI motion is synchronized to its dialogue segment.',
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
      'Each clip runs exactly as long as its scene audio segment from the master track.',
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
      'Clips and continuous narration are joined in order, with transitions.',
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
    <div className="wf-flow" role="img" aria-label="Video generation pipeline: plan (prompt, script), master audio and scene production, deliver (final mix, finished video)">
      <Phase num="1" title="Plan" sub="Turn your idea into scenes">
        <FlowNode stage={prompt} step={1} />
        <Link vertical />
        <FlowNode stage={script} step={2} />
      </Phase>

      <Link label="storyboard" />

      <Phase num="2" title="Audio-First Production" sub="Continuous voice track recorded first, scenes synced to audio" stacked>
        <FlowNode stage={voice} step={3} />
        <Link vertical label="master audio syncs scene length" />
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
    Icon: Mic,
    title: 'Master Audio-First Workflow',
    text: 'Rather than generating speech line-by-line per image, VidForge converts your entire story dialogue into a single continuous audio recording first. The video scenes and AI animations are then synchronized precisely to this voiceover.',
  },
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

// Author profile, from https://rixetbd.com/profile
const AUTHOR = {
  name: 'MD Rabiul Islam',
  title: 'Principal Software Engineer · Tech Explorer',
  role: 'Software Engineer Grade I at 6amTech',
  bio: 'Laravel developer building scalable, high-performance web applications with Laravel, PHP, MySQL, REST APIs and Laravel package development, plus SPA architecture, media management, payment gateway integration and AI automation with the OpenAI API.',
  skills: ['Laravel', 'PHP', 'MySQL', 'RESTful APIs', 'JavaScript', 'React', 'Vue', 'Livewire', 'Tailwind', 'OpenAI', 'Stripe', 'Git', 'Linux'],
  experience: [
    { company: '6amTech', role: 'Software Engineer Grade I', period: 'Mar 2023 – Present' },
    { company: 'Dimaz', role: 'Web Developer', period: 'May 2022 – Feb 2023' },
  ],
  links: [
    { label: 'Website', href: 'https://rixetbd.com', Icon: Globe },
    { label: 'GitHub', href: 'https://github.com/devrabiul', Icon: null },
    { label: 'Contact', href: 'mailto:rixetbd@gmail.com', Icon: Mail },
  ],
};

// lucide has no brand icons; GitHub mark inline
const GithubMark = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.52-1.33-1.28-1.69-1.28-1.69-1.05-.71.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.84 1.19 3.1 0 4.42-2.69 5.39-5.26 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5Z" />
  </svg>
);

function AuthorSection() {
  return (
    <section className="glass-panel wf-author" aria-labelledby="wf-author-title">
      <img className="wf-author-photo" src={authorPhoto} alt={AUTHOR.name} width={155} height={180} />
      <div className="wf-author-body">
        <span className="wf-author-kicker"><UserRound size={13} /> Author</span>
        <h3 id="wf-author-title">{AUTHOR.name}</h3>
        <div className="wf-author-title">{AUTHOR.title}</div>
        <div className="wf-author-role"><Briefcase size={13} /> {AUTHOR.role}</div>
        <div className="wf-author-links">
          {AUTHOR.links.map(({ label, href, Icon }) => (
            <a
              key={label}
              href={href}
              {...(href.startsWith('mailto:') ? { title: href.slice(7) } : { target: '_blank', rel: 'noopener noreferrer' })}
              className="wf-author-link"
            >
              {Icon ? <Icon size={14} /> : <GithubMark />} {label}
            </a>
          ))}
        </div>
        <p>{AUTHOR.bio}</p>
        <div className="wf-author-skills">
          {AUTHOR.skills.map(s => <span key={s}>{s}</span>)}
        </div>
        <div className="wf-author-foot">
          <ul className="wf-author-exp">
            {AUTHOR.experience.map(e => (
              <li key={e.company}><strong>{e.company}</strong> · {e.role} <span>{e.period}</span></li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

// What the studio does; engines match backend/ai_engine.py and backend/tts_engine.py
const ABOUT_FEATURES: { Icon: LucideIcon; title: string; text: string }[] = [
  { Icon: Wand2, title: 'Prompt to finished video', text: 'Write a topic or story; VidForge plans the scenes, writes the narration, voices it, illustrates every scene and edits the final MP4 on its own.' },
  { Icon: Film, title: '13 production types', text: 'Stories, news bulletins, documentaries, explainers, promos, reels, kids tales and more, each with its own writing style, pacing and music.' },
  { Icon: Languages, title: 'Bangla, Hindi & English', text: 'Narration in three languages with expressive cloud voices (Gemini, ElevenLabs) or your own cloned voice running locally.' },
  { Icon: Sparkles, title: 'Cinematic motion', text: 'Ultra HD Ken Burns camera moves on any machine, or real AI motion with Wan 2.1 on an NVIDIA GPU.' },
  { Icon: FolderOpen, title: 'Projects you can refine', text: 'Every video is kept as a project: design its thumbnail, revise scenes and re-render only what changed.' },
  { Icon: ShieldCheck, title: 'Runs on your computer', text: 'Script writing, images, motion and the final edit run locally. Your recordings and projects never leave this machine.' },
];

const ABOUT_STACK = ['Ollama LLM', 'ComfyUI', 'Z-Image Turbo', 'Wan 2.1 I2V', 'Gemini TTS', 'ElevenLabs', 'F5-TTS', 'FFmpeg', 'FastAPI', 'React + Vite'];

function AboutSection() {
  return (
    <section className="glass-panel wf-about" aria-labelledby="wf-about-title">
      <span className="wf-author-kicker"><Film size={13} /> About</span>
      <h3 id="wf-about-title">VidForge AI Studio <span className="brand-badge">PRO v1.0</span></h3>
      <p className="wf-about-lead">
        A local-first AI video production studio. It turns a single prompt into a narrated, illustrated and edited
        video, using open models on your own GPU instead of paid cloud render servers.
      </p>
      <div className="wf-about-grid">
        {ABOUT_FEATURES.map(({ Icon, title, text }) => (
          <div key={title} className="wf-about-item">
            <Icon size={16} color="var(--a-blue)" />
            <div>
              <strong>{title}</strong>
              <p>{text}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="wf-about-stack">
        <span>Built with</span>
        {ABOUT_STACK.map(t => <code key={t}>{t}</code>)}
      </div>
    </section>
  );
}

export default function WorkflowPage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <AuthorSection />
      <AboutSection />

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
