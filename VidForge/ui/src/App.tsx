import React, { useState, useEffect, useRef } from 'react';
import { 
  Film, Sparkles, Wand2, Volume2, Video, 
  CheckCircle2, Clock, Trash2, Download, RefreshCw, 
  Tv, Smartphone, Languages, Play, Square, Copy, Check,
  Plus, ArrowRight, BookOpen, Bot, Cpu, AlertTriangle,
  MessageSquare, Send, User, Key, Zap, ExternalLink
} from 'lucide-react';

interface Scene {
  id: number;
  narration: string;
  visual_prompt: string;
  motion_prompt?: string;
  duration?: number;
  image?: string;
}

interface Job {
  id: string;
  title: string;
  story_prompt: string;
  language: string;
  voice: string;
  aspect_ratio: string;
  status: 'QUEUED' | 'SCRIPTING' | 'VOICEOVER' | 'GENERATING_IMAGES' | 'ANIMATING_VIDEO' | 'COMPOSING' | 'DONE' | 'FAILED';
  progress: number;
  current_step: string;
  scenes?: Scene[];
  error_message?: string;
  output_video?: string;
  thumbnail?: string;
  video_type?: string;
  target_duration?: number;
  motion_mode?: string;
  music_theme?: string;
  created_at: number;
}

interface SystemStatus {
  ollama_online: boolean;
  models: string[];
  default_model: string;
  comfyui_online: boolean;
}

const API_BASE = typeof window !== 'undefined' && window.location.port === "8700" ? "" : "http://127.0.0.1:8700";

const ELEVENLABS_VOICE_LIST = [
  { id: "pNInz6obpgDQGcFmaJgB", name: "Adam", desc: "Deep, Authoritative Narration - US Male (Documentary & Epic)", gender: "male" },
  { id: "ErXwobaYiN019PkySvjV", name: "Antoni", desc: "Dramatic Storyteller & Engaging - US Male", gender: "male" },
  { id: "JBFqnCBsd6RMkjVDRZzb", name: "George", desc: "Warm, Eloquent British Documentary - UK Male", gender: "male" },
  { id: "21m00Tcm4TlvDq8ikWAM", name: "Rachel", desc: "Calm, Intimate & Clear Narration - US Female", gender: "female" },
  { id: "EXAVITQu4vr4xnSDxMaL", name: "Bella", desc: "Expressive, Vibrant & Emotional - US Female", gender: "female" },
  { id: "onwK4e9ZLuTAKqWW03F9", name: "Daniel", desc: "Authoritative, Deep Broadcast - UK Male", gender: "male" },
  { id: "TX3LPaxmHKxFdv7VOQHJ", name: "Liam", desc: "Young, Energetic & Direct - US Male", gender: "male" },
  { id: "custom", name: "Custom Voice ID", desc: "Enter your custom ElevenLabs cloned voice ID", gender: "custom" }
];

const F5_VOICE_LIST = [
  { id: "bn_epic_male", name: "Pradeep Seed", desc: "বাংলা গম্ভীর ঐতিহাসিক পুরুষ কণ্ঠ (Local RTX 5070 Ti Clone)", lang: "bn" },
  { id: "bn_soft_female", name: "Nabanita Seed", desc: "বাংলা সাবলীল আবেগঘন নারী কণ্ঠ (Local RTX 5070 Ti Clone)", lang: "bn" },
  { id: "en_nature", name: "Nature & Earth", desc: "English Deep Cinematic Male (Local RTX 5070 Ti Clone)", lang: "en" }
];

const FORMAT_INSPIRATIONS: Record<string, Array<{ title: string; lang: string; prompt: string; duration: number }>> = {
  story: [
    {
      title: "পলাশীর যুদ্ধ (১৭৫৭)",
      lang: "bn",
      duration: 120,
      prompt: "১৭৫৭ সালের ২৩ জুন পলাশীর আমবাগানে নবাব সিরাজউদ্দৌলা এবং লর্ড ক্লাইভের কোম্পানির যুদ্ধ। মীর জাফরের চরম বিশ্বাসঘাতকতা, বৃষ্টিতে বারুদ নষ্ট হওয়া এবং বাংলার স্বাধীনতার সূর্য অস্তমিত হওয়ার মহাকাব্যিক গল্প।"
    },
    {
      title: "সুলতান মুহাম্মদ ফাতিহ (১৪৫৩)",
      lang: "bn",
      duration: 120,
      prompt: "১৪৫৩ সালের এপ্রিল মাস। মাত্র ২১ বছর বয়সী অটোমান সুলতান দ্বিতীয় মুহাম্মদ অপরাজেয় কনস্টান্টিনোপল প্রাচীরের সামনে আসেন। তিনি ডাঙার উপর দিয়ে যুদ্ধজাহাজ টেনে নিয়ে যান এবং দানবীয় কামান দাগেন।"
    },
    {
      title: "তিতুমীরের বাঁশের কেল্লা (১৮৩১)",
      lang: "bn",
      duration: 90,
      prompt: "১৮৩১ সালে নারিকেলবাড়িয়ায় সৈয়দ মীর নিসার আলী তিতুমীরের ব্রিটিশ ও নীলকরদের বিরুদ্ধে বাঁশের কেল্লা তৈরি করে প্রতিরোধ ও বীরত্বপূর্ণ লড়াই।"
    }
  ],
  news: [
    {
      title: "কৃত্রিম বুদ্ধিমত্তা বিপ্লব ও ভবিষ্যৎ অর্থনীতি",
      lang: "bn",
      duration: 90,
      prompt: "আন্তর্জাতিক বাজারে কৃত্রিম বুদ্ধিমত্তা ও জেনারেটিভ এআই প্রযুক্তির অভূতপূর্ব অগ্রগতি। শীর্ষ টেক জায়ান্টদের ট্রিলিয়ন ডলার বিনিয়োগ এবং উন্নয়নশীল দেশগুলোর কর্মসংস্থান ও অর্থনীতিতে এর সুদূরপ্রসারী প্রভাব নিয়ে বিশেষ অনুসন্ধানী প্রতিবেদন।"
    },
    {
      title: "উপকূলীয় অঞ্চলে জলবায়ু পরিবর্তনের প্রভাব",
      lang: "bn",
      duration: 120,
      prompt: "সাম্প্রতিক আন্তর্জাতিক পরিবেশ সম্মেলনের বিশেষ অনুসন্ধান: সমুদ্রপৃষ্ঠের উচ্চতা বৃদ্ধি ও সুন্দরবনসহ দক্ষিণাঞ্চলের লবণাক্ততা সমস্যা। জলবায়ু উদ্বাস্তুদের সুরক্ষা ও জরুরি বাঁধ পুনর্নির্মাণের দাবি।"
    }
  ],
  presentation: [
    {
      title: "VidForge AI Studio: Architecture & Pitch",
      lang: "bn",
      duration: 120,
      prompt: "VidForge AI Studio — স্থানীয় GPU-নির্ভর স্বয়ংক্রিয় সিনেমাটিক ভিডিও প্রোডাকশন প্ল্যাটফর্মের আর্কিটেকচার। সমস্যা: ক্লাউড সার্ভারের চড়া খরচ ও ধীরগতি। সমাধান: Ollama LLM, F5-TTS জিরো-শট ভয়েস ক্লোনিং ও ComfyUI Z-Image টার্বোর রিয়েল-টাইম ইন্টিগ্রেশন।"
    },
    {
      title: "স্মার্ট এগ্রিকালচার আইওটি প্ল্যাটফর্ম ডেমো",
      lang: "bn",
      duration: 90,
      prompt: "কৃষকদের জন্য সাশ্রয়ী স্মার্ট আইওটি সেন্সর নেটওয়ার্ক। মাটির আর্দ্রতা, তাপমাত্রা ও ফসলের রোগবালাই স্বয়ংক্রিয়ভাবে শনাক্তকরণ ও মোবাইল অ্যাপের মাধ্যমে রিয়েল-টাইম সমাধান দেওয়ার প্রজেক্ট শোকেস।"
    }
  ],
  explainer: [
    {
      title: "কোয়ান্টাম কম্পিউটার কীভাবে কাজ করে?",
      lang: "bn",
      duration: 90,
      prompt: "সুপারপজিশন এবং এন্ট্যাঙ্গলমেন্টের রহস্য। সাধারণ সিলিকন বিট (০ ও ১) এবং কোয়ান্টাম কিউবিট (Qubit)-এর পার্থক্য। কেন কোয়ান্টাম কম্পিউটার জটিল রোগবালাই ও আবহাওয়ার পূর্বাভাস কোটি গুণ দ্রুত নির্ণয় করতে পারে?"
    },
    {
      title: "মস্তিষ্কে স্মৃতি কীভাবে তৈরি ও সংরক্ষিত হয়?",
      lang: "bn",
      duration: 90,
      prompt: "মানব মস্তিষ্কের নিউরন ও সিন্যাপসের ভেতর স্মৃতি কীভাবে গঠিত হয়। স্বল্পমেয়াদী স্মৃতি কীভাবে হিপ্পোক্যাম্পাস থেকে দীর্ঘমেয়াদী স্মৃতিতে রূপান্তরিত হয় এবং ঘুমের সময় ব্রেইনের ডেটা ব্যাকআপ প্রক্রিয়া।"
    }
  ],
  commercial: [
    {
      title: "Titan-X আল্ট্রা-ফাস্ট চার্জিং স্মার্টওয়াচ",
      lang: "bn",
      duration: 60,
      prompt: "টাইটানিয়াম গ্রেড ফিনিশ, অ্যামোলেড ডিসপ্লে এবং মাত্র ১০ মিনিটের চার্জে পুরো ৭ দিনের ব্যাটারি লাইফ। সার্বক্ষণিক হার্ট রেট ও ফিটনেস ট্র্যাকিং সহ আপনার লাইফস্টাইলের সেরা পারফেক্ট সঙ্গী।"
    }
  ],
  reel: [
    {
      title: "৩টি টেকনোলজি ট্রিকস যা সময় বাঁচাবে",
      lang: "bn",
      duration: 30,
      prompt: "স্মার্টফোন ও পিসির এমন ৩টি গোপন ট্রিকস যা ৯৯% মানুষ জানে না! কীভাবে সেকেন্ডের মধ্যে যেকোনো ডকুমেন্ট স্ক্যান করবেন এবং শর্টকাট দিয়ে কাজের গতি দ্বিগুণ করবেন।"
    }
  ]
};

const PROMPT_PLACEHOLDERS: Record<string, string> = {
  story: "এখানে আপনার গল্প বা ঐতিহাসিক ঘটনাটি বিস্তারিত লিখুন (যেমন: সুলতান সুলেমান, কনস্টান্টিনোপল, বা কোনো বীরত্বগাথা)...",
  news: "আজকের গুরুত্বপূর্ণ সংবাদ বা অনুসন্ধানী প্রতিবেদনের মূল তথ্য ও ঘটনা লিখুন (যেমন: নতুন প্রযুক্তি আবিষ্কার, বাজেট ঘোষণা, সাম্প্রতিক আন্তর্জাতিক ঘটনা)...",
  presentation: "আপনার প্রজেক্ট বা ব্যবসার নাম, মূল সমস্যা, প্রযুক্তিগত আর্কিটেকচার ও সমাধানের পয়েন্টগুলো লিখুন...",
  explainer: "যে জটিল বা শিক্ষণীয় বিষয়টি সহজভাবে ভেঙে বোঝাতে চান তা লিখুন (যেমন: কোয়ান্টাম কম্পিউটিং কীভাবে কাজ করে, ব্ল্যাক হোল কী)...",
  commercial: "আপনার পণ্য বা সেবার নাম, প্রধান সুবিধা, বিশেষ অফার ও কাস্টমারদের আকর্ষণ করার মূল পয়েন্ট লিখুন...",
  reel: "সোশ্যাল মিডিয়ায় ভাইরাল হওয়ার মতো আকর্ষণীয় শর্ট ভিডিও আইডিয়া ও হুক লিখুন..."
};

const PROMPT_LABELS: Record<string, string> = {
  story: "গল্প বা ঐতিহাসিক কাহিনী (Story Concept):",
  news: "সংবাদের বিষয়বস্তু বা হেডলাইন (News Topic / Reporting Fact):",
  presentation: "প্রজেক্টের মূল বিষয়বস্তু ও বিবরণ (Project Pitch / Tech Demo):",
  explainer: "শিক্ষণীয় বিষয়ের বিবরণ (Explainer / Educational Topic):",
  commercial: "পণ্য বা ব্র্যান্ডের বিবরণ (Commercial / Product Showcase):",
  reel: "ভাইরাল রিল বা শর্টসের টপিক (Viral Hook & Concept):"
};

interface ChatMsg {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

const PERSONA_PROMPTS: Record<string, string> = {
  film_director: "You are a master cinematic film director, historical author, and creative storyteller. Converse naturally with the user in their language (Bengali or English). Brainstorm scenes, write dramatic dialogues, and refine story ideas with vivid descriptions.",
  bangla_writer: "তুমি একজন বিজ্ঞ ও অভিজ্ঞ সাহিত্যিক এবং ঐতিহাসিক লেখক। চমৎকার আবেগঘন ভাষায় ঐতিহাসিক ও কাল্পনিক গল্প লেখো এবং ব্যবহারকারীর সাথে সুন্দর কথোপকথন করো।",
  screenwriter: "You are an expert Hollywood and global screenwriter specialized in punchy dialogues, emotional twists, cinematic tension, and vivid visual action scenes.",
  general: "You are a helpful, creative, and friendly AI assistant powered by Ollama."
};

export default function App() {
  // Navigation State
  const [activeTab, setActiveTab] = useState<"production" | "chat" | "ollama" | "voices" | "gallery">("production");

  // ChatGPT-style Chat State
  const [chatMessages, setChatMessages] = useState<ChatMsg[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "স্বাগতম! আমি আপনার লোকাল Ollama AI সহকারী। আপনি আমার সাথে ChatGPT-র মতো যেকোনো ঐতিহাসিক কাহিনী, গল্পের আইডিয়া, সংলাপ বা স্ক্রিপ্ট নিয়ে মন খুলে আলোচনা করতে পারেন। আপনি কী নিয়ে লিখতে চান?",
      timestamp: Date.now()
    }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [chatModel, setChatModel] = useState<string>("story-writer:latest");
  const [chatPersona, setChatPersona] = useState<string>("film_director");
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  // System & Backend Data
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    ollama_online: false,
    models: ["story-writer:latest", "qwen3.5:9b"],
    default_model: "story-writer:latest",
    comfyui_online: false
  });
  const [jobs, setJobs] = useState<Job[]>([]);
  const [voices, setVoices] = useState<Record<string, Record<string, string>>>({});

  // Multi-Engine TTS State
  const [ttsEngine, setTtsEngine] = useState<"elevenlabs" | "f5tts" | "edge">("elevenlabs");
  const [elevenVoice, setElevenVoice] = useState<string>("pNInz6obpgDQGcFmaJgB"); // Adam
  const [elevenCustomId, setElevenCustomId] = useState<string>("");
  const [f5Voice, setF5Voice] = useState<string>("bn_epic_male");
  const [elevenLabsApiKey, setElevenLabsApiKey] = useState<string>("");
  const [hasElevenLabsKey, setHasElevenLabsKey] = useState<boolean>(false);
  const [maskedKey, setMaskedKey] = useState<string>("");
  const [elevenKeyStatus, setElevenKeyStatus] = useState<{ valid?: boolean; message?: string; tier?: string } | null>(null);
  const [isTestingKey, setIsTestingKey] = useState<boolean>(false);
  const [isSavingKey, setIsSavingKey] = useState<boolean>(false);
  const [showElevenModal, setShowElevenModal] = useState<boolean>(false);
  const [voiceShowcaseEngineFilter, setVoiceShowcaseEngineFilter] = useState<"all" | "elevenlabs" | "f5tts" | "edge">("all");
  
  // Production Form State
  const [videoType, setVideoType] = useState<"story" | "news" | "presentation" | "explainer" | "commercial" | "reel">("story");
  const [targetDuration, setTargetDuration] = useState<number>(120); // Default to 2 minutes
  const [motionMode, setMotionMode] = useState<"kenburns" | "wan" | "static">("kenburns");
  const [musicTheme, setMusicTheme] = useState<string>("cinematic_epic");
  const [storyPrompt, setStoryPrompt] = useState("");
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState<string>("bn");
  const [voice, setVoice] = useState<string>("bn-BD-PradeepNeural");
  const [aspectRatio, setAspectRatio] = useState<"9:16" | "16:9">("9:16");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showInspirations, setShowInspirations] = useState(false);
  const [dismissedFailedJobIds, setDismissedFailedJobIds] = useState<string[]>([]);

  // Ollama Story Studio State
  const [ollamaModel, setOllamaModel] = useState<string>("story-writer:latest");
  const [storyTopic, setStoryTopic] = useState("");
  const [storyLang, setStoryLang] = useState<string>("bn");
  const [storyGenre, setStoryGenre] = useState("historical");
  const [storyTone, setStoryTone] = useState("epic");
  const [storySceneCount, setStorySceneCount] = useState<number>(5);
  const [isGeneratingStory, setIsGeneratingStory] = useState(false);
  const [storyError, setStoryError] = useState<string | null>(null);
  
  // Generated Storyboard State
  const [generatedTitle, setGeneratedTitle] = useState("");
  const [generatedSynopsis, setGeneratedSynopsis] = useState("");
  const [generatedScenes, setGeneratedScenes] = useState<Scene[]>([]);
  const [copySuccess, setCopySuccess] = useState(false);

  // Audio Preview State
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);
  const [loadingVoice, setLoadingVoice] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Switch tab safely with audio cleanup
  const switchTab = (tab: "production" | "chat" | "ollama" | "voices" | "gallery") => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setPlayingVoice(null);
    }
    setActiveTab(tab);
  };

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (activeTab === "chat") {
      chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatMessages, isChatLoading, activeTab]);

  // Send Chat message
  const handleSendChatMessage = async (textOverride?: string) => {
    const text = (textOverride || chatInput).trim();
    if (!text || isChatLoading) return;

    const userMsg: ChatMsg = {
      id: `user_${Date.now()}`,
      role: "user",
      content: text,
      timestamp: Date.now()
    };
    const updatedMessages = [...chatMessages, userMsg];
    setChatMessages(updatedMessages);
    setChatInput("");
    setIsChatLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/ollama/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: chatModel || ollamaModel,
          messages: updatedMessages.map(m => ({ role: m.role, content: m.content })),
          system_prompt: PERSONA_PROMPTS[chatPersona] || PERSONA_PROMPTS.film_director
        })
      });

      if (res.ok) {
        const data = await res.json();
        const assistantMsg: ChatMsg = {
          id: `bot_${Date.now()}`,
          role: "assistant",
          content: data.message,
          timestamp: Date.now()
        };
        setChatMessages(prev => [...prev, assistantMsg]);
      } else {
        const err = await res.json();
        alert("Chat error: " + (err.detail || "Failed to get response"));
      }
    } catch (e: any) {
      alert("Chat connection error: " + e.message);
    } finally {
      setIsChatLoading(false);
    }
  };

  const copyMessage = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMsgId(id);
    setTimeout(() => setCopiedMsgId(null), 2000);
  };

  // 1. Fetch System Status, Jobs, Voices
  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/system/status`);
      if (res.ok) {
        const data: SystemStatus = await res.json();
        setSystemStatus(data);
        if (data.models.length > 0 && !data.models.includes(ollamaModel)) {
          setOllamaModel(data.default_model || data.models[0]);
        }
      }
    } catch {
      // offline fallback
    }
  };

  const fetchJobs = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/jobs`);
      if (res.ok) {
        const data = await res.json();
        setJobs(data);
      }
    } catch (e) {
      console.error("Jobs error:", e);
    }
  };

  const fetchVoices = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/voices`);
      if (res.ok) {
        const data = await res.json();
        setVoices(data);
      }
    } catch (e) {
      console.error("Voices error:", e);
    }
  };

  const fetchTtsConfig = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/tts/config`);
      if (res.ok) {
        const data = await res.json();
        setHasElevenLabsKey(data.has_elevenlabs_key);
        setMaskedKey(data.masked_key || "");
        if (data.default_engine) {
          setTtsEngine(data.default_engine);
        }
      }
    } catch (e) {
      console.error("Failed to fetch TTS config", e);
    }
  };

  const handleSaveElevenKey = async () => {
    if (!elevenLabsApiKey.trim()) return;
    setIsSavingKey(true);
    try {
      const res = await fetch(`${API_BASE}/api/tts/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ elevenlabs_api_key: elevenLabsApiKey.trim() })
      });
      if (res.ok) {
        await fetchTtsConfig();
        setShowElevenModal(false);
        setElevenKeyStatus({ valid: true, message: "ElevenLabs API Key saved successfully!" });
      }
    } catch {
      alert("Failed to save ElevenLabs API key");
    } finally {
      setIsSavingKey(false);
    }
  };

  const handleTestElevenKey = async () => {
    const keyToTest = elevenLabsApiKey.trim();
    if (!keyToTest) {
      alert("Please enter an API key to test");
      return;
    }
    setIsTestingKey(true);
    setElevenKeyStatus(null);
    try {
      const res = await fetch(`${API_BASE}/api/tts/test_key`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: keyToTest })
      });
      const data = await res.json();
      setElevenKeyStatus({
        valid: data.valid,
        message: data.message,
        tier: data.tier
      });
    } catch {
      setElevenKeyStatus({ valid: false, message: "Connection test failed" });
    } finally {
      setIsTestingKey(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchJobs();
    fetchVoices();
    fetchTtsConfig();
    const interval = setInterval(() => {
      fetchJobs();
      fetchStatus();
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  // Update default voice when language changes (for Edge-TTS)
  useEffect(() => {
    if (language === "bn") setVoice("bn-BD-PradeepNeural");
    else if (language === "hi") setVoice("hi-IN-MadhurNeural");
    else if (language === "en") setVoice("en-US-ChristopherNeural");
    else if (language === "ur") setVoice("ur-PK-AsadNeural");
    else if (language === "ar") setVoice("ar-SA-HamedNeural");
  }, [language]);

  // Audio Voice Preview Player
  const playVoiceSample = async (vId: string, engineOverride?: string) => {
    const eng = engineOverride || ttsEngine;
    const playKey = `${eng}:${vId}`;
    if (playingVoice === playKey) {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      setPlayingVoice(null);
      return;
    }

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    setLoadingVoice(playKey);
    try {
      const res = await fetch(`${API_BASE}/api/voices/preview?voice=${encodeURIComponent(vId)}&engine=${eng}`);
      if (res.ok) {
        const data = await res.json();
        const audioUrl = `${API_BASE}${data.url}?t=${Date.now()}`;
        const audio = new Audio(audioUrl);
        audioRef.current = audio;
        audio.onended = () => {
          setPlayingVoice(null);
          audioRef.current = null;
        };
        audio.onerror = () => {
          setPlayingVoice(null);
          setLoadingVoice(null);
          audioRef.current = null;
        };
        await audio.play();
        setPlayingVoice(playKey);
      }
    } catch (err) {
      console.error("Voice play failed", err);
    } finally {
      setLoadingVoice(null);
    }
  };

  // Submit standard production job
  const handleProductionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!storyPrompt.trim()) return;

    let selectedVoice = voice;
    if (ttsEngine === "elevenlabs") {
      selectedVoice = elevenVoice === "custom" ? (elevenCustomId.trim() || "pNInz6obpgDQGcFmaJgB") : elevenVoice;
    } else if (ttsEngine === "f5tts") {
      selectedVoice = f5Voice;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          story_prompt: storyPrompt,
          language,
          voice: selectedVoice,
          tts_engine: ttsEngine,
          aspect_ratio: aspectRatio,
          video_type: videoType,
          target_duration: targetDuration,
          motion_mode: motionMode,
          music_theme: musicTheme
        })
      });

      if (res.ok) {
        setStoryPrompt("");
        setTitle("");
        await fetchJobs();
      }
    } catch {
      alert("Error adding job to queue");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Generate Story Script using Ollama
  const handleGenerateOllamaStory = async () => {
    if (!storyTopic.trim()) return;
    setIsGeneratingStory(true);
    setStoryError(null);

    try {
      const res = await fetch(`${API_BASE}/api/ollama/generate_story`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: storyTopic,
          model: ollamaModel,
          language: storyLang,
          genre: storyGenre,
          tone: storyTone,
          scene_count: storySceneCount,
          video_type: videoType,
          target_duration: targetDuration
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to generate story with Ollama");
      }

      const data = await res.json();
      setGeneratedTitle(data.title || "Untitled Epic");
      setGeneratedSynopsis(data.synopsis || "");
      setGeneratedScenes(data.scenes || []);
    } catch (err: any) {
      setStoryError(err.message || "Failed to generate story with Ollama");
    } finally {
      setIsGeneratingStory(false);
    }
  };

  // Send Ollama Story directly to Video Production Queue
  const handleSendStoryToProduction = async () => {
    if (generatedScenes.length === 0) return;

    let selectedVoice = voice;
    if (ttsEngine === "elevenlabs") {
      selectedVoice = elevenVoice === "custom" ? (elevenCustomId.trim() || "pNInz6obpgDQGcFmaJgB") : elevenVoice;
    } else if (ttsEngine === "f5tts") {
      selectedVoice = f5Voice;
    }

    setIsSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: generatedTitle,
          story_prompt: generatedSynopsis || generatedTitle,
          language: storyLang,
          voice: selectedVoice,
          tts_engine: ttsEngine,
          aspect_ratio: aspectRatio,
          scenes: generatedScenes,
          video_type: videoType,
          target_duration: targetDuration,
          motion_mode: motionMode,
          music_theme: musicTheme
        })
      });

      if (res.ok) {
        await fetchJobs();
        switchTab("production");
      }
    } catch {
      alert("Failed to submit story to production");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Copy full script to clipboard
  const handleCopyScript = () => {
    if (generatedScenes.length === 0) return;
    const fullScript = `🎬 ${generatedTitle}\n📖 ${generatedSynopsis}\n\n` + 
      generatedScenes.map((sc, i) => `[দৃশ্য ${i + 1}]\nভয়েসওভার: ${sc.narration}\nচিত্রায়ন: ${sc.visual_prompt}\nমোশন: ${sc.motion_prompt || 'N/A'}`).join("\n\n");
    
    navigator.clipboard.writeText(fullScript);
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2500);
  };

  // Delete Job
  const handleDelete = async (jobId: string) => {
    if (!confirm("Are you sure you want to remove this video?")) return;
    try {
      await fetch(`${API_BASE}/api/jobs/${jobId}`, { method: "DELETE" });
      setJobs(jobs.filter(j => j.id !== jobId));
    } catch (e) {
      console.error("Delete failed", e);
    }
  };

  const handleDismissFailed = async (jobId: string) => {
    setDismissedFailedJobIds(prev => [...prev, jobId]);
    try {
      await fetch(`${API_BASE}/api/jobs/${jobId}`, { method: "DELETE" });
      setJobs(prev => prev.filter(j => j.id !== jobId));
    } catch (e) {
      console.error("Delete failed", e);
    }
  };

  const activeJob = jobs.find(j => j.status !== 'DONE' && j.status !== 'FAILED');
  const queuedJobs = jobs.filter(j => j.status === 'QUEUED' && j.id !== activeJob?.id);
  const completedJobs = jobs.filter(j => j.status === 'DONE');
  const latestFailedJob = jobs.find(j => j.status === 'FAILED' && !dismissedFailedJobIds.includes(j.id));

  const getStatusBadge = (status: Job['status']) => {
    switch (status) {
      case 'QUEUED':
        return <span style={{ background: '#1e293b', color: '#94a3b8', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, border: '1px solid rgba(255,255,255,0.08)' }}>Queued</span>;
      case 'DONE':
        return <span style={{ background: 'rgba(16, 185, 129, 0.18)', color: '#34d399', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, border: '1px solid rgba(16, 185, 129, 0.3)' }}>Completed</span>;
      case 'FAILED':
        return <span style={{ background: 'rgba(239, 68, 68, 0.18)', color: '#f87171', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, border: '1px solid rgba(239, 68, 68, 0.3)' }}>Failed</span>;
      default:
        return <span style={{ background: 'rgba(59, 130, 246, 0.18)', color: '#60a5fa', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, border: '1px solid rgba(59, 130, 246, 0.35)' }}>Processing...</span>;
    }
  };

  return (
    <div className="studio-container">
      
      {/* Premium Glassmorphic Sticky Top Navbar (Single Slim Row) */}
      <header className="studio-header">
        {/* Brand Left (Compact Single Row) */}
        <div className="studio-brand">
          <div className="brand-logo-badge">
            <Film size={17} color="#ffffff" />
            <div style={{ position: 'absolute', bottom: -2, right: -2, width: 10, height: 10, borderRadius: '50%', background: '#10b981', border: '1.5px solid #0b101e', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Sparkles size={6} color="#000" />
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <h1 className="brand-title">
              VidForge <span style={{ fontSize: 11, letterSpacing: '0.12em', color: '#38bdf8', fontWeight: 800 }}>AI STUDIO</span>
            </h1>
            <span className="brand-badge">PRO v2.5</span>
          </div>
          <div className="brand-subtitle-inline">
            <span className="brand-subtitle-tag">⚡ RTX 5070 Ti</span>
            <span className="brand-subtitle-tag">👑 ElevenLabs</span>
            <span className="brand-subtitle-tag">⚡ F5-TTS</span>
            <span className="brand-subtitle-tag">🎬 Wan 2.1</span>
          </div>
        </div>

        {/* Engine Status Dock Right (Compact Chips) */}
        <div className="engine-status-dock">
          {/* ElevenLabs Capsule */}
          <div
            className="status-capsule clickable"
            onClick={() => setShowElevenModal(true)}
            title="ElevenLabs API Key Configuration"
            style={{
              borderColor: hasElevenLabsKey ? 'rgba(16, 185, 129, 0.35)' : 'rgba(234, 179, 8, 0.35)',
              background: hasElevenLabsKey ? 'rgba(16, 185, 129, 0.1)' : 'rgba(234, 179, 8, 0.1)'
            }}
          >
            <Key size={13} color={hasElevenLabsKey ? '#34d399' : '#facc15'} />
            <span style={{ fontSize: 11, color: '#94a3b8' }}>Eleven:</span>
            <span style={{ fontSize: 11.5, fontWeight: 700, color: hasElevenLabsKey ? '#34d399' : '#facc15' }}>
              {hasElevenLabsKey ? (maskedKey || 'Active') : 'Set Key'}
            </span>
          </div>

          {/* F5-TTS Capsule */}
          <div className="status-capsule" style={{ borderColor: 'rgba(56, 189, 248, 0.3)', background: 'rgba(56, 189, 248, 0.08)' }}>
            <Zap size={13} color="#38bdf8" />
            <span style={{ fontSize: 11, color: '#94a3b8' }}>F5-TTS:</span>
            <span style={{ fontSize: 11.5, fontWeight: 700, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span className="pulse-dot" style={{ width: 5, height: 5, borderRadius: '50%', background: '#38bdf8' }} />
              RTX 5070 Ti
            </span>
          </div>

          {/* Ollama LLM Capsule */}
          <div className="status-capsule" style={{ borderColor: systemStatus.ollama_online ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)' }}>
            <Bot size={13} color={systemStatus.ollama_online ? '#34d399' : '#ef4444'} />
            <span style={{ fontSize: 11, color: '#94a3b8' }}>Story:</span>
            <span style={{ fontSize: 11.5, fontWeight: 700, color: systemStatus.ollama_online ? '#f8fafc' : '#ef4444', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span className={systemStatus.ollama_online ? "pulse-dot" : ""} style={{ width: 5, height: 5, borderRadius: '50%', background: systemStatus.ollama_online ? '#10b981' : '#ef4444' }} />
              {systemStatus.ollama_online ? (ollamaModel || 'Online') : 'Offline'}
            </span>
          </div>

          {/* ComfyUI Capsule */}
          <div className="status-capsule" style={{ borderColor: systemStatus.comfyui_online ? 'rgba(6, 182, 212, 0.25)' : 'rgba(239, 68, 68, 0.25)' }}>
            <Cpu size={13} color={systemStatus.comfyui_online ? '#06b6d4' : '#ef4444'} />
            <span style={{ fontSize: 11, color: '#94a3b8' }}>Video:</span>
            <span style={{ fontSize: 11.5, fontWeight: 700, color: systemStatus.comfyui_online ? '#f8fafc' : '#ef4444', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span className={systemStatus.comfyui_online ? "pulse-dot" : ""} style={{ width: 5, height: 5, borderRadius: '50%', background: systemStatus.comfyui_online ? '#06b6d4' : '#ef4444' }} />
              {systemStatus.comfyui_online ? 'Port 8188' : 'Offline'}
            </span>
          </div>

          {/* Refresh Action Button */}
          <button
            type="button"
            className="refresh-action-btn"
            onClick={() => { fetchJobs(); fetchStatus(); fetchTtsConfig(); }}
            title="Refresh Status & Jobs"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </header>

      {/* Floating Vertical Navigation Dock (Right Side) */}
      <aside className="floating-tabs-dock" aria-label="Studio Navigation">
        {/* Tab 1: Video Production */}
        <button
          type="button"
          className={`floating-tab-btn ${activeTab === 'production' ? 'active' : ''}`}
          onClick={() => switchTab('production')}
          aria-label="Video Production"
        >
          <Film size={20} />
          {activeTab === 'production' && <span className="floating-active-pip" />}
          <div className="floating-tab-tooltip">
            <span className="tooltip-icon">🎬</span>
            <span className="tooltip-title">Video Production</span>
          </div>
        </button>

        {/* Tab 2: Ollama AI Chat (ChatGPT) */}
        <button
          type="button"
          className={`floating-tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => switchTab('chat')}
          aria-label="Ollama AI Chat"
        >
          <MessageSquare size={20} color={activeTab === 'chat' ? '#38bdf8' : '#60a5fa'} />
          <span className="floating-mini-badge">AI</span>
          {activeTab === 'chat' && <span className="floating-active-pip" />}
          <div className="floating-tab-tooltip">
            <span className="tooltip-icon">💬</span>
            <span className="tooltip-title">Ollama AI Chat</span>
            <span className="tooltip-badge">ChatGPT Mode</span>
          </div>
        </button>

        {/* Tab 3: Story & Script Studio */}
        <button
          type="button"
          className={`floating-tab-btn ${activeTab === 'ollama' ? 'active' : ''}`}
          onClick={() => switchTab('ollama')}
          aria-label="Story & Script Studio"
        >
          <Wand2 size={20} color={activeTab === 'ollama' ? '#38bdf8' : '#93c5fd'} />
          {activeTab === 'ollama' && <span className="floating-active-pip" />}
          <div className="floating-tab-tooltip">
            <span className="tooltip-icon">✍️</span>
            <span className="tooltip-title">Story & Script Studio</span>
            <span className="tooltip-sub">Director Lab</span>
          </div>
        </button>

        {/* Tab 4: Voice Artists Showcase */}
        <button
          type="button"
          className={`floating-tab-btn ${activeTab === 'voices' ? 'active' : ''}`}
          onClick={() => switchTab('voices')}
          aria-label="Voice Artist Showcase"
        >
          <Volume2 size={20} color={activeTab === 'voices' ? '#38bdf8' : '#38bdf8'} />
          {activeTab === 'voices' && <span className="floating-active-pip" />}
          <div className="floating-tab-tooltip">
            <span className="tooltip-icon">🎙️</span>
            <span className="tooltip-title">Voice Artists</span>
            <span className="tooltip-badge-gold">F5 & Eleven</span>
          </div>
        </button>

        {/* Tab 5: Video Gallery */}
        <button
          type="button"
          className={`floating-tab-btn ${activeTab === 'gallery' ? 'active' : ''}`}
          onClick={() => switchTab('gallery')}
          aria-label="Video Gallery"
        >
          <Video size={20} color={activeTab === 'gallery' ? '#38bdf8' : '#34d399'} />
          {completedJobs.length > 0 && (
            <span className="floating-count-badge">{completedJobs.length}</span>
          )}
          {activeTab === 'gallery' && <span className="floating-active-pip" />}
          <div className="floating-tab-tooltip">
            <span className="tooltip-icon">🎞️</span>
            <span className="tooltip-title">Video Gallery</span>
            <span className="tooltip-count">{completedJobs.length} Ready</span>
          </div>
        </button>
      </aside>

      {/* Main Tab Viewport - Zero-blink persistent panels */}
      <main className="tab-viewport">
        
        {/* ========================================================================= */}
        {/* TAB 1: PRODUCTION STUDIO                                                  */}
        {/* ========================================================================= */}
        <div className={`tab-pane ${activeTab === 'production' ? 'active' : ''}`}>
          <div style={{ display: 'grid', gridTemplateColumns: '460px 1fr', gap: 26, alignItems: 'start' }}>
            
            {/* Creator Form */}
            <section className="glass-panel" style={{ padding: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Sparkles size={18} color="#60a5fa" />
                  <h2 style={{ fontSize: 17, fontWeight: 700, margin: 0 }}>Fast Video Production</h2>
                </div>
                <button
                  type="button"
                  onClick={() => switchTab("ollama")}
                  style={{ background: 'rgba(37, 99, 235, 0.15)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.35)', padding: '5px 10px', borderRadius: 8, fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 5 }}
                >
                  <Wand2 size={13} /> Write in Ollama Lab
                </button>
              </div>

              {/* Video Format / Production Type Selector */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                  <Film size={14} color="#38bdf8" /> ভিডিওর ধরণ ও উদ্দেশ্য (Production Type):
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 7 }}>
                  {[
                    { id: 'story', label: 'গল্প / ইতিহাস', desc: 'Cinematic Story', icon: '🎬' },
                    { id: 'news', label: 'সংবাদ বুলেটিন', desc: 'News & Report', icon: '📰' },
                    { id: 'presentation', label: 'প্রেজেন্টেশন', desc: 'Project & Pitch', icon: '📊' },
                    { id: 'explainer', label: 'শিক্ষণীয় / টেক', desc: 'Educational Explainer', icon: '🎓' },
                    { id: 'commercial', label: 'বিজ্ঞাপন / প্রোমো', desc: 'Brand Showcase', icon: '💼' },
                    { id: 'reel', label: 'ভাইরাল রিল', desc: 'Viral Social Shorts', icon: '📱' },
                  ].map(item => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => {
                        setVideoType(item.id as any);
                        if (item.id === 'news' || item.id === 'reel') setMusicTheme('cinematic_epic');
                        else if (item.id === 'presentation') setMusicTheme('emotional_drama');
                        else if (item.id === 'explainer') setMusicTheme('ancient_history');
                      }}
                      style={{
                        padding: '8px 6px',
                        borderRadius: 10,
                        background: videoType === item.id ? 'rgba(56, 189, 248, 0.18)' : 'rgba(13, 18, 32, 0.65)',
                        border: videoType === item.id ? '2px solid #38bdf8' : '1px solid rgba(255,255,255,0.08)',
                        color: videoType === item.id ? '#38bdf8' : '#94a3b8',
                        textAlign: 'center',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease'
                      }}
                    >
                      <div style={{ fontSize: 15 }}>{item.icon}</div>
                      <div style={{ fontWeight: 700, fontSize: 11, marginTop: 2, color: videoType === item.id ? '#f8fafc' : '#cbd5e1' }}>{item.label}</div>
                      <div style={{ fontSize: 9.5, opacity: 0.75 }}>{item.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Target Video Duration System */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 7 }}>
                  <label style={{ fontSize: 12, fontWeight: 700, color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: 6, margin: 0 }}>
                    <Clock size={14} color="#60a5fa" /> টার্গেট সময় ও দৈর্ঘ্য (Estimated Duration):
                  </label>
                  <span style={{ fontSize: 11, fontWeight: 700, color: '#38bdf8', background: 'rgba(56, 189, 248, 0.15)', padding: '2px 8px', borderRadius: 12, border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                    ⏱️ {targetDuration >= 60 ? `${Math.floor(targetDuration / 60)} মিনিট ${targetDuration % 60 ? `${targetDuration % 60} সে.` : ''}` : `${targetDuration} সেকেন্ড`}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 6, marginBottom: 8 }}>
                  {[
                    { sec: 30, label: '30s', desc: 'Teaser' },
                    { sec: 60, label: '1 Min', desc: 'Short' },
                    { sec: 120, label: '2 Min', desc: 'Standard' },
                    { sec: 180, label: '3 Min', desc: 'In-Depth' },
                    { sec: 300, label: '5 Min', desc: 'Full Pitch' },
                  ].map(p => (
                    <button
                      key={p.sec}
                      type="button"
                      onClick={() => setTargetDuration(p.sec)}
                      style={{
                        padding: '7px 4px',
                        borderRadius: 8,
                        background: targetDuration === p.sec ? 'rgba(37, 99, 235, 0.25)' : 'rgba(13, 18, 32, 0.6)',
                        border: targetDuration === p.sec ? '2px solid #3b82f6' : '1px solid rgba(255,255,255,0.08)',
                        color: targetDuration === p.sec ? '#60a5fa' : '#94a3b8',
                        textAlign: 'center',
                        cursor: 'pointer'
                      }}
                    >
                      <div style={{ fontWeight: 700, fontSize: 11.5 }}>{p.label}</div>
                      <div style={{ fontSize: 9, opacity: 0.7 }}>{p.desc}</div>
                    </button>
                  ))}
                </div>

                <input
                  type="range"
                  min={15}
                  max={360}
                  step={15}
                  value={targetDuration}
                  onChange={e => setTargetDuration(Number(e.target.value))}
                  style={{ width: '100%', accentColor: '#38bdf8', cursor: 'pointer', marginBottom: 6 }}
                />

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10.5, color: '#94a3b8', background: 'rgba(0,0,0,0.25)', padding: '5px 8px', borderRadius: 6 }}>
                  <span>📊 আনুমানিক: <strong style={{ color: '#f8fafc' }}>{Math.max(2, Math.round(targetDuration / 14))} টি দৃশ্য</strong></span>
                  <span>📝 স্ক্রিপ্ট: <strong style={{ color: '#f8fafc' }}>~{Math.round(targetDuration * 1.95)} শব্দ</strong></span>
                  <span>🎯 দৈর্ঘ্য রেঞ্জ: <strong style={{ color: '#34d399' }}>{Math.max(10, targetDuration - 10)}s – {targetDuration + 10}s</strong></span>
                </div>
              </div>

              {/* Visual Quality & Motion Mode */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 7 }}>
                  <Sparkles size={14} color="#a855f7" /> ভিজ্যুয়াল কোয়ালিটি ও মোশন (Motion Engine):
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 7 }}>
                  <div
                    onClick={() => setMotionMode('kenburns')}
                    style={{
                      padding: '8px 10px',
                      borderRadius: 10,
                      background: motionMode === 'kenburns' ? 'rgba(168, 85, 247, 0.18)' : 'rgba(13, 18, 32, 0.65)',
                      border: motionMode === 'kenburns' ? '2px solid #a855f7' : '1px solid rgba(255,255,255,0.08)',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 3 }}>
                      <span style={{ fontSize: 13 }}>🌟</span>
                      <strong style={{ fontSize: 11.5, color: motionMode === 'kenburns' ? '#c084fc' : '#f8fafc' }}>Ultra HD Ken Burns</strong>
                      <span style={{ fontSize: 9, background: 'rgba(34, 197, 94, 0.2)', color: '#4ade80', padding: '1px 4px', borderRadius: 4, fontWeight: 700 }}>প্রস্তাবিত</span>
                    </div>
                    <div style={{ fontSize: 9.5, color: '#94a3b8', lineHeight: 1.3 }}>
                      স্পষ্ট 8K ছবি + সিনেম্যাটিক জুম-ইন, জুম-আউট ও ফেড ইফেক্ট (ছবি ভাঙার কোনো ঝুঁকি নেই)।
                    </div>
                  </div>

                  <div
                    onClick={() => setMotionMode('wan')}
                    style={{
                      padding: '8px 10px',
                      borderRadius: 10,
                      background: motionMode === 'wan' ? 'rgba(59, 130, 246, 0.18)' : 'rgba(13, 18, 32, 0.65)',
                      border: motionMode === 'wan' ? '2px solid #3b82f6' : '1px solid rgba(255,255,255,0.08)',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 3 }}>
                      <span style={{ fontSize: 13 }}>🤖</span>
                      <strong style={{ fontSize: 11.5, color: motionMode === 'wan' ? '#60a5fa' : '#f8fafc' }}>Wan 2.1 AI Motion</strong>
                      <span style={{ fontSize: 9, background: 'rgba(234, 179, 8, 0.2)', color: '#facc15', padding: '1px 4px', borderRadius: 4, fontWeight: 700 }}>পরীক্ষামূলক</span>
                    </div>
                    <div style={{ fontSize: 9.5, color: '#94a3b8', lineHeight: 1.3 }}>
                      ComfyUI I2V নিউরাল ভিডিও এনিমেশন। ক্যারেক্টার নড়াচড়া তৈরি করে।
                    </div>
                  </div>
                </div>
              </div>

              {/* Quick Inspirations for Active Format */}
              <div style={{ marginBottom: 16 }}>
                <button
                  type="button"
                  onClick={() => setShowInspirations(!showInspirations)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 12px',
                    borderRadius: 10,
                    background: showInspirations ? 'rgba(37, 99, 235, 0.16)' : 'rgba(13, 18, 32, 0.65)',
                    border: '1px solid',
                    borderColor: showInspirations ? 'rgba(59, 130, 246, 0.4)' : 'rgba(255, 255, 255, 0.08)',
                    color: showInspirations ? '#60a5fa' : '#cbd5e1',
                    fontSize: 12.5,
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                    <span>💡</span>
                    <span>Quick Inspirations ({videoType.toUpperCase()} আইডিয়া)</span>
                  </div>
                  <span style={{ fontSize: 11, color: '#94a3b8' }}>
                    {showInspirations ? '▲ Hide' : '▼ Show Ideas'}
                  </span>
                </button>

                {showInspirations && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8, padding: 8, background: 'rgba(9, 13, 24, 0.7)', borderRadius: 10, border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                    {(FORMAT_INSPIRATIONS[videoType] || FORMAT_INSPIRATIONS.story).map((qs, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => {
                          setStoryPrompt(qs.prompt);
                          setTitle(qs.title);
                          setLanguage(qs.lang);
                          if (qs.duration) setTargetDuration(qs.duration);
                        }}
                        style={{ textAlign: 'left', background: 'rgba(13, 18, 32, 0.8)', border: '1px solid rgba(255,255,255,0.06)', padding: '7px 10px', borderRadius: 8, fontSize: 12, color: '#cbd5e1', cursor: 'pointer' }}
                      >
                        ✨ <strong style={{ color: '#60a5fa' }}>{qs.title}</strong>
                        {qs.duration && <span style={{ fontSize: 10, color: '#38bdf8', marginLeft: 8 }}>({qs.duration}s)</span>}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <form onSubmit={handleProductionSubmit}>
                {/* Optional Custom Title */}
                <div style={{ marginBottom: 14 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 5 }}>
                    ভিডিওর শিরোনাম (Title - Optional):
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    placeholder="যেমন: প্রজেক্ট আর্কিটেকচার বা সংবাদ শিরোনাম"
                    style={{ width: '100%', padding: '10px 12px', fontSize: 13 }}
                  />
                </div>

                {/* Dynamic Story/News/Pitch Prompt */}
                <div style={{ marginBottom: 16 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 5 }}>
                    {PROMPT_LABELS[videoType] || "বিষয়বস্তু বা কাহিনী (Prompt):"}
                  </label>
                  <textarea
                    rows={4}
                    required
                    value={storyPrompt}
                    onChange={e => setStoryPrompt(e.target.value)}
                    placeholder={PROMPT_PLACEHOLDERS[videoType] || "এখানে আপনার কাহিনী বা ঘটনাটি বিস্তারিত লিখুন..."}
                    style={{ width: '100%', padding: '10px 12px', fontSize: 13, resize: 'vertical', lineHeight: 1.5 }}
                  />
                </div>

                {/* Language Selection */}
                <div style={{ marginBottom: 16 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 7 }}>
                    <Languages size={14} color="#60a5fa" /> ভাষার নির্বাচন (Narrator Language):
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
                    {[
                      { id: 'bn', label: '🇧🇩 বাংলা' },
                      { id: 'hi', label: '🇮🇳 हिन्दी' },
                      { id: 'en', label: '🇬🇧 English' },
                      { id: 'ur', label: '🇵🇰 اردو' },
                      { id: 'ar', label: '🇸🇦 العربية' }
                    ].map(item => (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => setLanguage(item.id)}
                        style={{
                          padding: '8px 6px',
                          borderRadius: 8,
                          background: language === item.id ? 'rgba(37, 99, 235, 0.2)' : 'rgba(13, 18, 32, 0.6)',
                          border: language === item.id ? '2px solid #3b82f6' : '1px solid rgba(255,255,255,0.08)',
                          color: language === item.id ? '#60a5fa' : '#94a3b8',
                          fontWeight: 600,
                          fontSize: 12,
                          textAlign: 'center'
                        }}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Multi-Engine Voice Artist Selection */}
                <div style={{ marginBottom: 20 }}>
                  <label style={{ fontSize: 12, fontWeight: 700, color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                    <Volume2 size={14} color="#38bdf8" /> ভয়েস ইঞ্জিন ও আর্টিস্ট (TTS Engine & Voice):
                  </label>

                  {/* Engine Switcher */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 12 }}>
                    <button
                      type="button"
                      onClick={() => setTtsEngine("elevenlabs")}
                      style={{
                        padding: '9px 10px',
                        borderRadius: 9,
                        background: ttsEngine === 'elevenlabs' ? 'rgba(37, 99, 235, 0.22)' : 'rgba(13, 18, 32, 0.65)',
                        border: ttsEngine === 'elevenlabs' ? '2px solid #3b82f6' : '1px solid rgba(255,255,255,0.08)',
                        color: ttsEngine === 'elevenlabs' ? '#60a5fa' : '#94a3b8',
                        textAlign: 'center',
                        cursor: 'pointer',
                        fontSize: 12,
                        fontWeight: 700
                      }}
                    >
                      <div>👑 ElevenLabs</div>
                      <div style={{ fontSize: 10, opacity: 0.75, fontWeight: 500, marginTop: 2 }}>Ultra Human</div>
                    </button>

                    <button
                      type="button"
                      onClick={() => setTtsEngine("f5tts")}
                      style={{
                        padding: '9px 10px',
                        borderRadius: 9,
                        background: ttsEngine === 'f5tts' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(13, 18, 32, 0.65)',
                        border: ttsEngine === 'f5tts' ? '2px solid #38bdf8' : '1px solid rgba(255,255,255,0.08)',
                        color: ttsEngine === 'f5tts' ? '#38bdf8' : '#94a3b8',
                        textAlign: 'center',
                        cursor: 'pointer',
                        fontSize: 12,
                        fontWeight: 700
                      }}
                    >
                      <div>⚡ F5-TTS Clone</div>
                      <div style={{ fontSize: 10, opacity: 0.75, fontWeight: 500, marginTop: 2 }}>RTX 5070 Ti</div>
                    </button>

                    <button
                      type="button"
                      onClick={() => setTtsEngine("edge")}
                      style={{
                        padding: '9px 10px',
                        borderRadius: 9,
                        background: ttsEngine === 'edge' ? 'rgba(37, 99, 235, 0.22)' : 'rgba(13, 18, 32, 0.65)',
                        border: ttsEngine === 'edge' ? '2px solid #3b82f6' : '1px solid rgba(255,255,255,0.08)',
                        color: ttsEngine === 'edge' ? '#60a5fa' : '#94a3b8',
                        textAlign: 'center',
                        cursor: 'pointer',
                        fontSize: 12,
                        fontWeight: 700
                      }}
                    >
                      <div>🌐 Edge-TTS</div>
                      <div style={{ fontSize: 10, opacity: 0.75, fontWeight: 500, marginTop: 2 }}>Fast Default</div>
                    </button>
                  </div>

                  {/* Engine 1: ElevenLabs UI */}
                  {ttsEngine === "elevenlabs" && (
                    <div style={{ background: 'rgba(37, 99, 235, 0.08)', border: '1px solid rgba(59, 130, 246, 0.25)', padding: '12px 14px', borderRadius: 10 }}>
                      {!hasElevenLabsKey && (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(234, 179, 8, 0.12)', border: '1px solid rgba(234, 179, 8, 0.3)', padding: '8px 12px', borderRadius: 8, marginBottom: 10 }}>
                          <span style={{ fontSize: 11, color: '#facc15', display: 'flex', alignItems: 'center', gap: 6 }}>
                            <AlertTriangle size={13} /> ElevenLabs API Key প্রয়োজন
                          </span>
                          <button
                            type="button"
                            onClick={() => setShowElevenModal(true)}
                            style={{ background: '#ca8a04', color: '#000', padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700 }}
                          >
                            Set Key
                          </button>
                        </div>
                      )}

                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                        <span style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600 }}>ElevenLabs স্টুডিও ভয়েস:</span>
                        <button
                          type="button"
                          onClick={() => playVoiceSample(elevenVoice, "elevenlabs")}
                          disabled={loadingVoice === `elevenlabs:${elevenVoice}`}
                          style={{ background: playingVoice === `elevenlabs:${elevenVoice}` ? '#ef4444' : 'rgba(37, 99, 235, 0.25)', color: playingVoice === `elevenlabs:${elevenVoice}` ? '#fff' : '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.4)', padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 5 }}
                        >
                          {playingVoice === `elevenlabs:${elevenVoice}` ? <Square size={10} /> : <Play size={10} />}
                          {playingVoice === `elevenlabs:${elevenVoice}` ? 'Stop' : (loadingVoice === `elevenlabs:${elevenVoice}` ? 'Generating...' : '🔊 Test ElevenLabs')}
                        </button>
                      </div>

                      <select
                        value={elevenVoice}
                        onChange={e => setElevenVoice(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', fontSize: 13, marginBottom: elevenVoice === 'custom' ? 8 : 0 }}
                      >
                        {ELEVENLABS_VOICE_LIST.map(ev => (
                          <option key={ev.id} value={ev.id}>{ev.name} — {ev.desc}</option>
                        ))}
                      </select>

                      {elevenVoice === 'custom' && (
                        <input
                          type="text"
                          value={elevenCustomId}
                          onChange={e => setElevenCustomId(e.target.value)}
                          placeholder="ElevenLabs Custom Voice ID (যেমন: 21m00Tcm4TlvDq8ikWAM)"
                          style={{ width: '100%', padding: '8px 12px', fontSize: 12, marginTop: 4 }}
                        />
                      )}
                    </div>
                  )}

                  {/* Engine 2: F5-TTS UI */}
                  {ttsEngine === "f5tts" && (
                    <div style={{ background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.28)', padding: '12px 14px', borderRadius: 10 }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                        <span style={{ fontSize: 11, color: '#38bdf8', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 5 }}>
                          <Zap size={13} /> RTX 5070 Ti Local Zero-Shot Clone
                        </span>
                        <button
                          type="button"
                          onClick={() => playVoiceSample(f5Voice, "f5tts")}
                          disabled={loadingVoice === `f5tts:${f5Voice}`}
                          style={{ background: playingVoice === `f5tts:${f5Voice}` ? '#ef4444' : 'rgba(56, 189, 248, 0.2)', color: playingVoice === `f5tts:${f5Voice}` ? '#fff' : '#38bdf8', border: '1px solid rgba(56, 189, 248, 0.4)', padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 5 }}
                        >
                          {playingVoice === `f5tts:${f5Voice}` ? <Square size={10} /> : <Play size={10} />}
                          {playingVoice === `f5tts:${f5Voice}` ? 'Stop' : (loadingVoice === `f5tts:${f5Voice}` ? 'Cloning on GPU...' : '🔊 Test F5-TTS')}
                        </button>
                      </div>

                      <select
                        value={f5Voice}
                        onChange={e => setF5Voice(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', fontSize: 13 }}
                      >
                        {F5_VOICE_LIST.map(fv => (
                          <option key={fv.id} value={fv.id}>{fv.name} — {fv.desc}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  {/* Engine 3: Edge-TTS UI */}
                  {ttsEngine === "edge" && (
                    <div style={{ background: 'rgba(13, 18, 32, 0.6)', border: '1px solid rgba(255,255,255,0.08)', padding: '12px 14px', borderRadius: 10 }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                        <span style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600 }}>Edge-TTS স্ট্যান্ডার্ড ক্লাউড ভয়েস:</span>
                        <button
                          type="button"
                          onClick={() => playVoiceSample(voice, "edge")}
                          disabled={loadingVoice === `edge:${voice}`}
                          style={{ background: playingVoice === `edge:${voice}` ? '#ef4444' : 'rgba(37, 99, 235, 0.18)', color: playingVoice === `edge:${voice}` ? '#fff' : '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.35)', padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 5 }}
                        >
                          {playingVoice === `edge:${voice}` ? <Square size={10} /> : <Play size={10} />}
                          {playingVoice === `edge:${voice}` ? 'Stop' : (loadingVoice === `edge:${voice}` ? 'Loading...' : '🔊 Test Voice')}
                        </button>
                      </div>

                      <select
                        value={voice}
                        onChange={e => setVoice(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', fontSize: 13 }}
                      >
                        {voices[language] && Object.entries(voices[language]).map(([vId, vLabel]) => (
                          <option key={vId} value={vId}>{vLabel}</option>
                        ))}
                      </select>
                    </div>
                  )}
                </div>

                {/* Aspect Ratio */}
                <div style={{ marginBottom: 22 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 7 }}>
                    ভিডিও রেজোলিউশন ও ফ্রেম ফরম্যাট:
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <button
                      type="button"
                      onClick={() => setAspectRatio("9:16")}
                      style={{
                        padding: '10px 12px',
                        borderRadius: 10,
                        background: aspectRatio === "9:16" ? 'rgba(37, 99, 235, 0.2)' : 'rgba(13, 18, 32, 0.6)',
                        border: aspectRatio === "9:16" ? '2px solid #3b82f6' : '1px solid rgba(255,255,255,0.08)',
                        color: aspectRatio === "9:16" ? '#60a5fa' : '#94a3b8',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        fontSize: 12,
                        fontWeight: 600
                      }}
                    >
                      <Smartphone size={16} />
                      <div style={{ textAlign: 'left' }}>
                        <div>9:16 Vertical</div>
                        <div style={{ fontSize: 10, opacity: 0.7 }}>Shorts / Reels</div>
                      </div>
                    </button>

                    <button
                      type="button"
                      onClick={() => setAspectRatio("16:9")}
                      style={{
                        padding: '10px 12px',
                        borderRadius: 10,
                        background: aspectRatio === "16:9" ? 'rgba(37, 99, 235, 0.2)' : 'rgba(13, 18, 32, 0.6)',
                        border: aspectRatio === "16:9" ? '2px solid #3b82f6' : '1px solid rgba(255,255,255,0.08)',
                        color: aspectRatio === "16:9" ? '#60a5fa' : '#94a3b8',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        fontSize: 12,
                        fontWeight: 600
                      }}
                    >
                      <Tv size={16} />
                      <div style={{ textAlign: 'left' }}>
                        <div>16:9 Landscape</div>
                        <div style={{ fontSize: 10, opacity: 0.7 }}>YouTube Standard</div>
                      </div>
                    </button>
                  </div>
                </div>

                {/* Submit */}
                <button
                  type="submit"
                  disabled={isSubmitting || !storyPrompt.trim()}
                  style={{
                    width: '100%',
                    padding: '13px',
                    borderRadius: 10,
                    background: 'linear-gradient(90deg, #2563eb, #0284c7)',
                    color: '#ffffff',
                    fontWeight: 700,
                    fontSize: 14,
                    boxShadow: '0 4px 18px rgba(37, 99, 235, 0.4)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 8
                  }}
                >
                  <Plus size={16} /> Add to Production Queue
                </button>
              </form>
            </section>

            {/* Right Panel: Live Worker Monitor & Queue */}
            <section style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              {/* Active Job Spotlight */}
              {activeJob ? (
                <div className="glass-panel active-job-glow" style={{ padding: 22 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div className="pulse-dot" style={{ width: 10, height: 10, borderRadius: '50%', background: '#3b82f6', boxShadow: '0 0 10px #3b82f6' }} />
                      <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>Active Job: {activeJob.title}</h3>
                    </div>
                    {getStatusBadge(activeJob.status)}
                  </div>

                  {/* Progress Bar */}
                  <div style={{ marginBottom: 14 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#94a3b8', marginBottom: 6 }}>
                      <span style={{ color: '#cbd5e1' }}>{activeJob.current_step}</span>
                      <span style={{ fontWeight: 700, color: '#60a5fa' }}>{activeJob.progress}%</span>
                    </div>
                    <div style={{ width: '100%', height: 8, background: 'rgba(255,255,255,0.08)', borderRadius: 10, overflow: 'hidden' }}>
                      <div className="progress-bar-animated" style={{ width: `${activeJob.progress}%`, height: '100%', transition: 'width 0.4s ease' }} />
                    </div>
                  </div>

                  {/* Live Scenes Preview */}
                  {activeJob.scenes && activeJob.scenes.length > 0 && (
                    <div style={{ marginTop: 16, borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 14 }}>
                      <label style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', display: 'block', marginBottom: 8 }}>
                        Planned Scenes ({activeJob.scenes.length} দৃশ্য):
                      </label>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: 10 }}>
                        {activeJob.scenes.map((sc, i) => (
                          <div key={i} style={{ background: 'rgba(13, 18, 32, 0.6)', padding: 10, borderRadius: 8, border: '1px solid rgba(255,255,255,0.05)', fontSize: 12 }}>
                            <div style={{ fontWeight: 700, color: '#60a5fa', marginBottom: 4 }}>Scene {sc.id}</div>
                            <p style={{ color: '#cbd5e1', margin: 0, fontSize: 12, lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                              "{sc.narration}"
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {latestFailedJob && (
                    <div className="glass-panel" style={{ padding: 18, border: '1px solid rgba(239, 68, 68, 0.45)', background: 'rgba(239, 68, 68, 0.08)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <AlertTriangle size={18} color="#ef4444" />
                          <h4 style={{ margin: 0, fontSize: 13.5, fontWeight: 700, color: '#f87171' }}>
                            Last Job Failed: {latestFailedJob.title}
                          </h4>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleDismissFailed(latestFailedJob.id)}
                          style={{ background: 'rgba(239, 68, 68, 0.2)', border: '1px solid rgba(239, 68, 68, 0.4)', color: '#fca5a5', padding: '2px 8px', borderRadius: 6, fontSize: 11, cursor: 'pointer' }}
                        >
                          Dismiss / Clear
                        </button>
                      </div>
                      <div style={{ fontSize: 12, color: '#cbd5e1', lineHeight: 1.4, wordBreak: 'break-word', maxHeight: 90, overflowY: 'auto', background: 'rgba(0,0,0,0.3)', padding: '6px 10px', borderRadius: 6 }}>
                        {latestFailedJob.error_message || 'An error occurred during video production.'}
                      </div>
                    </div>
                  )}

                  <div className="glass-panel" style={{ padding: 20, display: 'flex', alignItems: 'center', gap: 14, color: '#94a3b8' }}>
                    <CheckCircle2 size={24} color="#3b82f6" />
                    <div>
                      <div style={{ fontWeight: 600, color: '#f8fafc' }}>Production Pipeline is Idle</div>
                      <div style={{ fontSize: 12 }}>Submit a story on the left, or use the <strong>Ollama Story Studio</strong> tab to write and fine-tune your script.</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Waiting Queue List */}
              <div className="glass-panel" style={{ padding: 20 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Clock size={16} color="#60a5fa" />
                    <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Waiting in Queue ({queuedJobs.length})</h3>
                  </div>
                </div>

                {queuedJobs.length === 0 ? (
                  <div style={{ padding: 24, textAlign: 'center', color: '#64748b', fontSize: 13 }}>
                    No other videos waiting in queue. The next one you add will begin immediately.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {queuedJobs.map((qj, idx) => (
                      <div key={qj.id} style={{ background: 'rgba(13, 18, 32, 0.6)', padding: '12px 16px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                          <span style={{ fontSize: 12, fontWeight: 700, color: '#60a5fa', background: 'rgba(37, 99, 235, 0.15)', width: 24, height: 24, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            {idx + 1}
                          </span>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: 13, color: '#f8fafc' }}>{qj.title}</div>
                            <div style={{ fontSize: 11, color: '#64748b' }}>Language: {qj.language.toUpperCase()} • Format: {qj.aspect_ratio}</div>
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          {getStatusBadge(qj.status)}
                          <button onClick={() => handleDelete(qj.id)} style={{ background: 'none', color: '#ef4444', padding: 4 }}>
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Recent Completed Videos shortcut */}
              {completedJobs.length > 0 && (
                <div className="glass-panel" style={{ padding: 20 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <CheckCircle2 size={16} color="#34d399" />
                      <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Latest Completed Videos</h3>
                    </div>
                    <button
                      onClick={() => switchTab("gallery")}
                      style={{ background: 'none', color: '#60a5fa', fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}
                    >
                      View All in Gallery <ArrowRight size={13} />
                    </button>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 14 }}>
                    {completedJobs.slice(0, 2).map(cj => (
                      <div key={cj.id} style={{ background: 'rgba(13, 18, 32, 0.6)', borderRadius: 10, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.06)' }}>
                        {cj.output_video && (
                          <video
                            src={`${API_BASE}${cj.output_video}`}
                            controls
                            style={{ width: '100%', maxHeight: 160, background: '#000', objectFit: 'contain' }}
                          />
                        )}
                        <div style={{ padding: 10 }}>
                          <div style={{ fontWeight: 600, fontSize: 13, color: '#f8fafc', marginBottom: 4 }}>{cj.title}</div>
                          <a
                            href={`${API_BASE}${cj.output_video}`}
                            download
                            target="_blank"
                            rel="noreferrer"
                            style={{ color: '#34d399', fontSize: 11, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600 }}
                          >
                            <Download size={12} /> Download Video
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </section>

          </div>
        </div>

        {/* ========================================================================= */}
        {/* TAB 2: CHATGPT STYLE OLLAMA CHAT                                          */}
        {/* ========================================================================= */}
        <div className={`tab-pane ${activeTab === 'chat' ? 'active' : ''}`}>
          <div className="chat-workspace">
            {/* Header */}
            <div className="chat-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 34, height: 34, borderRadius: 10, background: 'rgba(37, 99, 235, 0.25)', border: '1px solid rgba(59, 130, 246, 0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <MessageSquare size={17} color="#60a5fa" />
                </div>
                <div>
                  <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: '#f8fafc' }}>
                    Ollama AI Chat (ChatGPT Mode)
                  </h3>
                  <span style={{ fontSize: 11, color: '#94a3b8' }}>
                    আপনার লোকাল LLM-এর সাথে বাংলায় বা ইংরেজিতে চ্যাট করুন
                  </span>
                </div>
              </div>

              {/* Controls */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {/* Persona selector */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600 }}>Persona:</span>
                  <select
                    value={chatPersona}
                    onChange={e => setChatPersona(e.target.value)}
                    style={{ background: 'rgba(13, 18, 32, 0.9)', padding: '5px 8px', fontSize: 12, border: '1px solid rgba(255,255,255,0.1)' }}
                  >
                    <option value="film_director">🎬 Film Director & Storyteller</option>
                    <option value="bangla_writer">📜 বাংলা সাহিত্যিক ও ঐতিহাসিক</option>
                    <option value="screenwriter">⚡ Hollywood Screenwriter</option>
                    <option value="general">🤖 General AI Assistant</option>
                  </select>
                </div>

                {/* Model selector */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 11, color: '#94a3b8', fontWeight: 600 }}>Model:</span>
                  <select
                    value={chatModel}
                    onChange={e => setChatModel(e.target.value)}
                    style={{ background: 'rgba(13, 18, 32, 0.9)', color: '#60a5fa', fontWeight: 700, padding: '5px 8px', fontSize: 12, border: '1px solid rgba(59, 130, 246, 0.35)' }}
                  >
                    {systemStatus.models.map(m => (
                      <option key={m} value={m} style={{ background: '#0f172a', color: '#f8fafc' }}>{m}</option>
                    ))}
                  </select>
                </div>

                {/* Clear Chat */}
                <button
                  type="button"
                  onClick={() => {
                    if (confirm("Are you sure you want to clear this chat?")) {
                      setChatMessages([
                        {
                          id: `welcome_${Date.now()}`,
                          role: "assistant",
                          content: "নতুন কথোপকথন শুরু হলো! আপনি যেকোনো কাহিনী, ডায়ালগ বা পরামর্শ নিয়ে বলতে পারেন।",
                          timestamp: Date.now()
                        }
                      ]);
                    }
                  }}
                  style={{ background: 'rgba(239, 68, 68, 0.12)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.25)', padding: '5px 10px', borderRadius: 8, fontSize: 11, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}
                >
                  <Trash2 size={12} /> Clear
                </button>
              </div>
            </div>

            {/* Scrollable Messages Area */}
            <div className="chat-scroll-area">
              {chatMessages.map(msg => (
                <div key={msg.id} className={`chat-msg-row ${msg.role}`}>
                  {msg.role === 'assistant' && (
                    <div className="chat-avatar assistant">
                      <Bot size={18} />
                    </div>
                  )}

                  <div className={`chat-bubble ${msg.role}`}>
                    <div>{msg.content}</div>

                    {/* Actions for assistant messages */}
                    {msg.role === 'assistant' && msg.id !== 'welcome' && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                        <button
                          type="button"
                          onClick={() => copyMessage(msg.id, msg.content)}
                          style={{ background: 'rgba(255,255,255,0.06)', color: '#cbd5e1', padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}
                        >
                          {copiedMsgId === msg.id ? <Check size={11} color="#34d399" /> : <Copy size={11} />}
                          {copiedMsgId === msg.id ? 'Copied' : 'Copy'}
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            setStoryPrompt(msg.content);
                            switchTab("production");
                          }}
                          style={{ background: 'rgba(37, 99, 235, 0.2)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.35)', padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}
                        >
                          <Film size={11} /> Use in Video Production 🎬
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            setStoryTopic(msg.content);
                            switchTab("ollama");
                          }}
                          style={{ background: 'rgba(6, 182, 212, 0.15)', color: '#38bdf8', border: '1px solid rgba(6, 182, 212, 0.3)', padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}
                        >
                          <Wand2 size={11} /> Convert to Storyboard ✍️
                        </button>
                      </div>
                    )}
                  </div>

                  {msg.role === 'user' && (
                    <div className="chat-avatar user">
                      <User size={18} />
                    </div>
                  )}
                </div>
              ))}

              {/* Typing indicator */}
              {isChatLoading && (
                <div className="chat-msg-row assistant">
                  <div className="chat-avatar assistant">
                    <Bot size={18} />
                  </div>
                  <div className="chat-bubble assistant" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px' }}>
                    <span style={{ fontSize: 12, color: '#94a3b8' }}>Ollama ({chatModel}) উত্তর তৈরি করছে</span>
                    <div style={{ display: 'flex', gap: 3 }}>
                      <div className="typing-dot" />
                      <div className="typing-dot" />
                      <div className="typing-dot" />
                    </div>
                  </div>
                </div>
              )}

              <div ref={chatBottomRef} />
            </div>

            {/* Quick Starter Suggestions */}
            {chatMessages.length <= 2 && (
              <div style={{ padding: '0 20px 10px 20px', display: 'flex', gap: 8, overflowX: 'auto' }}>
                {[
                  "পলাশীর যুদ্ধে মীর জাফরের বিশ্বাসঘাতকতার একটি নাটকীয় দৃশ্য লিখে দাও",
                  "কনস্টান্টিনোপল বিজয়ের দিনে সুলতান মুহাম্মদ ফাতিহের একটি রণহুংকার সংলাপ",
                  "তিতুমীরের বাঁশের কেল্লার বীরত্ব নিয়ে একটি সংক্ষিপ্ত আবেগঘন দৃশ্য রচনা করো",
                  "Write an intense dialogue between two commanders on the night before battle"
                ].map((sugg, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handleSendChatMessage(sugg)}
                    style={{ whiteSpace: 'nowrap', background: 'rgba(13, 18, 32, 0.7)', border: '1px solid rgba(59, 130, 246, 0.25)', color: '#cbd5e1', padding: '6px 12px', borderRadius: 16, fontSize: 11 }}
                  >
                    💡 {sugg}
                  </button>
                ))}
              </div>
            )}

            {/* Chat Input Bar */}
            <div className="chat-input-bar">
              <form
                onSubmit={e => {
                  e.preventDefault();
                  handleSendChatMessage();
                }}
                style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}
              >
                <textarea
                  rows={2}
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendChatMessage();
                    }
                  }}
                  placeholder="ChatGPT-র মতো এখানে লিখুন (Shift + Enter দিয়ে নতুন লাইন, Enter দিয়ে পাঠান)..."
                  style={{ flex: 1, padding: '10px 14px', fontSize: 13.5, resize: 'none', lineHeight: 1.5, maxHeight: 100 }}
                />

                <button
                  type="submit"
                  disabled={isChatLoading || !chatInput.trim()}
                  style={{
                    height: 48,
                    padding: '0 20px',
                    borderRadius: 10,
                    background: 'linear-gradient(90deg, #2563eb, #0284c7)',
                    color: '#ffffff',
                    fontWeight: 700,
                    fontSize: 13,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    boxShadow: '0 4px 16px rgba(37, 99, 235, 0.4)'
                  }}
                >
                  <Send size={15} />
                  <span>Send</span>
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* TAB 3: OLLAMA STORY STUDIO                                                */}
        {/* ========================================================================= */}
        <div className={`tab-pane ${activeTab === 'ollama' ? 'active' : ''}`}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            
            {/* Studio Hero Banner with Blue Glow */}
            <div className="glass-panel" style={{ padding: '22px 26px', background: 'linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(6, 182, 212, 0.05))', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <div style={{ width: 44, height: 44, borderRadius: 12, background: 'rgba(37, 99, 235, 0.25)', border: '1px solid rgba(59, 130, 246, 0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Wand2 size={24} color="#60a5fa" />
                  </div>
                  <div>
                    <h2 style={{ fontSize: 20, fontWeight: 800, margin: '0 0 4px 0', color: '#f8fafc' }}>
                      Ollama AI Story & Script Studio
                    </h2>
                    <p style={{ fontSize: 13, color: '#94a3b8', margin: 0 }}>
                      আপনার লোকাল Ollama LLM মডেল ব্যবহার করে মুহূর্তেই যেকোনো ঐতিহাসিক বা কাল্পনিক ঘটনার দৃশ্যভিত্তিক সম্পূর্ণ চিত্রনাট্য তৈরি ও সম্পাদনা করুন।
                    </p>
                  </div>
                </div>

                {/* Model Selector */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(13, 18, 32, 0.85)', padding: '6px 14px', borderRadius: 10, border: '1px solid rgba(59, 130, 246, 0.3)' }}>
                  <Bot size={16} color="#60a5fa" />
                  <span style={{ fontSize: 12, color: '#94a3b8', fontWeight: 600 }}>Ollama Model:</span>
                  <select
                    value={ollamaModel}
                    onChange={e => setOllamaModel(e.target.value)}
                    style={{ background: 'transparent', border: 'none', color: '#60a5fa', fontWeight: 700, fontSize: 13, cursor: 'pointer', outline: 'none' }}
                  >
                    {systemStatus.models.map(m => (
                      <option key={m} value={m} style={{ background: '#0f172a', color: '#f8fafc' }}>{m}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Generator Controls */}
            <div className="glass-panel" style={{ padding: 24 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 24 }}>
                
                {/* Left Column: Topic & Presets */}
                <div>
                  <label style={{ fontSize: 13, fontWeight: 700, color: '#cbd5e1', display: 'block', marginBottom: 8 }}>
                    কাহিনীর বিষয় বা পটভূমি (Story Topic / Prompt):
                  </label>
                  <textarea
                    rows={4}
                    value={storyTopic}
                    onChange={e => setStoryTopic(e.target.value)}
                    placeholder="যেমন: পলাশীর যুদ্ধ ও মীর জাফরের বিশ্বাসঘাতকতা, সুলতান সালাহউদ্দিন ও জেরুজালেম বিজয়, কিংবা প্রাচীন ময়নামতীর হারিয়ে যাওয়া গুপ্তধন..."
                    style={{ width: '100%', padding: '12px 14px', fontSize: 14, lineHeight: 1.5, marginBottom: 12 }}
                  />

                  {/* Quick Topic Chips */}
                  <div>
                    <span style={{ fontSize: 11, fontWeight: 600, color: '#64748b', display: 'block', marginBottom: 6 }}>জনপ্রিয় আইডিয়া (ক্লিক করে নির্বাচন করুন):</span>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {[
                        "পলাশীর যুদ্ধ এবং মীর জাফরের বিশ্বাসঘাতকতা (১৭৫৭)",
                        "সুলতান মুহাম্মদ ফাতিহ ও কনস্টান্টিনোপল বিজয় (১৪৫৩)",
                        "তিতুমীরের বাঁশের কেল্লা ও বীরত্বগাথা (১৮৩১)",
                        "পানিপথের যুদ্ধ ও বারুদের বিধ্বংসী ব্যবহার (১৫২৬)",
                        "ময়নামতীর রহস্যময় বৌদ্ধ শালবন বিহার",
                        "ঈসা খাঁ ও বারো ভূঁইয়ার নৌযুদ্ধ"
                      ].map((idea, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => setStoryTopic(idea)}
                          style={{ background: 'rgba(13, 18, 32, 0.6)', border: '1px solid rgba(255,255,255,0.08)', padding: '5px 10px', borderRadius: 20, fontSize: 11, color: '#cbd5e1' }}
                        >
                          ⚡ {idea}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Right Column: Parameters (Lang, Genre, Tone, Scene count) */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  {/* Language */}
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 6 }}>
                      চিত্রনাট্যের ভাষা (Narration Language):
                    </label>
                    <select
                      value={storyLang}
                      onChange={e => setStoryLang(e.target.value)}
                      style={{ width: '100%', padding: '9px 12px', fontSize: 13 }}
                    >
                      <option value="bn">🇧🇩 বাংলা (Bengali)</option>
                      <option value="hi">🇮🇳 हिन्दी (Hindi)</option>
                      <option value="en">🇬🇧 English</option>
                      <option value="ur">🇵🇰 اردو (Urdu)</option>
                      <option value="ar">🇸🇦 العربية (Arabic)</option>
                    </select>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                    {/* Genre */}
                    <div>
                      <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 6 }}>
                        কাহিনী ধরন (Genre):
                      </label>
                      <select
                        value={storyGenre}
                        onChange={e => setStoryGenre(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', fontSize: 13 }}
                      >
                        <option value="historical war">মহাকাব্যিক যুদ্ধ (Historical War)</option>
                        <option value="ancient mystery">প্রাচীন রহস্য (Ancient Mystery)</option>
                        <option value="thriller drama">রোমাঞ্চ ও থ্রিলার (Thriller Drama)</option>
                        <option value="spiritual legend">আধ্যাত্মিক ও পৌরাণিক (Spiritual/Myth)</option>
                        <option value="inspirational biography">বীরত্বগাথা ও জীবনী (Biography)</option>
                      </select>
                    </div>

                    {/* Tone */}
                    <div>
                      <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'block', marginBottom: 6 }}>
                        মুড ও সুর (Tone):
                      </label>
                      <select
                        value={storyTone}
                        onChange={e => setStoryTone(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', fontSize: 13 }}
                      >
                        <option value="cinematic epic">মহাকাব্যিক ও গম্ভীর (Cinematic Epic)</option>
                        <option value="dark thrilling">রহস্যময় ও রোমাঞ্চকর (Dark Thrilling)</option>
                        <option value="emotional heartfelt">আবেগঘন ও হৃদয়স্পর্শী (Emotional)</option>
                        <option value="fast-paced intense">তীব্র ও রণহুংকার (Fast & Intense)</option>
                      </select>
                    </div>
                  </div>

                  {/* Scene Count */}
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: '#cbd5e1', display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <span>দৃশ্যের সংখ্যা (Scenes Count):</span>
                      <span style={{ color: '#60a5fa', fontWeight: 700 }}>{storySceneCount} টি দৃশ্য (~{storySceneCount * 7} সেকেন্ড)</span>
                    </label>
                    <div style={{ display: 'flex', gap: 8 }}>
                      {[3, 4, 5, 6].map(cnt => (
                        <button
                          key={cnt}
                          type="button"
                          onClick={() => setStorySceneCount(cnt)}
                          style={{
                            flex: 1,
                            padding: '8px 0',
                            borderRadius: 8,
                            background: storySceneCount === cnt ? 'rgba(37, 99, 235, 0.25)' : 'rgba(13, 18, 32, 0.6)',
                            border: storySceneCount === cnt ? '2px solid #3b82f6' : '1px solid rgba(255,255,255,0.08)',
                            color: storySceneCount === cnt ? '#60a5fa' : '#94a3b8',
                            fontWeight: 700,
                            fontSize: 13
                          }}
                        >
                          {cnt} দৃশ্য
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Generate Button */}
                  <button
                    type="button"
                    onClick={handleGenerateOllamaStory}
                    disabled={isGeneratingStory || !storyTopic.trim()}
                    style={{
                      marginTop: 6,
                      padding: '13px',
                      borderRadius: 10,
                      background: 'linear-gradient(90deg, #2563eb, #0284c7)',
                      color: '#ffffff',
                      fontWeight: 700,
                      fontSize: 14,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 8,
                      boxShadow: '0 4px 20px rgba(37, 99, 235, 0.45)'
                    }}
                  >
                    {isGeneratingStory ? (
                      <>
                        <RefreshCw size={16} className="animate-spin" />
                        <span>Ollama দ্বারা স্টোরি তৈরি হচ্ছে...</span>
                      </>
                    ) : (
                      <>
                        <Wand2 size={16} />
                        <span>Generate Story Script with Ollama</span>
                      </>
                    )}
                  </button>

                </div>
              </div>

              {storyError && (
                <div style={{ marginTop: 16, padding: '12px 16px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: 8, color: '#fca5a5', display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
                  <AlertTriangle size={16} />
                  <span>{storyError}</span>
                </div>
              )}
            </div>

            {/* Generated Storyboard & Scene Editor */}
            {generatedScenes.length > 0 && (
              <div className="glass-panel" style={{ padding: 24 }}>
                
                {/* Header with Title & Synopsis */}
                <div style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: 18, marginBottom: 20 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <BookOpen size={20} color="#60a5fa" />
                      <span style={{ fontSize: 13, fontWeight: 700, color: '#60a5fa', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Ollama Generated Storyboard ({generatedScenes.length} Scenes)
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <button
                        type="button"
                        onClick={handleCopyScript}
                        style={{ background: 'rgba(255,255,255,0.06)', color: '#cbd5e1', padding: '7px 12px', borderRadius: 8, fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}
                      >
                        {copySuccess ? <Check size={14} color="#34d399" /> : <Copy size={14} />}
                        {copySuccess ? 'Copied Script!' : 'Copy Script'}
                      </button>

                      <button
                        type="button"
                        onClick={handleSendStoryToProduction}
                        disabled={isSubmitting}
                        style={{
                          background: 'linear-gradient(90deg, #2563eb, #0284c7)',
                          color: '#fff',
                          padding: '8px 16px',
                          borderRadius: 8,
                          fontSize: 13,
                          fontWeight: 700,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 7,
                          boxShadow: '0 4px 18px rgba(37, 99, 235, 0.4)'
                        }}
                      >
                        <Film size={15} />
                        <span>Send to Video Production Queue 🚀</span>
                      </button>
                    </div>
                  </div>

                  {/* Editable Title */}
                  <input
                    type="text"
                    value={generatedTitle}
                    onChange={e => setGeneratedTitle(e.target.value)}
                    style={{ width: '100%', fontSize: 20, fontWeight: 800, padding: '8px 12px', marginBottom: 8, background: 'rgba(13, 18, 32, 0.4)' }}
                  />

                  {/* Editable Synopsis */}
                  <textarea
                    rows={2}
                    value={generatedSynopsis}
                    onChange={e => setGeneratedSynopsis(e.target.value)}
                    placeholder="Story synopsis / summary..."
                    style={{ width: '100%', fontSize: 13, padding: '8px 12px', background: 'rgba(13, 18, 32, 0.4)', color: '#94a3b8' }}
                  />
                </div>

                {/* Scene Cards List */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {generatedScenes.map((scene, idx) => (
                    <div key={idx} className="scene-card">
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: 8 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ background: '#2563eb', color: '#ffffff', fontWeight: 800, fontSize: 12, padding: '2px 8px', borderRadius: 6 }}>
                            Scene {idx + 1}
                          </span>
                          <span style={{ fontSize: 12, color: '#94a3b8' }}>
                            Est. Duration: ~6-8 seconds
                          </span>
                        </div>

                        <button
                          type="button"
                          onClick={() => {
                            const updated = generatedScenes.filter((_, i) => i !== idx);
                            setGeneratedScenes(updated);
                          }}
                          style={{ background: 'none', color: '#ef4444', padding: 4 }}
                          title="Delete Scene"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 14 }}>
                        {/* Narration voiceover text */}
                        <div>
                          <label style={{ fontSize: 11, fontWeight: 700, color: '#60a5fa', display: 'flex', alignItems: 'center', gap: 5, marginBottom: 5 }}>
                            <Volume2 size={13} /> কণ্ঠস্বরের ভাষ্য (Spoken Voiceover Script):
                          </label>
                          <textarea
                            rows={4}
                            value={scene.narration}
                            onChange={e => {
                              const updated = [...generatedScenes];
                              updated[idx].narration = e.target.value;
                              setGeneratedScenes(updated);
                            }}
                            style={{ width: '100%', padding: '8px 10px', fontSize: 13, lineHeight: 1.5 }}
                          />
                        </div>

                        {/* Visual & Motion Prompts */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          <div>
                            <label style={{ fontSize: 11, fontWeight: 700, color: '#38bdf8', display: 'block', marginBottom: 4 }}>
                              🎨 Visual AI Prompt (ComfyUI চিত্রায়ন প্রম্পট):
                            </label>
                            <textarea
                              rows={2}
                              value={scene.visual_prompt}
                              onChange={e => {
                                const updated = [...generatedScenes];
                                updated[idx].visual_prompt = e.target.value;
                                setGeneratedScenes(updated);
                              }}
                              style={{ width: '100%', padding: '6px 10px', fontSize: 12 }}
                            />
                          </div>

                          <div>
                            <label style={{ fontSize: 11, fontWeight: 700, color: '#34d399', display: 'block', marginBottom: 4 }}>
                              🎬 Motion AI Prompt (Wan 2.1 ভিডিও অ্যানিমেশন প্রম্পট):
                            </label>
                            <textarea
                              rows={2}
                              value={scene.motion_prompt || ""}
                              onChange={e => {
                                const updated = [...generatedScenes];
                                updated[idx].motion_prompt = e.target.value;
                                setGeneratedScenes(updated);
                              }}
                              style={{ width: '100%', padding: '6px 10px', fontSize: 12 }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Add New Scene Button */}
                <div style={{ marginTop: 16, display: 'flex', justifyContent: 'center' }}>
                  <button
                    type="button"
                    onClick={() => {
                      const newScene: Scene = {
                        id: generatedScenes.length + 1,
                        narration: "নতুন দৃশ্যের ভাষ্য এখানে লিখুন...",
                        visual_prompt: "Cinematic 8k photorealistic shot...",
                        motion_prompt: "Slow cinematic camera push in..."
                      };
                      setGeneratedScenes([...generatedScenes, newScene]);
                    }}
                    style={{ background: 'rgba(255,255,255,0.06)', color: '#cbd5e1', border: '1px dashed rgba(59, 130, 246, 0.4)', padding: '9px 18px', borderRadius: 8, fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}
                  >
                    <Plus size={15} /> Add Another Scene
                  </button>
                </div>

              </div>
            )}

          </div>
        </div>

        {/* ========================================================================= */}
        {/* TAB 3: VOICE ARTIST SHOWCASE & MULTI-ENGINE STUDIO                        */}
        {/* ========================================================================= */}
        <div className={`tab-pane ${activeTab === 'voices' ? 'active' : ''}`}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div className="glass-panel" style={{ padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14 }}>
              <div>
                <h2 style={{ fontSize: 19, fontWeight: 800, margin: '0 0 4px 0', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span>🎙️ Voice Studio</span>
                  <span style={{ fontSize: 11, background: 'rgba(37, 99, 235, 0.25)', border: '1px solid rgba(59, 130, 246, 0.4)', color: '#60a5fa', padding: '2px 8px', borderRadius: 12 }}>ElevenLabs + F5-TTS + Edge</span>
                </h2>
                <p style={{ fontSize: 13, color: '#94a3b8', margin: 0 }}>
                  আল্ট্রা-রিয়েলিস্টিক হিউম্যান ভয়েস (ElevenLabs), লোকাল RTX 5070 Ti ভয়েস ক্লোনিং (F5-TTS), অথবা স্ট্যান্ডার্ড ক্লাউড ভয়েস টেস্ট ও সিলেক্ট করুন।
                </p>
              </div>

              {/* Engine Filters */}
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {[
                  { id: 'all', label: '✨ All Engines' },
                  { id: 'elevenlabs', label: '👑 ElevenLabs' },
                  { id: 'f5tts', label: '⚡ F5-TTS (RTX 5070 Ti)' },
                  { id: 'edge', label: '🌐 Edge-TTS' }
                ].map(item => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setVoiceShowcaseEngineFilter(item.id as any)}
                    style={{
                      padding: '7px 14px',
                      borderRadius: 8,
                      background: voiceShowcaseEngineFilter === item.id ? 'rgba(37, 99, 235, 0.25)' : 'rgba(13, 18, 32, 0.65)',
                      border: voiceShowcaseEngineFilter === item.id ? '2px solid #3b82f6' : '1px solid rgba(255,255,255,0.08)',
                      color: voiceShowcaseEngineFilter === item.id ? '#60a5fa' : '#94a3b8',
                      fontWeight: 700,
                      fontSize: 12
                    }}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* ElevenLabs Status Banner (When visible) */}
            {(voiceShowcaseEngineFilter === "all" || voiceShowcaseEngineFilter === "elevenlabs") && (
              <div style={{ background: hasElevenLabsKey ? 'rgba(16, 185, 129, 0.08)' : 'rgba(234, 179, 8, 0.08)', border: hasElevenLabsKey ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(234, 179, 8, 0.25)', padding: '14px 20px', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 38, height: 38, borderRadius: 10, background: hasElevenLabsKey ? 'rgba(16, 185, 129, 0.2)' : 'rgba(234, 179, 8, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Key size={18} color={hasElevenLabsKey ? '#34d399' : '#facc15'} />
                  </div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>
                      ElevenLabs API: {hasElevenLabsKey ? `Connected (${maskedKey})` : 'API Key Not Configured'}
                    </div>
                    <div style={{ fontSize: 12, color: '#94a3b8' }}>
                      {hasElevenLabsKey 
                        ? 'Hyper-realistic human voices with emotional cadence and breathing are fully active.'
                        : 'ElevenLabs API key যোগ করুন যেকোনো ভাষায় হলিউড মানের আসল মানুষের মতো ভয়েস তৈরি করতে।'}
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setShowElevenModal(true)}
                  style={{ background: hasElevenLabsKey ? 'rgba(37, 99, 235, 0.25)' : '#ca8a04', color: hasElevenLabsKey ? '#60a5fa' : '#000', border: '1px solid rgba(59, 130, 246, 0.4)', padding: '8px 16px', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer' }}
                >
                  {hasElevenLabsKey ? '⚙️ Manage API Key' : '🔑 Set ElevenLabs Key'}
                </button>
              </div>
            )}

            {/* F5-TTS Status Banner (When visible) */}
            {(voiceShowcaseEngineFilter === "all" || voiceShowcaseEngineFilter === "f5tts") && (
              <div style={{ background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.25)', padding: '14px 20px', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 38, height: 38, borderRadius: 10, background: 'rgba(56, 189, 248, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Zap size={18} color="#38bdf8" />
                  </div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: '#f8fafc' }}>
                      F5-TTS Voice Cloning: RTX 5070 Ti Active (16GB VRAM)
                    </div>
                    <div style={{ fontSize: 12, color: '#94a3b8' }}>
                      সম্পূর্ণ লোকাল এআই ভয়েস ক্লোনিং। HuggingFace F5-TTS Base মডেল (1.34 GB) ডাউনলোড ও সক্রিয় রয়েছে। কোনো ক্লাউড বিল নেই।
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(13, 18, 32, 0.8)', padding: '6px 12px', borderRadius: 8, border: '1px solid rgba(56, 189, 248, 0.3)', fontSize: 12, color: '#38bdf8', fontWeight: 600 }}>
                  <CheckCircle2 size={14} /> Zero-Shot Model Ready
                </div>
              </div>
            )}

            {/* Voices Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 16 }}>

              {/* 1. ELEVENLABS VOICES */}
              {(voiceShowcaseEngineFilter === "all" || voiceShowcaseEngineFilter === "elevenlabs") && ELEVENLABS_VOICE_LIST.map(ev => {
                const isSelected = ttsEngine === 'elevenlabs' && elevenVoice === ev.id;
                const playKey = `elevenlabs:${ev.id}`;
                const isPlaying = playingVoice === playKey;
                const isLoading = loadingVoice === playKey;

                return (
                  <div
                    key={`el_${ev.id}`}
                    className="glass-panel"
                    style={{
                      padding: 18,
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      border: isSelected ? '2px solid #3b82f6' : '1px solid rgba(255,255,255,0.08)',
                      background: isSelected ? 'rgba(37, 99, 235, 0.14)' : undefined
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                        <span style={{ fontSize: 11, fontWeight: 800, color: '#f59e0b', background: 'rgba(245, 158, 11, 0.16)', padding: '3px 9px', borderRadius: 12, border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                          👑 ElevenLabs Studio
                        </span>
                        {isSelected && (
                          <span style={{ fontSize: 11, fontWeight: 700, color: '#34d399', display: 'flex', alignItems: 'center', gap: 4 }}>
                            <CheckCircle2 size={12} /> Active
                          </span>
                        )}
                      </div>

                      <h4 style={{ fontSize: 16, fontWeight: 800, color: '#f8fafc', margin: '0 0 6px 0' }}>
                        {ev.name}
                      </h4>

                      <p style={{ fontSize: 12, color: '#94a3b8', margin: '0 0 16px 0', lineHeight: 1.45 }}>
                        {ev.desc}
                      </p>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 12 }}>
                      {ev.id !== 'custom' ? (
                        <button
                          type="button"
                          onClick={() => playVoiceSample(ev.id, "elevenlabs")}
                          disabled={isLoading}
                          style={{
                            flex: 1,
                            padding: '8px 12px',
                            borderRadius: 8,
                            background: isPlaying ? '#ef4444' : 'rgba(37, 99, 235, 0.2)',
                            border: '1px solid rgba(59, 130, 246, 0.4)',
                            color: isPlaying ? '#fff' : '#60a5fa',
                            fontWeight: 700,
                            fontSize: 12,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: 6
                          }}
                        >
                          {isPlaying ? <Square size={13} /> : <Play size={13} />}
                          <span>{isPlaying ? 'Stop' : (isLoading ? 'Generating Preview...' : 'Listen Sample')}</span>
                        </button>
                      ) : (
                        <div style={{ flex: 1, fontSize: 11, color: '#94a3b8' }}>
                          Enter custom ID in production form
                        </div>
                      )}

                      <button
                        type="button"
                        onClick={() => {
                          setTtsEngine('elevenlabs');
                          setElevenVoice(ev.id);
                          switchTab("production");
                        }}
                        style={{
                          padding: '8px 14px',
                          borderRadius: 8,
                          background: isSelected ? '#2563eb' : 'rgba(255,255,255,0.06)',
                          color: isSelected ? '#ffffff' : '#cbd5e1',
                          fontWeight: 700,
                          fontSize: 12
                        }}
                      >
                        {isSelected ? 'Selected' : 'Use Voice'}
                      </button>
                    </div>
                  </div>
                );
              })}

              {/* 2. F5-TTS VOICES */}
              {(voiceShowcaseEngineFilter === "all" || voiceShowcaseEngineFilter === "f5tts") && F5_VOICE_LIST.map(fv => {
                const isSelected = ttsEngine === 'f5tts' && f5Voice === fv.id;
                const playKey = `f5tts:${fv.id}`;
                const isPlaying = playingVoice === playKey;
                const isLoading = loadingVoice === playKey;

                return (
                  <div
                    key={`f5_${fv.id}`}
                    className="glass-panel"
                    style={{
                      padding: 18,
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      border: isSelected ? '2px solid #38bdf8' : '1px solid rgba(255,255,255,0.08)',
                      background: isSelected ? 'rgba(56, 189, 248, 0.12)' : undefined
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                        <span style={{ fontSize: 11, fontWeight: 800, color: '#38bdf8', background: 'rgba(56, 189, 248, 0.16)', padding: '3px 9px', borderRadius: 12, border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                          ⚡ F5-TTS (RTX 5070 Ti)
                        </span>
                        {isSelected && (
                          <span style={{ fontSize: 11, fontWeight: 700, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 4 }}>
                            <CheckCircle2 size={12} /> Active
                          </span>
                        )}
                      </div>

                      <h4 style={{ fontSize: 16, fontWeight: 800, color: '#f8fafc', margin: '0 0 6px 0' }}>
                        {fv.name}
                      </h4>

                      <p style={{ fontSize: 12, color: '#94a3b8', margin: '0 0 16px 0', lineHeight: 1.45 }}>
                        {fv.desc}
                      </p>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 12 }}>
                      <button
                        type="button"
                        onClick={() => playVoiceSample(fv.id, "f5tts")}
                        disabled={isLoading}
                        style={{
                          flex: 1,
                          padding: '8px 12px',
                          borderRadius: 8,
                          background: isPlaying ? '#ef4444' : 'rgba(56, 189, 248, 0.2)',
                          border: '1px solid rgba(56, 189, 248, 0.4)',
                          color: isPlaying ? '#fff' : '#38bdf8',
                          fontWeight: 700,
                          fontSize: 12,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: 6
                        }}
                      >
                        {isPlaying ? <Square size={13} /> : <Play size={13} />}
                        <span>{isPlaying ? 'Stop' : (isLoading ? 'Cloning on GPU...' : 'Listen Sample')}</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setTtsEngine('f5tts');
                          setF5Voice(fv.id);
                          switchTab("production");
                        }}
                        style={{
                          padding: '8px 14px',
                          borderRadius: 8,
                          background: isSelected ? '#0284c7' : 'rgba(255,255,255,0.06)',
                          color: isSelected ? '#ffffff' : '#cbd5e1',
                          fontWeight: 700,
                          fontSize: 12
                        }}
                      >
                        {isSelected ? 'Selected' : 'Use Voice'}
                      </button>
                    </div>
                  </div>
                );
              })}

              {/* 3. EDGE-TTS VOICES */}
              {(voiceShowcaseEngineFilter === "all" || voiceShowcaseEngineFilter === "edge") && voices[language] && Object.entries(voices[language]).map(([vId, vLabel]) => {
                const isSelected = ttsEngine === 'edge' && voice === vId;
                const playKey = `edge:${vId}`;
                const isPlaying = playingVoice === playKey;
                const isLoading = loadingVoice === playKey;

                return (
                  <div
                    key={`edge_${vId}`}
                    className="glass-panel"
                    style={{
                      padding: 18,
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      border: isSelected ? '2px solid #3b82f6' : '1px solid rgba(255,255,255,0.08)',
                      background: isSelected ? 'rgba(37, 99, 235, 0.12)' : undefined
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                        <span style={{ fontSize: 11, fontWeight: 700, color: '#60a5fa', background: 'rgba(37, 99, 235, 0.2)', padding: '2px 8px', borderRadius: 12 }}>
                          🌐 Edge-TTS Cloud
                        </span>
                        {isSelected && (
                          <span style={{ fontSize: 11, fontWeight: 700, color: '#34d399', display: 'flex', alignItems: 'center', gap: 4 }}>
                            <CheckCircle2 size={12} /> Active
                          </span>
                        )}
                      </div>

                      <h4 style={{ fontSize: 15, fontWeight: 700, color: '#f8fafc', margin: '0 0 8px 0' }}>
                        {vLabel}
                      </h4>

                      <p style={{ fontSize: 12, color: '#94a3b8', margin: '0 0 16px 0', lineHeight: 1.4 }}>
                        স্ট্যান্ডার্ড দ্রুত ক্লাউড নিউরাল ভয়েস।
                      </p>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 12 }}>
                      <button
                        type="button"
                        onClick={() => playVoiceSample(vId, "edge")}
                        disabled={isLoading}
                        style={{
                          flex: 1,
                          padding: '8px 12px',
                          borderRadius: 8,
                          background: isPlaying ? '#ef4444' : 'rgba(37, 99, 235, 0.18)',
                          border: '1px solid rgba(59, 130, 246, 0.35)',
                          color: isPlaying ? '#fff' : '#60a5fa',
                          fontWeight: 600,
                          fontSize: 12,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: 6
                        }}
                      >
                        {isPlaying ? <Square size={13} /> : <Play size={13} />}
                        <span>{isPlaying ? 'Stop' : (isLoading ? 'Loading...' : 'Listen Sample')}</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setTtsEngine('edge');
                          setVoice(vId);
                          switchTab("production");
                        }}
                        style={{
                          padding: '8px 14px',
                          borderRadius: 8,
                          background: isSelected ? '#2563eb' : 'rgba(255,255,255,0.06)',
                          color: isSelected ? '#ffffff' : '#cbd5e1',
                          fontWeight: 700,
                          fontSize: 12
                        }}
                      >
                        {isSelected ? 'Selected' : 'Use Voice'}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* TAB 4: COMPLETED VIDEOS GALLERY                                           */}
        {/* ========================================================================= */}
        <div className={`tab-pane ${activeTab === 'gallery' ? 'active' : ''}`}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div className="glass-panel" style={{ padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <h2 style={{ fontSize: 18, fontWeight: 800, margin: '0 0 4px 0', color: '#f8fafc' }}>
                  🎞️ Completed Video Productions ({completedJobs.length})
                </h2>
                <p style={{ fontSize: 13, color: '#94a3b8', margin: 0 }}>
                  উৎপাদিত সকল ভিডিও দেখুন, প্রিভিউ প্লে করুন এবং সরাসরি MP4 ডাউনলোড করুন।
                </p>
              </div>
            </div>

            {completedJobs.length === 0 ? (
              <div className="glass-panel" style={{ padding: 48, textAlign: 'center', color: '#64748b' }}>
                <Video size={48} style={{ margin: '0 auto 12px auto', opacity: 0.5 }} />
                <div style={{ fontSize: 16, fontWeight: 600, color: '#f8fafc', marginBottom: 4 }}>No completed videos yet</div>
                <div style={{ fontSize: 13 }}>Generate a video from the Production Studio or Ollama Story Studio to see it here.</div>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 20 }}>
                {completedJobs.map(cj => (
                  <div key={cj.id} className="glass-panel" style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                    {cj.output_video ? (
                      <video
                        src={`${API_BASE}${cj.output_video}`}
                        controls
                        style={{ width: '100%', maxHeight: 240, background: '#000', objectFit: 'contain' }}
                      />
                    ) : (
                      <div style={{ height: 200, background: '#0f172a', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Video size={36} color="#64748b" />
                      </div>
                    )}

                    <div style={{ padding: 16, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                      <div>
                        <h4 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 6px 0', color: '#f8fafc' }}>{cj.title}</h4>
                        <div style={{ fontSize: 11, color: '#64748b', marginBottom: 12 }}>
                          {cj.language === 'bn' ? '🇧🇩 বাংলা' : cj.language === 'hi' ? '🇮🇳 हिन्दी' : '🇬🇧 English'} • {cj.aspect_ratio} • {cj.voice}
                        </div>

                        {/* Scene lines preview */}
                        {cj.scenes && cj.scenes.length > 0 && (
                          <div style={{ background: 'rgba(13, 18, 32, 0.5)', padding: 8, borderRadius: 6, fontSize: 11, color: '#94a3b8', marginBottom: 12 }}>
                            {cj.scenes.length} Scenes Generated
                          </div>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 10 }}>
                        <a
                          href={`${API_BASE}${cj.output_video}`}
                          download
                          target="_blank"
                          rel="noreferrer"
                          style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#34d399', textDecoration: 'none', fontWeight: 600 }}
                        >
                          <Download size={14} /> Download MP4
                        </a>

                        <button onClick={() => handleDelete(cj.id)} style={{ background: 'none', color: '#ef4444', padding: 4 }}>
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </main>

      {/* ElevenLabs API Key Modal */}
      {showElevenModal && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 9999, background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
          <div className="glass-panel" style={{ width: '100%', maxWidth: 520, padding: 28, border: '1px solid rgba(59, 130, 246, 0.4)', boxShadow: '0 20px 50px rgba(0,0,0,0.8)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 36, height: 36, borderRadius: 10, background: 'linear-gradient(135deg, #f59e0b, #d97706)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Key size={18} color="#000" />
                </div>
                <div>
                  <h3 style={{ fontSize: 17, fontWeight: 800, color: '#f8fafc', margin: 0 }}>ElevenLabs API Configuration</h3>
                  <p style={{ fontSize: 12, color: '#94a3b8', margin: 0 }}>Ultra-Realistic Human Voice Narration</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowElevenModal(false)}
                style={{ background: 'none', color: '#94a3b8', fontSize: 18, cursor: 'pointer', padding: 4 }}
              >
                ✕
              </button>
            </div>

            <p style={{ fontSize: 13, color: '#cbd5e1', lineHeight: 1.5, marginBottom: 16 }}>
              ElevenLabs ব্যবহার করে আপনি হলিউড সিনেমার মতো আবেগঘন, সাবলীল মানুষের কণ্ঠ তৈরি করতে পারবেন। আপনার API Key নিচে পেস্ট করুন:
            </p>

            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 700, color: '#60a5fa', display: 'block', marginBottom: 6 }}>
                ElevenLabs API Key (xi-api-key):
              </label>
              <input
                type="password"
                value={elevenLabsApiKey}
                onChange={e => setElevenLabsApiKey(e.target.value)}
                placeholder={hasElevenLabsKey ? `Current Key: ${maskedKey}` : "Paste your key (e.g. sk_... or xi-...)"}
                style={{ width: '100%', padding: '10px 14px', fontSize: 13, borderRadius: 8 }}
              />
              <div style={{ marginTop: 6, display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: '#64748b' }}>
                  {hasElevenLabsKey ? `Active Key: ${maskedKey}` : 'No key saved yet'}
                </span>
                <a
                  href="https://elevenlabs.io"
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: '#60a5fa', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}
                >
                  <ExternalLink size={11} /> Get free key from elevenlabs.io
                </a>
              </div>
            </div>

            {/* Test status banner */}
            {elevenKeyStatus && (
              <div style={{
                background: elevenKeyStatus.valid ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                border: elevenKeyStatus.valid ? '1px solid rgba(16, 185, 129, 0.35)' : '1px solid rgba(239, 68, 68, 0.35)',
                padding: '10px 14px',
                borderRadius: 8,
                fontSize: 12,
                color: elevenKeyStatus.valid ? '#34d399' : '#f87171',
                marginBottom: 16,
                fontWeight: 600
              }}>
                {elevenKeyStatus.valid ? '✅ ' : '❌ '}
                {elevenKeyStatus.message}
              </div>
            )}

            {/* Action buttons */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10, borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 16 }}>
              <button
                type="button"
                onClick={handleTestElevenKey}
                disabled={isTestingKey || !elevenLabsApiKey.trim()}
                style={{ background: 'rgba(255,255,255,0.06)', color: '#cbd5e1', border: '1px solid rgba(255,255,255,0.12)', padding: '9px 16px', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer' }}
              >
                {isTestingKey ? 'Verifying...' : '🔍 Test Key'}
              </button>

              <button
                type="button"
                onClick={handleSaveElevenKey}
                disabled={isSavingKey || !elevenLabsApiKey.trim()}
                style={{ background: 'linear-gradient(135deg, #2563eb, #1d4ed8)', color: '#ffffff', border: 'none', padding: '9px 20px', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer', boxShadow: '0 0 16px rgba(37, 99, 235, 0.4)' }}
              >
                {isSavingKey ? 'Saving...' : '💾 Save & Activate'}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
