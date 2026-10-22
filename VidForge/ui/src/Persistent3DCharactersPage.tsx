import React, { useState, useEffect } from 'react';
import { 
  Box, Sparkles, RefreshCw, Upload, Film, 
  CheckCircle2, Layers, User, Plus, Trash2, RotateCcw,
  UserPlus, X, Image as ImageIcon
} from 'lucide-react';
import { toast } from './Toast';

interface Character3DProfile {
  character_id: string;
  name: string;
  look?: string;
  avatar_url?: string;
  version: number;
  status: 'UNINITIALIZED' | 'MESH_READY' | 'RIGGED' | 'BLENDER_PROJECT_READY' | 'ERROR';
  mesh_file?: string;
  rigged_file?: string;
  blend_file?: string;
  has_rig: boolean;
  bones_count: number;
  bones: string[];
  has_facial_rig: boolean;
  blendshapes: string[];
  supported_animations: string[];
  last_error?: string;
  updated_at?: string;
}

interface System3DStatus {
  blender_installed: boolean;
  blender_path: string | null;
  tripo3d_configured: boolean;
  animation_presets: Record<string, { name: string; description: string; loop: boolean; default_speed: number; category: string }>;
  blendshape_targets: string[];
  gpu: string;
}

interface SceneDirectorConfig {
  id: number;
  animation: string;
  camera_mode: string;
  lighting_preset: string;
  dialogue: string;
  voice: string;
  tts_engine: string;
  language: string;
  duration: number;
  rendered_video_url?: string;
  is_rendering?: boolean;
}

export default function Persistent3DCharactersPage({ apiBase, active }: { apiBase: string; active: boolean }) {
  const [systemStatus, setSystemStatus] = useState<System3DStatus | null>(null);
  const [characters, setCharacters] = useState<Character3DProfile[]>([]);
  const [selectedCharId, setSelectedCharId] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isGeneratingLocal, setIsGeneratingLocal] = useState<boolean>(false);
  const [isImporting, setIsImporting] = useState<boolean>(false);

  // Multi-Scene Director state
  const [scenes, setScenes] = useState<SceneDirectorConfig[]>([
    {
      id: 1,
      animation: 'walk',
      camera_mode: 'medium',
      lighting_preset: 'studio',
      dialogue: 'হ্যালো! আমি রবিউল, VidForge-এর একটি স্থায়ী ৩ডি চরিত্র।',
      voice: 'Charon',
      tts_engine: 'gemini',
      language: 'bn',
      duration: 3.5
    },
    {
      id: 2,
      animation: 'talk_gestures',
      camera_mode: 'close_up',
      lighting_preset: 'sunset',
      dialogue: 'আমি একাধিক দৃশ্যে হুবহু একই রূপ এবং পোশাক নিয়ে হাজির হতে পারি।',
      voice: 'Charon',
      tts_engine: 'gemini',
      language: 'bn',
      duration: 3.8
    }
  ]);
  const [activeSceneTab, setActiveSceneTab] = useState<number>(1);

  // Add Character Modal state
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [newCharName, setNewCharName] = useState<string>('');
  const [newCharLook, setNewCharLook] = useState<string>('');
  const [newCharVoice, setNewCharVoice] = useState<string>('Charon');
  const [newCharFile, setNewCharFile] = useState<File | null>(null);
  const [newCharPreview, setNewCharPreview] = useState<string>('');
  const [isSavingNewChar, setIsSavingNewChar] = useState<boolean>(false);
  const [autoGen3D, setAutoGen3D] = useState<boolean>(true);

  const fetchStatusAndCharacters = async () => {
    try {
      const [statusRes, charsRes] = await Promise.all([
        fetch(`${apiBase}/api/3d/status`),
        fetch(`${apiBase}/api/3d/characters`)
      ]);
      if (statusRes.ok) {
        const sData = await statusRes.json();
        setSystemStatus(sData);
      }
      if (charsRes.ok) {
        const cData = await charsRes.json();
        setCharacters(cData);
        if (cData.length > 0 && !selectedCharId) {
          setSelectedCharId(cData[0].character_id);
        }
      }
    } catch (err) {
      console.error('Failed to load 3D studio data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (active) {
      fetchStatusAndCharacters();
    }
  }, [active]);

  const selectedChar = characters.find(c => c.character_id === selectedCharId) || characters[0];

  const handleGenerateLocalModel = async () => {
    if (!selectedChar) return;
    setIsGeneratingLocal(true);
    try {
      const res = await fetch(`${apiBase}/api/3d/characters/${selectedChar.character_id}/generate-local`, {
        method: 'POST'
      });
      if (res.ok) {
        toast.success(`'${selectedChar.name}' ৩ডি মডেল ও ব্লেন্ডার রিগ সফলভাবে তৈরি হয়েছে!`);
        await fetchStatusAndCharacters();
      } else {
        const err = await res.json();
        toast.error(`ব্লেন্ডার জেনারেশন ব্যর্থ: ${err.detail || 'ত্রুটি'}`);
      }
    } catch (err: any) {
      toast.error(`জেনারেশন ব্যর্থ: ${err.message}`);
    } finally {
      setIsGeneratingLocal(false);
    }
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedChar) return;

    setIsImporting(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('is_rigged', 'true');

      const res = await fetch(`${apiBase}/api/3d/characters/${selectedChar.character_id}/import-model`, {
        method: 'POST',
        body: fd
      });
      if (res.ok) {
        toast.success(`3D ফাইল '${file.name}' সফলভাবে ইম্পোর্ট করা হয়েছে!`);
        await fetchStatusAndCharacters();
      } else {
        toast.error('ফাইল ইম্পোর্ট ব্যর্থ হয়েছে');
      }
    } catch (err: any) {
      toast.error(`ইম্পোর্ট ত্রুটি: ${err.message}`);
    } finally {
      setIsImporting(false);
    }
  };

  const handleDeleteCharacter = async () => {
    if (!selectedChar) return;
    if (!window.confirm(`আপনি কি সত্যিই '${selectedChar.name}' ৩ডি চরিত্রটি সম্পূর্ণরূপে মুছে ফেলতে চান? এটি ক্যারেক্টার ভল্ট এবং ৩ডি ফাইল উভয়ই মুছে ফেলবে।`)) return;

    try {
      const res = await fetch(`${apiBase}/api/3d/characters/${selectedChar.character_id}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        toast.success(`'${selectedChar.name}' চরিত্র এবং ৩ডি ফাইল মুছে ফেলা হয়েছে`);
        setSelectedCharId('');
        await fetchStatusAndCharacters();
      } else {
        toast.error('মুছে ফেলতে সমস্যা হয়েছে');
      }
    } catch (err: any) {
      toast.error(`মুছে ফেলা ব্যর্থ: ${err.message}`);
    }
  };

  const handleResetAssets = async () => {
    if (!selectedChar) return;
    if (!window.confirm(`'${selectedChar.name}'-এর জেনারেট করা ৩ডি মেমোরি (.blend, .glb) রিসেট করতে চান? মূল ছবি অক্ষত থাকবে।`)) return;

    try {
      const res = await fetch(`${apiBase}/api/3d/characters/${selectedChar.character_id}/assets`, {
        method: 'DELETE'
      });
      if (res.ok) {
        toast.success(`'${selectedChar.name}'-এর ৩ডি ফাইল রিসেট করা হয়েছে`);
        await fetchStatusAndCharacters();
      } else {
        toast.error('৩ডি রিসেট ব্যর্থ হয়েছে');
      }
    } catch (err: any) {
      toast.error(`ত্রুটি: ${err.message}`);
    }
  };

  const handleDeleteRenderedVideo = async (sceneId: number) => {
    const sc = scenes.find(s => s.id === sceneId);
    if (!sc || !sc.rendered_video_url || !selectedChar) return;
    if (!window.confirm(`দৃশ্য ${sceneId}-এর রেন্ডার করা ভিডিও মুছে ফেলতে চান?`)) return;

    try {
      const filename = sc.rendered_video_url.split('/').pop()?.split('?')[0] || '';
      if (filename) {
        await fetch(`${apiBase}/api/3d/characters/${selectedChar.character_id}/renders/${filename}`, {
          method: 'DELETE'
        });
      }
      setScenes(prev => prev.map(s => s.id === sceneId ? { ...s, rendered_video_url: undefined } : s));
      toast.success(`দৃশ্য ${sceneId}-এর রেন্ডার ভিডিও মুছে ফেলা হয়েছে`);
    } catch (err: any) {
      toast.error(`ভিডিও মোছা ব্যর্থ: ${err.message}`);
    }
  };

  const handleDeleteScene = (sceneId: number) => {
    if (scenes.length <= 1) {
      toast.info('কমপক্ষে একটি দৃশ্য থাকা আবশ্যক');
      return;
    }
    const remaining = scenes.filter(s => s.id !== sceneId);
    setScenes(remaining);
    if (activeSceneTab === sceneId) {
      setActiveSceneTab(remaining[0].id);
    }
    toast.success(`দৃশ্য ${sceneId} টাইমলাইন থেকে সরানো হয়েছে`);
  };

  const handleAddNewCharacter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCharName.trim()) {
      toast.error('চরিত্রের নাম আবশ্যক');
      return;
    }
    if (!newCharFile) {
      toast.error('রেফারেন্স ছবি আপলোড করুন');
      return;
    }

    setIsSavingNewChar(true);
    try {
      const fd = new FormData();
      fd.append('name', newCharName.trim());
      fd.append('look', newCharLook.trim());
      fd.append('voice_preset', newCharVoice);
      fd.append('video_type', 'animation');
      fd.append('file', newCharFile);

      const res = await fetch(`${apiBase}/api/characters`, {
        method: 'POST',
        body: fd
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'চরিত্র সংরক্ষণ ব্যর্থ হয়েছে');
      }

      const savedChar = await res.json();
      const newCharId = savedChar.id;

      toast.success(`'${newCharName}' চরিত্র সফলভাবে তৈরি হয়েছে!`);

      // If autoGen3D is true, automatically trigger local Blender humanoid model & rig generation
      if (autoGen3D && newCharId) {
        toast.info(`'${newCharName}'-এর ৩ডি মডেল ও ব্লেন্ডার রিগ প্রস্তুত করা হচ্ছে...`);
        try {
          await fetch(`${apiBase}/api/3d/characters/${newCharId}/generate-local`, {
            method: 'POST'
          });
          toast.success(`'${newCharName}' ৩ডি রিগ তৈরি সম্পন্ন!`);
        } catch (genErr) {
          console.warn('Auto 3D generation error:', genErr);
        }
      }

      // Reset form & close modal
      setNewCharName('');
      setNewCharLook('');
      setNewCharFile(null);
      setNewCharPreview('');
      setShowAddModal(false);

      // Refresh list and select new character
      await fetchStatusAndCharacters();
      setSelectedCharId(newCharId);
    } catch (err: any) {
      toast.error(`ত্রুটি: ${err.message}`);
    } finally {
      setIsSavingNewChar(false);
    }
  };

  const handleRenderScene = async (sceneId: number) => {
    if (!selectedChar) return;
    const sc = scenes.find(s => s.id === sceneId);
    if (!sc) return;

    setScenes(prev => prev.map(s => s.id === sceneId ? { ...s, is_rendering: true } : s));

    try {
      const res = await fetch(`${apiBase}/api/3d/render-scene`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          character_id: selectedChar.character_id,
          scene_id: sceneId,
          animation: sc.animation,
          camera_mode: sc.camera_mode,
          lighting_preset: sc.lighting_preset,
          duration: sc.duration,
          dialogue: sc.dialogue,
          voice: sc.voice,
          tts_engine: sc.tts_engine,
          language: sc.language,
          aspect_ratio: '9:16'
        })
      });

      if (res.ok) {
        const data = await res.json();
        const fullUrl = `${apiBase}${data.video_url}`;
        setScenes(prev => prev.map(s => s.id === sceneId ? { ...s, rendered_video_url: fullUrl, is_rendering: false } : s));
        toast.success(`দৃশ্য ${sceneId} সফলভাবে রেন্ডার হয়েছে!`);
      } else {
        const err = await res.json();
        toast.error(`রেন্ডার ব্যর্থ: ${err.detail || 'ত্রুটি'}`);
        setScenes(prev => prev.map(s => s.id === sceneId ? { ...s, is_rendering: false } : s));
      }
    } catch (err: any) {
      toast.error(`রেন্ডার ত্রুটি: ${err.message}`);
      setScenes(prev => prev.map(s => s.id === sceneId ? { ...s, is_rendering: false } : s));
    }
  };

  const currentScene = scenes.find(s => s.id === activeSceneTab) || scenes[0];

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: '24px 20px 80px' }}>
      
      {/* Header Banner */}
      <div style={{ 
        background: 'linear-gradient(135deg, rgb(168 85 247 / 0.12) 0%, rgb(59 130 246 / 0.08) 100%)', 
        border: '1px solid rgb(168 85 247 / 0.3)', 
        borderRadius: 16, 
        padding: '20px 24px', 
        marginBottom: 24,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 16
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ width: 46, height: 46, borderRadius: 12, background: 'rgb(168 85 247 / 0.25)', color: 'var(--a-purple)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Box size={24} />
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: 'var(--t-strong)' }}>
              Persistent 3D Character Studio
            </h2>
            <div style={{ fontSize: 12, color: 'var(--t-muted)', marginTop: 4 }}>
              রেফারেন্স ফটো থেকে ৩ডি ক্যারেক্টার তৈরি, ওয়াকিং, স্পিকিং লিপ-সিঙ্ক এবং একাধিক দৃশ্যে হুবহু ধারাবাহিকতা
            </div>
          </div>
        </div>

        {/* Engine Status Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'var(--surface)', border: '1px solid var(--line)', padding: '6px 12px', borderRadius: 8, fontSize: 11.5 }}>
            <CheckCircle2 size={13} color="var(--a-green-bright)" />
            <span><strong>Blender:</strong> {systemStatus?.blender_installed ? 'Blender 5.2 LTS (Ready)' : 'Detecting...'}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'var(--surface)', border: '1px solid var(--line)', padding: '6px 12px', borderRadius: 8, fontSize: 11.5 }}>
            <Sparkles size={13} color="var(--a-purple)" />
            <span><strong>GPU:</strong> {systemStatus?.gpu || 'NVIDIA NVENC'}</span>
          </div>
        </div>
      </div>

      {/* Character Vault Bar */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 12, padding: '12px 16px', marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10, flexWrap: 'wrap', gap: 8 }}>
          <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--t-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            চরিত্র নির্বাচন করুন (Character Vault):
          </div>
          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            className="btn btn-primary btn-sm"
            style={{ fontSize: 11.5, padding: '5px 12px', display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <UserPlus size={13} />
            নতুন চরিত্র যোগ করুন (Add Character)
          </button>
        </div>
        <div style={{ display: 'flex', gap: 10, overflowX: 'auto', paddingBottom: 4, alignItems: 'center' }}>
          {isLoading && (
            <div style={{ fontSize: 12, color: 'var(--t-muted)', padding: '8px 4px', display: 'flex', alignItems: 'center', gap: 6 }}>
              <RefreshCw size={14} className="animate-spin" />
              <span>চরিত্রসমূহ লোড হচ্ছে...</span>
            </div>
          )}
          {characters.map(c => {
            const isSelected = c.character_id === selectedCharId;
            return (
              <button
                key={c.character_id}
                type="button"
                onClick={() => setSelectedCharId(c.character_id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '8px 14px',
                  borderRadius: 10,
                  background: isSelected ? 'rgb(168 85 247 / 0.18)' : 'var(--surface-hover)',
                  border: isSelected ? '1px solid var(--a-purple)' : '1px solid var(--line)',
                  color: isSelected ? 'var(--a-purple)' : 'var(--t-body)',
                  cursor: 'pointer',
                  fontWeight: isSelected ? 700 : 500,
                  fontSize: 13,
                  transition: 'all 0.15s ease',
                  flexShrink: 0
                }}
              >
                <div style={{ width: 30, height: 30, borderRadius: '50%', overflow: 'hidden', background: 'var(--well)', flexShrink: 0 }}>
                  {c.avatar_url ? (
                    <img src={`${apiBase}${c.avatar_url}`} alt={c.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  ) : (
                    <User size={16} style={{ margin: 7 }} />
                  )}
                </div>
                <span>{c.name || 'Untitled Character'}</span>
                {c.status === 'BLENDER_PROJECT_READY' && (
                  <span style={{ fontSize: 9.5, background: 'rgb(34 197 94 / 0.2)', color: 'var(--a-green-bright)', padding: '2px 5px', borderRadius: 4, fontWeight: 700 }}>
                    3D READY
                  </span>
                )}
              </button>
            );
          })}
          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 14px',
              borderRadius: 10,
              background: 'transparent',
              border: '1px dashed var(--line)',
              color: 'var(--t-muted)',
              cursor: 'pointer',
              fontSize: 12,
              whiteSpace: 'nowrap',
              transition: 'all 0.15s ease',
              flexShrink: 0
            }}
          >
            <Plus size={15} />
            <span>নতুন চরিত্র যোগ</span>
          </button>
        </div>
      </div>

      {/* Main Studio Grid: Left Asset Inspector, Right Multi-Scene Director */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 380px) 1fr', gap: 24, alignItems: 'start' }}>
        
        {/* LEFT COLUMN: Character 3D Asset Profile */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 14, padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <div style={{ width: 64, height: 64, borderRadius: 12, overflow: 'hidden', border: '1px solid var(--line)', flexShrink: 0 }}>
              {selectedChar?.avatar_url ? (
                <img src={`${apiBase}${selectedChar.avatar_url}`} alt={selectedChar.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              ) : (
                <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <User size={24} color="var(--t-muted)" />
                </div>
              )}
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: 17, fontWeight: 800, color: 'var(--t-strong)' }}>
                {selectedChar?.name || 'No character selected'}
              </h3>
              <div style={{ fontSize: 11, color: 'var(--t-muted)', marginTop: 3 }}>
                ID: {selectedChar?.character_id}
              </div>
              <div style={{ marginTop: 6 }}>
                <span style={{ 
                  fontSize: 10, 
                  fontWeight: 700, 
                  padding: '2px 7px', 
                  borderRadius: 4,
                  background: selectedChar?.status === 'BLENDER_PROJECT_READY' ? 'rgb(34 197 94 / 0.2)' : 'rgb(234 179 8 / 0.2)',
                  color: selectedChar?.status === 'BLENDER_PROJECT_READY' ? 'var(--a-green-bright)' : 'var(--a-amber)'
                }}>
                  {selectedChar?.status || 'UNINITIALIZED'}
                </span>
              </div>
            </div>
          </div>

          {/* Model & Skeleton Specs */}
          <div style={{ background: 'var(--surface-hover)', borderRadius: 10, padding: 14, marginBottom: 16 }}>
            <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--t-strong)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Layers size={13} color="var(--a-purple)" /> ৩ডি রিগ ও স্কেলেটন স্পেসিফিকেশন:
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11.5 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--t-muted)' }}>Humanoid Rig:</span>
                <span style={{ fontWeight: 600, color: selectedChar?.has_rig ? 'var(--a-green-bright)' : 'var(--t-body)' }}>
                  {selectedChar?.has_rig ? `✓ সক্রিয় (${selectedChar.bones_count} Bones)` : 'Not Rigged'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--t-muted)' }}>Facial Blendshapes:</span>
                <span style={{ fontWeight: 600, color: selectedChar?.has_facial_rig ? 'var(--a-green-bright)' : 'var(--t-body)' }}>
                  {selectedChar?.has_facial_rig ? `✓ ${selectedChar.blendshapes.length} Visemes (Lip-Sync Ready)` : '0 detected'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--t-muted)' }}>Native Project:</span>
                <span style={{ fontWeight: 600, color: selectedChar?.blend_file ? 'var(--a-purple)' : 'var(--t-muted)' }}>
                  {selectedChar?.blend_file ? 'character.blend' : 'None'}
                </span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <button
              type="button"
              onClick={handleGenerateLocalModel}
              disabled={isGeneratingLocal}
              className="btn btn-primary"
              style={{ width: '100%', fontSize: 12, padding: '9px 12px', justifyContent: 'center' }}
            >
              {isGeneratingLocal ? (
                <><RefreshCw size={13} className="animate-spin" /> ব্লেন্ডারে ৩ডি রিগ তৈরি হচ্ছে...</>
              ) : (
                <><Sparkles size={13} /> ব্লেন্ডারে ৩ডি মডেল ও রিগ তৈরি করুন</>
              )}
            </button>

            <label className="btn btn-secondary" style={{ width: '100%', fontSize: 12, padding: '9px 12px', justifyContent: 'center', cursor: 'pointer', margin: 0 }}>
              <Upload size={13} /> কাস্টম ৩ডি ফাইল ইম্পোর্ট (.GLB / .BLEND)
              <input type="file" accept=".glb,.gltf,.fbx,.blend" style={{ display: 'none' }} onChange={handleImportFile} disabled={isImporting} />
            </label>

            {/* Delete & Reset Action Group */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 4 }}>
              <button
                type="button"
                onClick={handleResetAssets}
                disabled={!selectedChar || selectedChar.status === 'UNINITIALIZED'}
                className="btn btn-secondary btn-sm"
                style={{ fontSize: 11, padding: '7px 8px', justifyContent: 'center', display: 'flex', alignItems: 'center', gap: 5 }}
                title="শুধুমাত্র তৈরি হওয়া ৩ডি মেমোরি রিসেট করুন (মূল রেফারেন্স ছবি অক্ষত থাকবে)"
              >
                <RotateCcw size={12} /> ৩ডি রিসেট
              </button>
              <button
                type="button"
                onClick={handleDeleteCharacter}
                disabled={!selectedChar}
                className="btn btn-danger btn-sm"
                style={{ 
                  fontSize: 11, 
                  padding: '7px 8px', 
                  justifyContent: 'center', 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 5,
                  background: 'rgb(239 68 68 / 0.15)',
                  borderColor: 'rgb(239 68 68 / 0.4)',
                  color: 'rgb(248 113 113)'
                }}
                title="চরিত্রটি এবং এর সমস্ত ৩ডি ফাইল সম্পূর্ণ মুছে ফেলুন"
              >
                <Trash2 size={12} /> চরিত্র মুছুন
              </button>
            </div>
          </div>

          <div style={{ fontSize: 10.5, color: 'var(--t-muted)', marginTop: 12, lineHeight: 1.4 }}>
            💡 <strong>স্থায়ী চরিত্র গ্যারান্টি:</strong> একবার এই ৩ডি প্রোফাইল তৈরি হলে ব্লেন্ডার সেই একই মেটারিয়াল ও টেক্সচার প্রতিটি সিনে হুবহু ব্যবহার করবে।
          </div>
        </div>

        {/* RIGHT COLUMN: Multi-Scene 3D Director & Lip-Sync */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 14, padding: 22 }}>
          
          {/* Scene Tabs */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18, borderBottom: '1px solid var(--line)', paddingBottom: 12 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              {scenes.map(sc => (
                <div
                  key={sc.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    borderRadius: 8,
                    background: activeSceneTab === sc.id ? 'rgb(168 85 247 / 0.2)' : 'var(--surface-hover)',
                    border: activeSceneTab === sc.id ? '1px solid var(--a-purple)' : '1px solid var(--line)',
                    padding: '2px 4px 2px 10px',
                    gap: 4
                  }}
                >
                  <button
                    type="button"
                    onClick={() => setActiveSceneTab(sc.id)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: activeSceneTab === sc.id ? 'var(--a-purple)' : 'var(--t-body)',
                      fontSize: 12.5,
                      fontWeight: activeSceneTab === sc.id ? 700 : 500,
                      cursor: 'pointer',
                      padding: '4px 2px'
                    }}
                  >
                    দৃশ্য {sc.id}
                  </button>
                  {scenes.length > 1 && (
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); handleDeleteScene(sc.id); }}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--t-muted)',
                        cursor: 'pointer',
                        padding: 3,
                        display: 'flex',
                        alignItems: 'center',
                        borderRadius: 4
                      }}
                      title={`দৃশ্য ${sc.id} টাইমলাইন থেকে সরান`}
                    >
                      <Trash2 size={12} />
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={() => {
                  const newId = scenes.length + 1;
                  setScenes([...scenes, {
                    id: newId,
                    animation: 'walk',
                    camera_mode: 'medium',
                    lighting_preset: 'studio',
                    dialogue: '',
                    voice: 'Charon',
                    tts_engine: 'gemini',
                    language: 'bn',
                    duration: 3.0
                  }]);
                  setActiveSceneTab(newId);
                }}
                style={{
                  padding: '6px 10px',
                  borderRadius: 8,
                  background: 'transparent',
                  border: '1px dashed var(--line)',
                  color: 'var(--t-muted)',
                  fontSize: 12,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4
                }}
              >
                <Plus size={12} /> দৃশ্য যোগ করুন
              </button>
            </div>

            {currentScene.rendered_video_url && (
              <span style={{ fontSize: 11, color: 'var(--a-green-bright)', display: 'flex', alignItems: 'center', gap: 4 }}>
                <CheckCircle2 size={13} /> রেন্ডার প্রস্তুত
              </span>
            )}
          </div>

          {/* Scene Director Configuration Form */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 16 }}>
            
            {/* Locomotion & Animation */}
            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--t-strong)', display: 'block', marginBottom: 5 }}>
                চরিত্রের অ্যানিমেশন (Animation / Movement):
              </label>
              <select
                value={currentScene.animation}
                onChange={e => setScenes(scenes.map(s => s.id === currentScene.id ? { ...s, animation: e.target.value } : s))}
                style={{ width: '100%', padding: '8px 10px', fontSize: 12 }}
              >
                <option value="walk">🚶‍♂️ Forward Walk (সোজা সামনে হাঁটা)</option>
                <option value="talk_gestures">🗣️ Conversational Gestures (কথা বলা ও অঙ্গভঙ্গি)</option>
                <option value="idle">🧘 Natural Idle (স্বাভাবিক দাঁড়িয়ে থাকা)</option>
                <option value="run">🏃 Athletic Run (সামনে দৌড়ানো)</option>
                <option value="greeting">👋 Friendly Wave & Smile (হাত নাড়া)</option>
              </select>
            </div>

            {/* Camera Framing */}
            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--t-strong)', display: 'block', marginBottom: 5 }}>
                ক্যামেরা অ্যাঙ্গেল ও ফ্রেম (Cinematic Camera):
              </label>
              <select
                value={currentScene.camera_mode}
                onChange={e => setScenes(scenes.map(s => s.id === currentScene.id ? { ...s, camera_mode: e.target.value } : s))}
                style={{ width: '100%', padding: '8px 10px', fontSize: 12 }}
              >
                <option value="medium">Medium Shot (কোমর থেকে মাথা পর্যন্ত)</option>
                <option value="close_up">Close-up Portrait (মুখের表情 ও লিপ-সিঙ্ক)</option>
                <option value="wide">Wide Tracking (পুরো চরিত্র ও হাঁটার পথ)</option>
                <option value="pan">Dynamic Camera Pan (ক্যামেরা মুভমেন্ট)</option>
              </select>
            </div>

            {/* Lighting Mood */}
            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--t-strong)', display: 'block', marginBottom: 5 }}>
                লাইটিং ও পরিবেশ (Lighting Preset):
              </label>
              <select
                value={currentScene.lighting_preset}
                onChange={e => setScenes(scenes.map(s => s.id === currentScene.id ? { ...s, lighting_preset: e.target.value } : s))}
                style={{ width: '100%', padding: '8px 10px', fontSize: 12 }}
              >
                <option value="studio">Studio Neutral (পরিষ্কার প্রফেশনাল লাইট)</option>
                <option value="sunset">Sunset Warm (গোধূলির নরম সোনালি আলো)</option>
                <option value="cyberpunk">Cyberpunk Neon (নীল ও গোলাপি নিয়ন)</option>
              </select>
            </div>

            {/* Duration */}
            <div>
              <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--t-strong)', display: 'block', marginBottom: 5 }}>
                দৃশ্যের সময়কাল (Duration): {currentScene.duration}s
              </label>
              <input
                type="range"
                min={1.0}
                max={15.0}
                step={0.5}
                value={currentScene.duration}
                onChange={e => setScenes(scenes.map(s => s.id === currentScene.id ? { ...s, duration: parseFloat(e.target.value) } : s))}
                style={{ width: '100%', marginTop: 8 }}
              />
            </div>
          </div>

          {/* Dialogue & Lip-Sync Box */}
          <div style={{ marginBottom: 18 }}>
            <label style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--t-strong)', display: 'block', marginBottom: 6 }}>
              চরিত্রের সংলাপ ও স্বয়ংক্রিয় লিপ-সিঙ্ক (Dialogue & Lip-Sync):
            </label>
            <textarea
              rows={3}
              placeholder="চরিত্রটি এই দৃশ্যে কী বলবে লিখুন (এআই স্বয়ংক্রিয়ভাবে অডিও বানিয়ে মুখের জ-বোন ও ঠোঁটের আকৃতি নাচাবে)..."
              value={currentScene.dialogue}
              onChange={e => setScenes(scenes.map(s => s.id === currentScene.id ? { ...s, dialogue: e.target.value } : s))}
              style={{ width: '100%', padding: '10px 12px', fontSize: 12.5, resize: 'vertical' }}
            />
          </div>

          {/* Render Scene Button */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
            <div style={{ fontSize: 11, color: 'var(--t-muted)' }}>
              ⚡ Blender H.264 NVENC হার্ডওয়্যার এনকোডার দ্বারা রেন্ডার হবে
            </div>
            <button
              type="button"
              onClick={() => handleRenderScene(currentScene.id)}
              disabled={currentScene.is_rendering}
              className="btn btn-primary"
              style={{ fontSize: 13, padding: '10px 20px' }}
            >
              {currentScene.is_rendering ? (
                <><RefreshCw size={14} className="animate-spin" /> দৃশ্য {currentScene.id} ব্লেন্ডারে রেন্ডার হচ্ছে...</>
              ) : (
                <><Film size={14} /> দৃশ্য {currentScene.id} রেন্ডার করুন (Render in Blender)</>
              )}
            </button>
          </div>

          {/* Video Preview Player */}
          {currentScene.rendered_video_url && (
            <div style={{ background: 'var(--well)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--t-strong)' }}>
                  দৃশ্য {currentScene.id} রেন্ডার প্রিভিউ:
                </span>
                <div style={{ display: 'flex', gap: 8 }}>
                  <a
                    href={currentScene.rendered_video_url}
                    download={`scene_${currentScene.id}.mp4`}
                    className="btn btn-secondary btn-sm"
                    style={{ fontSize: 11 }}
                  >
                    ভিডিও ডাউনলোড
                  </a>
                  <button
                    type="button"
                    onClick={() => handleDeleteRenderedVideo(currentScene.id)}
                    className="btn btn-danger btn-sm"
                    style={{ 
                      fontSize: 11, 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: 4,
                      background: 'rgb(239 68 68 / 0.15)',
                      borderColor: 'rgb(239 68 68 / 0.4)',
                      color: 'rgb(248 113 113)'
                    }}
                    title="রেন্ডার করা ভিডিও ফাইলটি মুছে ফেলুন"
                  >
                    <Trash2 size={12} />
                    রেন্ডার মুছুন
                  </button>
                </div>
              </div>
              <div style={{ borderRadius: 8, overflow: 'hidden', maxHeight: 420, background: '#000', display: 'flex', justifyContent: 'center' }}>
                <video
                  src={currentScene.rendered_video_url}
                  controls
                  autoPlay
                  loop
                  style={{ maxHeight: 420, width: 'auto', display: 'block' }}
                />
              </div>
            </div>
          )}

        </div>

      </div>

      {/* Create / Add Character Modal */}
      {showAddModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: 20
        }}>
          <div style={{
            background: 'var(--surface)',
            border: '1px solid var(--line)',
            borderRadius: 16,
            width: '100%',
            maxWidth: 540,
            overflow: 'hidden',
            boxShadow: '0 20px 40px rgba(0,0,0,0.4)'
          }}>
            {/* Modal Header */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '16px 20px',
              borderBottom: '1px solid var(--line)',
              background: 'linear-gradient(135deg, rgb(168 85 247 / 0.1) 0%, rgb(59 130 246 / 0.05) 100%)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 34, height: 34, borderRadius: 10, background: 'rgb(168 85 247 / 0.2)', color: 'var(--a-purple)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <UserPlus size={18} />
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: 'var(--t-strong)' }}>
                    নতুন ৩ডি চরিত্র যোগ করুন
                  </h3>
                  <div style={{ fontSize: 11, color: 'var(--t-muted)', marginTop: 2 }}>
                    রেফারেন্স ছবি ও নাম দিয়ে স্থায়ী ৩ডি ক্যারেক্টার তৈরি করুন
                  </div>
                </div>
              </div>
              <button
                type="button"
                onClick={() => { setShowAddModal(false); setNewCharFile(null); setNewCharPreview(''); }}
                style={{ background: 'transparent', border: 'none', color: 'var(--t-muted)', cursor: 'pointer', padding: 4 }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleAddNewCharacter} style={{ padding: 20 }}>
              {/* Character Name */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--t-strong)', display: 'block', marginBottom: 6 }}>
                  চরিত্রের নাম (Character Name) *
                </label>
                <input
                  type="text"
                  required
                  placeholder="যেমন: রোবট রনি, সায়রা, জন..."
                  value={newCharName}
                  onChange={e => setNewCharName(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', fontSize: 13 }}
                />
              </div>

              {/* Reference Portrait Image */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--t-strong)', display: 'block', marginBottom: 6 }}>
                  রেফারেন্স প্রতিকৃতি ছবি (Reference Portrait) *
                </label>
                <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
                  {newCharPreview ? (
                    <div style={{ width: 72, height: 72, borderRadius: 12, overflow: 'hidden', border: '1px solid var(--line)', flexShrink: 0 }}>
                      <img src={newCharPreview} alt="Preview" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    </div>
                  ) : (
                    <div style={{ width: 72, height: 72, borderRadius: 12, border: '1px dashed var(--line)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--t-muted)', flexShrink: 0 }}>
                      <ImageIcon size={22} />
                      <span style={{ fontSize: 9, marginTop: 4 }}>ছবি নেই</span>
                    </div>
                  )}
                  <label className="btn btn-secondary" style={{ fontSize: 12, padding: '9px 14px', cursor: 'pointer', margin: 0 }}>
                    <Upload size={14} /> ছবি ব্রাউজ করুন (.JPG, .PNG)
                    <input
                      type="file"
                      accept="image/*"
                      style={{ display: 'none' }}
                      onChange={e => {
                        const file = e.target.files?.[0];
                        if (file) {
                          setNewCharFile(file);
                          setNewCharPreview(URL.createObjectURL(file));
                        }
                      }}
                    />
                  </label>
                </div>
              </div>

              {/* Character Appearance Look Description */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--t-strong)', display: 'block', marginBottom: 6 }}>
                  চেহারা ও পোশাকের বিবরণ (Look Description - ঐচ্ছিক)
                </label>
                <textarea
                  rows={2}
                  placeholder="খালি রাখলে এআই স্বয়ংক্রিয়ভাবে আপলোড করা ছবি থেকে মুখ ও পোশাকের বর্ণনা বের করবে..."
                  value={newCharLook}
                  onChange={e => setNewCharLook(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', fontSize: 12, resize: 'vertical' }}
                />
              </div>

              {/* Voice Preset Dropdown */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--t-strong)', display: 'block', marginBottom: 6 }}>
                  কণ্ঠস্বর (Voice Preset)
                </label>
                <select
                  value={newCharVoice}
                  onChange={e => setNewCharVoice(e.target.value)}
                  style={{ width: '100%', padding: '9px 12px', fontSize: 12.5 }}
                >
                  <optgroup label="Gemini Studio Voices (বাংলা ও ইংরেজি উভয়তেই চমৎকার)">
                    <option value="Charon">Charon (গম্ভীর, পুরুষালী গভীর কণ্ঠ)</option>
                    <option value="Puck">Puck (প্রাণবন্ত, তারুণ্যদীপ্ত কণ্ঠ)</option>
                    <option value="Fenrir">Fenrir (দৃঢ় ও নাটকীয় কণ্ঠ)</option>
                    <option value="Aoede">Aoede (মিষ্টি, নারী কণ্ঠ)</option>
                    <option value="Kore">Kore (শান্ত ও স্পষ্ট নারী কণ্ঠ)</option>
                  </optgroup>
                  <optgroup label="ElevenLabs Voices">
                    <option value="Adam">Adam (Deep US Male)</option>
                    <option value="Rachel">Rachel (Calm US Female)</option>
                    <option value="George">George (Warm UK Male)</option>
                  </optgroup>
                </select>
              </div>

              {/* Auto Generate 3D Rig Checkbox */}
              <div style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', background: 'var(--well)', borderRadius: 8, border: '1px solid var(--line)' }}>
                <input
                  type="checkbox"
                  id="autoGen3dCheck"
                  checked={autoGen3D}
                  onChange={e => setAutoGen3D(e.target.checked)}
                  style={{ cursor: 'pointer' }}
                />
                <label htmlFor="autoGen3dCheck" style={{ fontSize: 11.5, color: 'var(--t-strong)', cursor: 'pointer', margin: 0 }}>
                  ⚡ সংরক্ষণের পর ব্লেন্ডারে স্বয়ংক্রিয় ৩ডি মডেল ও ৯-বোন রিগ তৈরি করুন
                </label>
              </div>

              {/* Submit / Cancel Buttons */}
              <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => { setShowAddModal(false); setNewCharFile(null); setNewCharPreview(''); }}
                  disabled={isSavingNewChar}
                  className="btn btn-secondary"
                  style={{ fontSize: 12.5, padding: '8px 16px' }}
                >
                  বাতিল
                </button>
                <button
                  type="submit"
                  disabled={isSavingNewChar}
                  className="btn btn-primary"
                  style={{ fontSize: 12.5, padding: '8px 20px', display: 'flex', alignItems: 'center', gap: 6 }}
                >
                  {isSavingNewChar ? (
                    <><RefreshCw size={14} className="animate-spin" /> চরিত্র সংরক্ষণ ও ৩ডি প্রস্তুত হচ্ছে...</>
                  ) : (
                    <><Sparkles size={14} /> চরিত্র সংরক্ষণ করুন</>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
