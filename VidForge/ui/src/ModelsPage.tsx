import { Fragment, useEffect, useState } from 'react';
import { toast } from './Toast';
import {
  Boxes, RefreshCw, Download, ExternalLink, Copy, Check, Cloud, Terminal,
  ShieldCheck, CircleDashed, CircleAlert, LoaderCircle, Cpu, MemoryStick, HardDrive, Monitor,
} from 'lucide-react';

type Basis = "vendor" | "calculated" | "estimate" | "app";

interface ModelFile {
  name: string;
  url: string;
  page: string;
  size: number;
  sha256: string | null;
  comfy_folder: string | null;
}

interface RequirementLine {
  label: string;
  value: string;
  basis: Basis;
  note?: string;
  source?: string;
}

interface Model {
  id: string;
  name: string;
  stage: string;
  role: string;
  runtime: "ollama" | "comfyui" | "f5";
  precision: string;
  page: string;
  ollama_tag?: string;
  download_cmd?: string;
  registry_size?: number;
  files: ModelFile[];
  requirements: { accel_gb: number; platform_block?: string | null; lines: RequirementLine[] };
}

interface LocalFile {
  name: string;
  expected_bytes: number;
  status: "match" | "mismatch" | "missing" | "incomplete" | "unreadable";
  bytes?: number;
  path?: string;
  searched: string[];
}

interface Device {
  os: string;
  arch: string;
  cpu: string;
  ram_bytes: number;
  gpus: { name: string; vram_bytes: number; kind: string }[];
  unified_memory: boolean;
  accel_bytes: number;
  disk_free_bytes: number;
}

interface Catalog {
  checked_on: string;
  models: Model[];
  cloud: { id: string; name: string; model: string; role: string; page: string; note: string }[];
  comfyui_dir: string;
  ollama_models_dir: string;
  hf_cache_dir: string;
  device: Device;
  local: { id: string; files: LocalFile[] }[];
}

interface HashResult { expected: string; actual: string; match: boolean; path: string }

const GB = 1e9;
const GIB = 1024 ** 3;
const fmtGB = (b: number) => (b >= 1e8 ? `${(b / GB).toFixed(2)} GB` : b >= 1e6 ? `${(b / 1e6).toFixed(1)} MB` : `${(b / 1e3).toFixed(1)} KB`);
const fmtBytes = (b: number) => b.toLocaleString('en-US');

const BASIS_LABEL: Record<Basis, string> = {
  vendor: "Vendor stated",
  calculated: "Calculated",
  estimate: "Estimate",
  app: "VidForge",
};

const STATUS_TEXT: Record<LocalFile["status"], string> = {
  match: "Verified — size matches",
  mismatch: "Size differs from official",
  missing: "Not downloaded — local size not verified",
  incomplete: "Partially downloaded — local size not verified",
  unreadable: "Found but unreadable — local size not verified",
};

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      className="btn btn-icon btn-ghost models-copy"
      title="Copy"
      aria-label="Copy to clipboard"
      onClick={() => { navigator.clipboard?.writeText(text); setDone(true); setTimeout(() => setDone(false), 1400); }}
    >
      {done ? <Check size={12} /> : <Copy size={12} />}
    </button>
  );
}

function sizeCommands(os: string, path: string, isOllama: boolean, tag?: string): string[] {
  if (isOllama && tag) return [`ollama list`, `ollama show ${tag}`];
  if (os.startsWith("Windows")) return [`(Get-Item "${path}").Length`, `Get-FileHash "${path}" -Algorithm SHA256`];
  if (os.startsWith("Darwin")) return [`stat -f%z "${path}"`, `shasum -a 256 "${path}"`];
  return [`stat -c%s "${path}"`, `sha256sum "${path}"`];
}

export default function ModelsPage({ apiBase, active }: { apiBase: string; active: boolean }) {
  const [data, setData] = useState<Catalog | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hashes, setHashes] = useState<Record<string, HashResult | "running" | string>>({});

  // `announce` is true for a manual re-scan; the automatic first scan stays silent
  const load = async (announce = false) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${apiBase}/api/models`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const next: Catalog = await res.json();
      setData(next);
      if (announce) {
        const files = next.local.flatMap(l => l.files);
        const verified = files.filter(f => f.status === "match").length;
        const problems = files.filter(f => f.status === "mismatch" || f.status === "incomplete" || f.status === "unreadable").length;
        if (problems > 0) {
          toast.error("Scan complete", `${problems} file${problems > 1 ? 's' : ''} need attention · ${verified}/${files.length} verified`);
        } else {
          toast.success("Scan complete", `${verified}/${files.length} files verified on this device`);
        }
      }
    } catch (e) {
      const msg = `Could not load the model list from the backend (${(e as Error).message}). Restart the backend if it was started before this page was added.`;
      setError(msg);
      if (announce) toast.error("Re-scan failed", "The backend did not respond.");
    } finally {
      setLoading(false);
    }
  };

  // Scan when the page is first opened
  useEffect(() => { if (active && !data && !loading) load(); }, [active]);

  const verify = async (modelId: string, fileName: string) => {
    const key = `${modelId}/${fileName}`;
    setHashes(h => ({ ...h, [key]: "running" }));
    try {
      const res = await fetch(`${apiBase}/api/models/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: modelId, file_name: fileName }),
      });
      const body = await res.json();
      setHashes(h => ({ ...h, [key]: res.ok ? body : (body.detail || "Verification failed") }));
    } catch {
      setHashes(h => ({ ...h, [key]: "Verification failed" }));
    }
  };

  const localFor = (id: string) => data?.local.find(l => l.id === id)?.files || [];
  const allLocal = data?.local.flatMap(l => l.files) || [];
  const verifiedCount = allLocal.filter(f => f.status === "match").length;
  const totalDownload = data ? data.models.reduce((sum, m) => sum + (m.registry_size || m.files.reduce((s, f) => s + f.size, 0)), 0) : 0;
  const stages = data ? Array.from(new Set(data.models.map(m => m.stage))) : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div className="glass-panel page-head">
        <div>
          <h2 className="page-title"><Boxes size={18} color="var(--a-blue)" /> AI Models &amp; Hardware</h2>
          <p className="page-sub">
            Every model VidForge loads: where to download it, its exact size, and the hardware it needs.
            {data && <> Official sizes checked against Hugging Face and the Ollama registry on {data.checked_on}.</>}
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {data && (
            <div className="page-stats">
              <div><strong>{data.models.length}</strong><span>Local models</span></div>
              <div><strong>{(totalDownload / GB).toFixed(1)}</strong><span>GB to download</span></div>
              <div><strong>{verifiedCount}/{allLocal.length}</strong><span>Files verified</span></div>
            </div>
          )}
          <button type="button" className="btn btn-primary" onClick={() => load(true)} disabled={loading} aria-busy={loading} title={loading ? 'Scanning…' : 'Re-scan this device'}>
            <RefreshCw size={13} className={loading ? 'spin' : ''} /> Re-scan device
          </button>
        </div>
      </div>

      {error && <div className="glass-panel models-error"><CircleAlert size={16} /> {error}</div>}

      {data && (
        <>
          {/* This device */}
          <div className="glass-panel models-device">
            <div className="models-device-title">This device</div>
            <div className="models-device-grid">
              <div><Monitor size={14} /><span>System</span><strong>{data.device.os} · {data.device.arch}</strong></div>
              <div><Cpu size={14} /><span>Processor</span><strong>{data.device.cpu || 'Unknown'}</strong></div>
              <div><MemoryStick size={14} /><span>RAM</span><strong>{data.device.ram_bytes ? `${(data.device.ram_bytes / GIB).toFixed(0)} GB` : 'Unknown'}</strong></div>
              <div>
                <Cpu size={14} /><span>GPU</span>
                <strong>
                  {data.device.gpus.length === 0
                    ? 'No supported GPU detected'
                    : data.device.gpus.map(g => `${g.name} · ${(g.vram_bytes / GIB).toFixed(0)} GB${g.kind === 'apple' ? ' unified (shared with CPU)' : ' VRAM'}`).join(', ')}
                </strong>
              </div>
              <div><HardDrive size={14} /><span>Free disk</span><strong>{(data.device.disk_free_bytes / GB).toFixed(0)} GB</strong></div>
            </div>
            <div className="models-legend">
              <span>Hardware figures are tagged:</span>
              {(Object.keys(BASIS_LABEL) as Basis[]).map(b => <span key={b} className={`basis basis-${b}`}>{BASIS_LABEL[b]}</span>)}
              <span>Vendor figures link to their source; calculated ones are derived from the exact file sizes.</span>
            </div>
          </div>

          {stages.map(stage => (
            <section key={stage} className="voice-group">
              <div className="voice-group-head"><h3>{stage}</h3></div>
              {data.models.filter(m => m.stage === stage).map(model => {
                const local = localFor(model.id);
                const allMatch = local.length > 0 && local.every(f => f.status === "match");
                const anyFound = local.some(f => f.status !== "missing");
                const overall = allMatch ? "match" : !anyFound ? "missing" : local.some(f => f.status === "mismatch") ? "mismatch" : "incomplete";
                const need = model.requirements.accel_gb;
                const have = data.device.accel_bytes / GIB;
                const fit = model.requirements.platform_block
                  ? { cls: 'bad', text: model.requirements.platform_block }
                  : need === 0 ? null
                  // Unified memory is shared with the OS and other apps, so a small margin is not really enough
                  : data.device.unified_memory && have >= need && have - need < 4
                    ? { cls: 'bad', text: `Borderline: ${have.toFixed(0)} GB unified memory is shared with the system (${need} GB needed)` }
                  : have >= need ? { cls: 'ok', text: `Your device meets the ${need} GB minimum` }
                  : { cls: 'bad', text: `Below the ${need} GB minimum (${have.toFixed(0)} GB available)` };

                return (
                  <article key={model.id} className="glass-panel model-card">
                    <header className="model-card-head">
                      <div style={{ minWidth: 0 }}>
                        <h4>{model.name}</h4>
                        <p>{model.role}</p>
                        <div className="gallery-meta" style={{ marginTop: 6 }}>
                          <span className="chip chip-primary">{model.precision}</span>
                          <span className="chip">{model.runtime === 'ollama' ? 'Ollama' : model.runtime === 'comfyui' ? 'ComfyUI' : 'Local voice (Python)'}</span>
                          <a className="chip" href={model.page} target="_blank" rel="noreferrer"><ExternalLink size={11} /> Model page</a>
                        </div>
                      </div>
                      <div className="model-badges">
                        <span className={`model-status ${overall}`}>
                          {overall === 'match' ? <ShieldCheck size={13} /> : overall === 'missing' ? <CircleDashed size={13} /> : <CircleAlert size={13} />}
                          {overall === 'match' ? 'Verified on this device' : overall === 'missing' ? 'Not downloaded — local size not verified' : overall === 'mismatch' ? 'Size mismatch on this device' : 'Partially downloaded'}
                        </span>
                        {fit && <span className={`model-fit ${fit.cls}`}>{fit.text}</span>}
                      </div>
                    </header>

                    {/* Files */}
                    <div className="model-files">
                      <div className="model-files-head">
                        <span>File</span><span>Official size</span><span>On this device</span><span />
                      </div>
                      {(model.runtime === 'ollama'
                        ? [{ name: model.ollama_tag!, url: model.page, page: model.page, size: model.registry_size!, sha256: 'ollama', comfy_folder: null }]
                        : model.files
                      ).map(file => {
                        const lf = local.find(l => l.name === file.name);
                        const key = `${model.id}/${file.name}`;
                        const hash = hashes[key];
                        const path = lf?.path || lf?.searched[0] || '';
                        return (
                          <Fragment key={file.name}>
                            <div className="model-file-row">
                              <div className="model-file-name">
                                <code>{file.name}</code>
                                {model.runtime === 'ollama' ? (
                                  <span className="model-cmd"><Terminal size={11} /> <code>{model.download_cmd}</code> <CopyButton text={model.download_cmd!} /></span>
                                ) : (
                                  <a href={file.page} target="_blank" rel="noreferrer" className="model-link">{file.url.replace('https://', '')}</a>
                                )}
                              </div>
                              <div className="model-size">
                                <strong>{fmtGB(file.size)}</strong>
                                <span>{fmtBytes(file.size)} bytes</span>
                              </div>
                              <div className={`model-local ${lf?.status || 'missing'}`}>
                                <strong>{STATUS_TEXT[lf?.status || 'missing']}</strong>
                                {lf?.bytes !== undefined && <span>{fmtBytes(lf.bytes)} bytes</span>}
                                {lf?.path
                                  ? <span className="model-path" title={lf.path}>{lf.path}</span>
                                  : <span className="model-path" title={lf?.searched.join('\n')}>Looked in: {lf?.searched[0]}</span>}
                              </div>
                              <div className="model-actions">
                                {model.runtime !== 'ollama' && (
                                  <a className="btn btn-ghost" href={file.url} target="_blank" rel="noreferrer" title="Direct download">
                                    <Download size={13} /> Download
                                  </a>
                                )}
                                {lf?.status === 'match' && file.sha256 && (
                                  <button type="button" className="btn btn-ghost" onClick={() => verify(model.id, file.name)} disabled={hash === 'running'}>
                                    {hash === 'running' ? <><LoaderCircle size={13} className="spin" /> Hashing…</> : <><ShieldCheck size={13} /> Verify SHA-256</>}
                                  </button>
                                )}
                              </div>
                            </div>
                            {hash && hash !== 'running' && (
                              <div className={`model-hash ${typeof hash === 'string' ? 'bad' : hash.match ? 'ok' : 'bad'}`}>
                                {typeof hash === 'string' ? hash : (
                                  <>
                                    <strong>{hash.match ? 'SHA-256 matches the official file' : 'SHA-256 does NOT match — re-download this file'}</strong>
                                    <span>Official: <code>{hash.expected}</code></span>
                                    <span>Yours: <code>{hash.actual}</code></span>
                                  </>
                                )}
                              </div>
                            )}
                            {file.sha256 && file.sha256 !== 'ollama' && (
                              <div className="model-sha">Official SHA-256: <code>{file.sha256}</code></div>
                            )}
                            <details className="model-howto">
                              <summary><Terminal size={12} /> Check the size yourself</summary>
                              {sizeCommands(data.device.os, path, model.runtime === 'ollama', model.ollama_tag).map(cmd => (
                                <div key={cmd} className="model-cmd-row"><code>{cmd}</code><CopyButton text={cmd} /></div>
                              ))}
                              <p>
                                {model.runtime === 'ollama'
                                  ? `ollama list shows a rounded size; the exact total of the downloaded layers should be ${fmtBytes(file.size)} bytes.`
                                  : `The first command prints the size in bytes — it should be exactly ${fmtBytes(file.size)}. The second prints the SHA-256${file.sha256 ? ', which should match the official value above' : ''}.`}
                              </p>
                            </details>
                          </Fragment>
                        );
                      })}
                    </div>

                    {/* Hardware */}
                    <div className="model-req">
                      <div className="model-req-title">Minimum hardware</div>
                      {model.requirements.lines.map(line => (
                        <div key={line.label} className="model-req-row">
                          <span className="model-req-label">{line.label}</span>
                          <div className="model-req-value">
                            <strong>{line.value}</strong>
                            <span className={`basis basis-${line.basis}`}>{BASIS_LABEL[line.basis]}</span>
                            {line.source && <a href={line.source} target="_blank" rel="noreferrer" className="model-link"><ExternalLink size={11} /> Source</a>}
                            {line.note && <p>{line.note}</p>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </article>
                );
              })}
            </section>
          ))}

          {/* Cloud */}
          <section className="voice-group">
            <div className="voice-group-head"><h3>Cloud voices</h3><span className="voice-group-sub">Nothing to download — no local hardware needed</span></div>
            <div className="voice-grid">
              {data.cloud.map(c => (
                <div key={c.id} className="voice-card">
                  <div className="voice-card-top">
                    <span className="voice-avatar"><Cloud size={16} /></span>
                    <div className="voice-card-id"><h4>{c.name}</h4><span><code>{c.model}</code></span></div>
                  </div>
                  <p className="voice-desc" style={{ WebkitLineClamp: 4 }}>{c.role}. {c.note}</p>
                  <a className="btn btn-ghost" href={c.page} target="_blank" rel="noreferrer"><ExternalLink size={13} /> Get API key</a>
                </div>
              ))}
            </div>
          </section>

          <p className="models-foot">
            Searched locations — ComfyUI models: <code>{data.comfyui_dir}/models</code> · Ollama: <code>{data.ollama_models_dir}</code> · Hugging Face cache: <code>{data.hf_cache_dir}</code>.
            Change them with <code>comfyui_dir</code>, <code>ollama_models_dir</code> (or <code>OLLAMA_MODELS</code>) and <code>HF_HOME</code>.
          </p>
        </>
      )}

    </div>
  );
}
