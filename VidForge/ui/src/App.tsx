import React, { Fragment, useState, useEffect, useRef } from 'react';
import { 
  Film, Sparkles, Wand2, Volume2, Video, 
  CheckCircle2, Clock, Trash2, Download, RefreshCw, 
  Tv, Smartphone, Languages, Play, Square, Copy, Check,
  Plus, ArrowRight, BookOpen, Bot, Cpu, AlertTriangle,
  MessageSquare, Send, User, Key, Zap, ExternalLink, Mic, Upload, Settings, X, Sun, Moon,
  Newspaper, Presentation, GraduationCap, Megaphone, Clapperboard, Camera, UserRound, Flame,
  Plane, Rabbit, Search, Music, FolderOpen, Image as ImageIcon, PartyPopper, Boxes, Subtitles, Workflow, type LucideIcon
} from 'lucide-react';
import ModelsPage from './ModelsPage';
import BackgroundMusicPicker, { DEFAULT_MUSIC_SETTINGS, type MusicSettings, type MusicTrack } from './BackgroundMusicPicker';
import ThumbnailStudio from './ThumbnailStudio';
import ProjectReviseDialog from './ProjectReviseDialog';
import WorkflowPage from './WorkflowPage';
import { toast, Toaster } from './Toast';
import { LoadMeter, LoadDot, optionLoad } from './LoadMeter';

interface Scene {
  id: number;
  narration: string;
  visual_prompt: string;
  motion_prompt?: string;
  delivery?: string;
  pause_after?: number;
  duration?: number;
  image?: string;
  image_url?: string;
  // Story continuity (filled by the script planner)
  characters?: string[];
  location?: string;
  action?: string;
  continuity?: string;
  music_level?: "low" | "medium" | "high";
  cast?: { name: string; look: string }[];
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
  music_track?: string;
  music_volume?: number;
  voice_volume?: number;
  music_ducking?: number;
  resolution?: number;
  fps?: number;
  thumbnail_design?: string;
  revision?: number;
  created_at: number;
}

interface SystemStatus {
  ollama_online: boolean;
  models: string[];
  default_model: string;
  comfyui_online: boolean;
  platform?: string;
  wan_available?: boolean;
  video_encoder?: string;
  gpu_name?: string;
  vram_used_gb?: number | null;
  vram_total_gb?: number | null;
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

type TtsEngine = "gemini" | "elevenlabs" | "f5tts";
type KeyProvider = "gemini" | "elevenlabs";

interface F5Voice {
  id: string;
  name: string;
  lang: string;
  custom: boolean;
  duration?: number;
  transcript?: string;
}

interface TtsEngines {
  gemini?: { configured: boolean; model: string; voices: Record<string, { name: string; description: string }> };
  elevenlabs?: { configured: boolean; model: string };
  f5tts?: { ready: boolean; voices: F5Voice[] };
}

const ENGINE_OPTIONS: { id: TtsEngine; label: string; sub: string; accent: string }[] = [
  { id: "gemini", label: "✨ Gemini TTS", sub: "Expressive Studio", accent: "var(--a-purple)" },
  { id: "elevenlabs", label: "👑 ElevenLabs", sub: "Ultra Human", accent: "var(--a-blue)" },
  { id: "f5tts", label: "⚡ Local Voice", sub: "Offline · My Voices", accent: "var(--a-sky)" }
];

type VideoType =
  | "story" | "news" | "presentation" | "explainer" | "commercial" | "reel"
  | "documentary" | "biography" | "motivational" | "travel" | "kids" | "animation" | "mystery";

// Production types; ids must match VIDEO_TYPES_CONFIG in backend/ai_engine.py
const VIDEO_TYPES: { id: VideoType; label: string; desc: string; Icon: LucideIcon; music: string }[] = [
  { id: "story", label: "গল্প / ইতিহাস", desc: "Cinematic Story", Icon: Clapperboard, music: "cinematic_epic" },
  { id: "animation", label: "অ্যানিমেশন / কার্টুন", desc: "3D Cartoon & Anime", Icon: Sparkles, music: "emotional_drama" },
  { id: "news", label: "সংবাদ বুলেটিন", desc: "News & Report", Icon: Newspaper, music: "cinematic_epic" },
  { id: "documentary", label: "ডকুমেন্টারি", desc: "Nature & World", Icon: Camera, music: "emotional_drama" },
  { id: "biography", label: "জীবনী", desc: "Life Story", Icon: UserRound, music: "ancient_history" },
  { id: "explainer", label: "শিক্ষণীয় / টেক", desc: "Explainer", Icon: GraduationCap, music: "ancient_history" },
  { id: "presentation", label: "প্রেজেন্টেশন", desc: "Project & Pitch", Icon: Presentation, music: "emotional_drama" },
  { id: "commercial", label: "বিজ্ঞাপন / প্রোমো", desc: "Brand Showcase", Icon: Megaphone, music: "cinematic_epic" },
  { id: "reel", label: "ভাইরাল রিল", desc: "Social Shorts", Icon: Smartphone, music: "cinematic_epic" },
  { id: "motivational", label: "মোটিভেশন", desc: "Self-Improvement", Icon: Flame, music: "cinematic_epic" },
  { id: "travel", label: "ভ্রমণ গাইড", desc: "Travel & Places", Icon: Plane, music: "emotional_drama" },
  { id: "kids", label: "শিশুতোষ গল্প", desc: "Kids & Moral Tale", Icon: Rabbit, music: "emotional_drama" },
  { id: "mystery", label: "রহস্য / অমীমাংসিত", desc: "Mystery & Cases", Icon: Search, music: "ancient_history" },
];

// F5-TTS copies the pacing and emotion of the reference; it clips references beyond ~12s
const MAX_RECORD_SECONDS = 12;

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
    },
    {
      title: "ঈশা খাঁ বনাম মানসিংহ (১৫৯৭)",
      lang: "bn",
      duration: 120,
      prompt: "বারো ভূঁইয়াদের নেতা ঈশা খাঁ ও মোগল সেনাপতি মানসিংহের ঐতিহাসিক দ্বৈরথ। চরিত্র: ঈশা খাঁ (চল্লিশোর্ধ্ব, দৃঢ়চেতা, সবুজ-সোনালি বর্ম), মানসিংহ (রাজপুত সেনাপতি, লাল পাগড়ি, রুপালি বর্ম)। কাহিনী: সোনারগাঁয়ের নৌঘাঁটি থেকে যাত্রা → মোগল বাহিনীর অবরোধ → রক্তক্ষয় এড়াতে একক দ্বৈরথের প্রস্তাব → তলোয়ার ভেঙে যাওয়ার পর ঈশা খাঁর মহানুভবতা → দুই বীরের পারস্পরিক সম্মান ও বন্ধুত্ব।"
    },
    {
      title: "ক্ষুদিরামের শেষ সকাল (১৯০৮)",
      lang: "bn",
      duration: 90,
      prompt: "মাত্র আঠারো বছর বয়সী বিপ্লবী ক্ষুদিরাম বসুর আত্মত্যাগের গল্প। চরিত্র: ক্ষুদিরাম (রোগা কিশোর, সাদা ধুতি-ফতুয়া, উজ্জ্বল চোখ), তাঁর দিদি অপরূপা। কাহিনী: মেদিনীপুরে শৈশব ও দিদির স্নেহ → স্বদেশি আন্দোলনে যোগ → মুজফফরপুরের অভিযান → গ্রেপ্তার ও বিচার → ফাঁসির মঞ্চে হাসিমুখে গীতা হাতে শেষ সকাল → 'একবার বিদায় দে মা' গানে অমর হয়ে থাকা।"
    },
    {
      title: "একুশে ফেব্রুয়ারি ১৯৫২: মায়ের ভাষা",
      lang: "bn",
      duration: 120,
      prompt: "ভাষা আন্দোলনের এক ছাত্রের চোখে ২১ ফেব্রুয়ারি ১৯৫২। চরিত্র: রফিক (বাইশ বছরের ছাত্র, সাদা পাঞ্জাবি, চশমা), তার ছোট বোন নূরজাহান। কাহিনী: ভোরে বোনকে বাংলা বর্ণমালা শেখানো → ঢাকা বিশ্ববিদ্যালয়ের আমতলায় ছাত্রসমাবেশ → ১৪৪ ধারা ভঙ্গের সিদ্ধান্ত → মিছিলে গুলি → শহীদের রক্তে রাঙা রাজপথ → বোনের হাতে প্রথম শহীদ মিনারে ফুল, মায়ের ভাষার জয়।"
    },
    {
      title: "লালকমল-নীলকমল (ঠাকুরমার ঝুলি)",
      lang: "bn",
      duration: 120,
      prompt: "ঠাকুরমার ঝুলির চিরকালের রূপকথা। চরিত্র: লালকমল (লাল পোশাক, সাহসী বড় ভাই), নীলকমল (নীল পোশাক, বুদ্ধিমান ছোট ভাই), রাক্ষসী রানি, তেপান্তরের মাঠের রাক্ষসের দল। কাহিনী: রাজপ্রাসাদে দুই ভাইয়ের ভালোবাসা → রাক্ষসী রানির ষড়যন্ত্র → গভীর রাতে রাক্ষসদের আক্রমণ → 'লালকমল জাগো, নীলকমল জাগো' ডাক → দুই ভাইয়ের বুদ্ধি ও সাহসে রাক্ষসপুরী জয় → রাজ্যে শান্তি ফেরা। শিশু-কিশোরদের উপযোগী, ভয়ংকর রক্তপাত ছাড়া।"
    },
    {
      title: "গোপাল ভাঁড় ও রাজার আম",
      lang: "bn",
      duration: 60,
      prompt: "রাজা কৃষ্ণচন্দ্রের রাজসভায় গোপাল ভাঁড়ের রসিক বুদ্ধির গল্প। চরিত্র: গোপাল ভাঁড় (গোলগাল মুখ, টাক মাথা, হলুদ চাদর), রাজা কৃষ্ণচন্দ্র (রাজকীয় পোশাক, মুকুট), লোভী মন্ত্রী। কাহিনী: রাজবাগানের সেরা আম চুরির রহস্য → মন্ত্রীর মিথ্যা অভিযোগ গোপালের উপর → গোপালের মজার ফাঁদ → আসল চোর মন্ত্রী ধরা পড়া → রাজার হাসি ও গোপালের পুরস্কার।"
    },
    {
      title: "সুন্দরবনের মধুয়াল: বাবা ও ছেলে",
      lang: "bn",
      duration: 120,
      prompt: "সুন্দরবনে মধু সংগ্রহে যাওয়া এক বাবা ও কিশোর ছেলের রোমাঞ্চকর গল্প। চরিত্র: হাসেম মাঝি (পঞ্চাশ বছরের অভিজ্ঞ মৌয়াল, গামছা মাথায়, রোদে পোড়া মুখ), ছেলে জুয়েল (চোদ্দ বছর, লাল গেঞ্জি)। কাহিনী: ভোরে নৌকায় যাত্রা → গহীন বনে মৌচাকের খোঁজ → ধোঁয়া দিয়ে মধু সংগ্রহ → হঠাৎ কাদায় বাঘের পায়ের ছাপ → নিঃশব্দ উত্তেজনা ও বাবার সাহসী সিদ্ধান্ত → নিরাপদে নৌকায় ফেরা, প্রকৃতির প্রতি শ্রদ্ধার শিক্ষা।"
    },
    {
      title: "নদীভাঙনের পর: আমেনার নতুন ঘর",
      lang: "bn",
      duration: 90,
      prompt: "যমুনার ভাঙনে ঘর হারানো এক মায়ের লড়াই ও আশার গল্প। চরিত্র: আমেনা (পঁয়ত্রিশ বছর, সবুজ শাড়ি, শক্ত মনের মা), মেয়ে তিথি (আট বছর, স্কুলের নীল জামা)। কাহিনী: বর্ষার রাতে নদীতে ঘর বিলীন হওয়া → বাঁধের উপর অস্থায়ী আশ্রয় → সেলাই মেশিনে আমেনার নতুন জীবিকা → তিথির স্কুলে ফেরা → বছর শেষে নিজের হাতে গড়া নতুন ঘরে প্রথম সন্ধ্যার প্রদীপ।"
    },
    {
      title: "পুণ্ড্রনগরের হারানো রাজধানী",
      lang: "bn",
      duration: 120,
      prompt: "মহাস্থানগড়ে লুকিয়ে থাকা আড়াই হাজার বছরের পুরোনো নগরীর রহস্য। চরিত্র: ড. সায়রা (প্রত্নতত্ত্ববিদ, খাকি পোশাক, টুপি), স্থানীয় বৃদ্ধ গাইড করিম চাচা। কাহিনী: করতোয়া নদীর তীরে প্রাচীন ইটের দেয়াল → খননে ব্রাহ্মী লিপির শিলালিপি আবিষ্কার → করিম চাচার মুখে লোককাহিনী → মৌর্য যুগের বাণিজ্যনগরীর কল্পিত পুনর্জাগরণ → অমীমাংসিত প্রশ্ন: কেন হারিয়ে গেল এই নগরী?"
    },
    {
      title: "বাতিঘরের শেষ প্রহরী",
      lang: "bn",
      duration: 90,
      prompt: "সেন্ট মার্টিনের কাছে এক নির্জন বাতিঘরের রহস্যময় রাত। চরিত্র: বৃদ্ধ প্রহরী মতিন (সাদা দাড়ি, নীল উলের সোয়েটার, হাতে লণ্ঠন), ঝড়ে পথহারা জেলে নৌকা। কাহিনী: শেষ দায়িত্বের রাতে প্রচণ্ড ঝড় → বাতিঘরের আলো হঠাৎ নিভে যাওয়া → সিঁড়ি বেয়ে উঠে পুরোনো যন্ত্র মেরামতের লড়াই → দূরে বিপদগ্রস্ত নৌকার সংকেত → আলো জ্বলে ওঠা ও জেলেদের তীরে ফেরা → ভোরে মতিনের শান্ত বিদায়।"
    },
    {
      title: "বেহুলা-লখিন্দর: ভেলায় ভেসে যাওয়া প্রেম",
      lang: "bn",
      duration: 120,
      prompt: "মনসামঙ্গল কাব্যের অমর লোককাহিনী। চরিত্র: বেহুলা (লাল বেনারসি, অবিচল চোখ), লখিন্দর (সুদর্শন যুবক, রাজবেশ), চাঁদ সওদাগর (লখিন্দরের পিতা)। কাহিনী: লোহার বাসরঘরে বিবাহের রাত → সাপের দংশনে লখিন্দরের মৃত্যু → বেহুলার কলার ভেলায় স্বামীর দেহ নিয়ে নদীযাত্রা → পথে নানা বিপদ ও অটল প্রতিজ্ঞা → দেবসভায় নৃত্য ও প্রার্থনা → লখিন্দরের প্রাণ ফিরে পাওয়া।"
    },
    {
      title: "झाँसी की रानी: अंतिम युद्ध (1858)",
      lang: "hi",
      duration: 120,
      prompt: "रानी लक्ष्मीबाई के अदम्य साहस की कहानी। पात्र: रानी लक्ष्मीबाई (युद्ध-वेश, लाल अंगरखा, पीठ पर बंधा दत्तक पुत्र दामोदर), सेनापति तात्या टोपे, घोड़ा बादल। कथा: झाँसी के किले की घेराबंदी → 'मैं अपनी झाँसी नहीं दूँगी' की प्रतिज्ञा → रात में किले की दीवार से घोड़े पर छलाँग → काल्पी और ग्वालियर तक संघर्ष → कोटा की सराय में अंतिम युद्ध → अमर बलिदान और प्रेरणा।"
    },
    {
      title: "बंदर और मगरमच्छ (पंचतंत्र)",
      lang: "hi",
      duration: 60,
      prompt: "पंचतंत्र की बुद्धिमानी भरी कहानी, बच्चों के लिए। पात्र: चतुर बंदर रक्तमुख (भूरे बाल, जामुन के पेड़ पर), भोला मगरमच्छ करालमुख (हरा, बड़ी मुस्कान), मगरमच्छ की लालची पत्नी। कथा: नदी किनारे जामुन बाँटकर दोस्ती → पत्नी की बंदर का दिल खाने की ज़िद → मगरमच्छ की पीठ पर नदी की सैर → बीच धारा में सच्चाई का पता चलना → 'दिल तो पेड़ पर रह गया' वाली चतुराई → बंदर का सुरक्षित लौटना और सच्ची दोस्ती की सीख।"
    },
    {
      title: "The Lighthouse Keeper's Daughter",
      lang: "en",
      duration: 90,
      prompt: "A coastal tale of courage. Characters: Grace (12, braided red hair, yellow raincoat), her father Thomas (keeper, grey beard, navy wool coat). Story: Thomas falls ill on the night of a great storm → a ship's distress flare over the reef → Grace climbs the tower alone and relights the great lamp → she signals the ship away from the rocks with the lantern → dawn reveals the rescued sailors waving from the shore → father and daughter watch the calm sea together."
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
  ],
  documentary: [
    {
      title: "সুন্দরবনের রয়েল বেঙ্গল টাইগার",
      lang: "bn",
      duration: 120,
      prompt: "পৃথিবীর বৃহত্তম ম্যানগ্রোভ বন সুন্দরবনে রয়েল বেঙ্গল টাইগারের জীবন। জোয়ার-ভাটার নদী পেরিয়ে সাঁতার, শিকারের কৌশল, লবণাক্ত পানিতে টিকে থাকার রহস্য এবং বিলুপ্তির হুমকি।"
    }
  ],
  biography: [
    {
      title: "বেগম রোকেয়া: নারী জাগরণের অগ্রদূত",
      lang: "bn",
      duration: 120,
      prompt: "১৮৮০ সালে রংপুরের পায়রাবন্দে জন্ম। গোপনে ভাইয়ের কাছে লেখাপড়া শেখা, 'সুলতানার স্বপ্ন' রচনা, সাখাওয়াত মেমোরিয়াল গার্লস স্কুল প্রতিষ্ঠা এবং নারী শিক্ষার জন্য আজীবন সংগ্রামের অনুপ্রেরণামূলক জীবনী।"
    }
  ],
  motivational: [
    {
      title: "ব্যর্থতা থেকে ঘুরে দাঁড়ানো",
      lang: "bn",
      duration: 60,
      prompt: "বারবার ব্যর্থ হয়ে যারা হাল ছেড়ে দিতে চান তাদের জন্য। থমাস এডিসনের হাজারবার চেষ্টা থেকে শিক্ষা, প্রতিদিন ১% উন্নতির শক্তি এবং আজ থেকেই নতুন করে শুরু করার দৃঢ় আহ্বান।"
    }
  ],
  travel: [
    {
      title: "সাজেক ভ্যালি: মেঘের রাজ্যে একদিন",
      lang: "bn",
      duration: 90,
      prompt: "রাঙামাটির সাজেক ভ্যালি ভ্রমণ গাইড। ভোরের মেঘের সমুদ্র, কংলাক পাহাড়ের চূড়া, আদিবাসী সংস্কৃতি ও খাবার, যাওয়ার সেরা সময়, খরচ এবং প্রয়োজনীয় টিপস।"
    }
  ],
  kids: [
    {
      title: "খরগোশ ও কচ্ছপের নতুন দৌড়",
      lang: "bn",
      duration: 60,
      prompt: "বনের মাঠে অহংকারী খরগোশ আর ধীর কিন্তু ধৈর্যশীল কচ্ছপের মজার দৌড় প্রতিযোগিতা। বন্ধুদের সাহায্য, পরিশ্রম ও ধৈর্যের জয় — শেষে একটি সুন্দর নৈতিক শিক্ষা।"
    }
  ],
  animation: [
    {
      title: "জাদুর বনের খুদে রোবট",
      lang: "bn",
      duration: 60,
      prompt: "একটি ঘন জাদুর বনে পথ হারিয়ে ফেলা এক ছোট্ট বন্ধুত্বপূর্ণ এআই রোবটের রোমাঞ্চকর অভিযান। পিক্সার স্টাইলের কিউট ক্যারেক্টার ডিজাইন, বনের পশুপাখিদের সাথে বন্ধুত্ব এবং তার বাড়ি ফিরে যাওয়ার সুন্দর গল্প।"
    },
    {
      title: "চাঁদের দেশে ছোট্ট চড়ুই",
      lang: "bn",
      duration: 60,
      prompt: "একটি ছোট্ট দুঃসাহসী চড়ুই পাখির চাঁদে যাওয়ার রঙিন স্বপ্ন। চমৎকার 3D কার্টুন অ্যানিমেশন, রাতের তারাভরা আকাশ এবং স্বপ্ন পূরণের মিষ্টি গল্প।"
    }
  ],
  mystery: [
    {
      title: "বারমুডা ট্রায়াঙ্গলের রহস্য",
      lang: "bn",
      duration: 120,
      prompt: "আটলান্টিক মহাসাগরের বারমুডা ট্রায়াঙ্গলে জাহাজ ও বিমান নিখোঁজ হওয়ার রহস্যময় ঘটনা। ফ্লাইট ১৯-এর অন্তর্ধান, বৈজ্ঞানিক ব্যাখ্যা, প্রচলিত তত্ত্ব এবং অমীমাংসিত প্রশ্ন।"
    }
  ]
};

const PROMPT_PLACEHOLDERS: Record<string, string> = {
  story: "এখানে আপনার গল্প বা ঐতিহাসিক ঘটনাটি বিস্তারিত লিখুন (যেমন: সুলতান সুলেমান, কনস্টান্টিনোপল, বা কোনো বীরত্বগাথা)...",
  animation: "অ্যানিমেটেড ফিল্ম বা কার্টুনের গল্প, চরিত্রদের চেহারা ও রূপরেখা লিখুন (যেমন: পিক্সার স্টাইলের খুদে রোবট, রূপকথার ড্রাগন)...",
  news: "আজকের গুরুত্বপূর্ণ সংবাদ বা অনুসন্ধানী প্রতিবেদনের মূল তথ্য ও ঘটনা লিখুন (যেমন: নতুন প্রযুক্তি আবিষ্কার, বাজেট ঘোষণা, সাম্প্রতিক আন্তর্জাতিক ঘটনা)...",
  presentation: "আপনার প্রজেক্ট বা ব্যবসার নাম, মূল সমস্যা, প্রযুক্তিগত আর্কিটেকচার ও সমাধানের পয়েন্টগুলো লিখুন...",
  explainer: "যে জটিল বা শিক্ষণীয় বিষয়টি সহজভাবে ভেঙে বোঝাতে চান তা লিখুন (যেমন: কোয়ান্টাম কম্পিউটিং কীভাবে কাজ করে, ব্ল্যাক হোল কী)...",
  commercial: "আপনার পণ্য বা সেবার নাম, প্রধান সুবিধা, বিশেষ অফার ও কাস্টমারদের আকর্ষণ করার মূল পয়েন্ট লিখুন...",
  reel: "সোশ্যাল মিডিয়ায় ভাইরাল হওয়ার মতো আকর্ষণীয় শর্ট ভিডিও আইডিয়া ও হুক লিখুন...",
  documentary: "প্রকৃতি, প্রাণী বা পৃথিবীর যে বিষয়ের ডকুমেন্টারি বানাতে চান তা লিখুন (যেমন: সুন্দরবনের বাঘ, আমাজন বন, মহাসাগরের গভীরতা)...",
  biography: "যার জীবনী বানাতে চান তার নাম ও জীবনের মূল ঘটনা, সংগ্রাম ও অর্জনগুলো লিখুন...",
  motivational: "যে বিষয়ে অনুপ্রেরণা দিতে চান তা লিখুন (যেমন: ব্যর্থতা থেকে ঘুরে দাঁড়ানো, সময়ের মূল্য, স্বপ্ন পূরণ)...",
  travel: "যে জায়গার ভ্রমণ গাইড বানাতে চান তার নাম ও দেখার মতো স্থান, খাবার, সংস্কৃতি লিখুন...",
  kids: "শিশুদের জন্য গল্পের চরিত্র, ঘটনা এবং শেষে যে নৈতিক শিক্ষা দিতে চান তা লিখুন...",
  mystery: "যে রহস্যময় বা অমীমাংসিত ঘটনা নিয়ে ভিডিও বানাতে চান তা লিখুন (যেমন: বারমুডা ট্রায়াঙ্গল, হারানো শহর)..."
};

const PROMPT_LABELS: Record<string, string> = {
  story: "গল্প বা ঐতিহাসিক কাহিনী (Story Concept):",
  animation: "কার্টুন বা অ্যানিমেশনের গল্প (Cartoon / Animation Concept):",
  news: "সংবাদের বিষয়বস্তু বা হেডলাইন (News Topic / Reporting Fact):",
  presentation: "প্রজেক্টের মূল বিষয়বস্তু ও বিবরণ (Project Pitch / Tech Demo):",
  explainer: "শিক্ষণীয় বিষয়ের বিবরণ (Explainer / Educational Topic):",
  commercial: "পণ্য বা ব্র্যান্ডের বিবরণ (Commercial / Product Showcase):",
  reel: "ভাইরাল রিল বা শর্টসের টপিক (Viral Hook & Concept):",
  documentary: "ডকুমেন্টারির বিষয় (Documentary Subject):",
  biography: "যার জীবনী (Biography Subject & Key Events):",
  motivational: "অনুপ্রেরণার বিষয় (Motivational Theme):",
  travel: "ভ্রমণের গন্তব্য (Travel Destination):",
  kids: "শিশুতোষ গল্পের ধারণা (Kids Story & Moral):",
  mystery: "রহস্যের বিবরণ (Mystery / Unsolved Case):"
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

type TabId = "production" | "chat" | "ollama" | "voices" | "gallery" | "models" | "workflow";

// ?tab= slug for each tab, so a reload or shared link opens the same tab
const TAB_SLUGS: Record<TabId, string> = {
  production: "video-production",
  chat: "ollama-ai-chat",
  ollama: "script-studio",
  voices: "voice-artists",
  gallery: "projects",
  models: "ai-models",
  workflow: "how-it-works",
};

const tabFromUrl = (): TabId => {
  const slug = new URLSearchParams(window.location.search).get("tab");
  const match = (Object.keys(TAB_SLUGS) as TabId[]).find(id => TAB_SLUGS[id] === slug);
  return match || "production";
};

export default function App() {
  // Navigation State
  const [activeTab, setActiveTab] = useState<TabId>(tabFromUrl);

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
  const [chatModel, setChatModel] = useState<string>("qwen3.5:9b");
  const [chatPersona, setChatPersona] = useState<string>("film_director");
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);
  const chatBottomRef = useRef<HTMLDivElement | null>(null);

  // System & Backend Data
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    ollama_online: false,
    models: ["qwen3.5:9b", "story-writer:latest"],
    default_model: "qwen3.5:9b",
    comfyui_online: false
  });
  const [jobs, setJobs] = useState<Job[]>([]);
  const [engines, setEngines] = useState<TtsEngines>({});

  // Multi-Engine TTS State
  const [ttsEngine, setTtsEngine] = useState<TtsEngine>("gemini");
  const [geminiVoice, setGeminiVoice] = useState<string>("Charon");
  const [elevenVoice, setElevenVoice] = useState<string>("pNInz6obpgDQGcFmaJgB"); // Adam
  const [elevenCustomId, setElevenCustomId] = useState<string>("");
  const [f5Voice, setF5Voice] = useState<string>("bn_epic_male");
  const [keyInput, setKeyInput] = useState<string>("");
  const [hasElevenLabsKey, setHasElevenLabsKey] = useState<boolean>(false);
  const [maskedKey, setMaskedKey] = useState<string>("");
  const [hasGeminiKey, setHasGeminiKey] = useState<boolean>(false);
  const [geminiMaskedKey, setGeminiMaskedKey] = useState<string>("");
  const [keyStatus, setKeyStatus] = useState<{ valid?: boolean; message?: string; tier?: string } | null>(null);
  const [isTestingKey, setIsTestingKey] = useState<boolean>(false);
  const [isSavingKey, setIsSavingKey] = useState<boolean>(false);
  const [keyModal, setKeyModal] = useState<KeyProvider | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">(() =>
    document.documentElement.dataset.theme === "light" ? "light" : "dark"
  );
  const settingsRef = useRef<HTMLDivElement | null>(null);
  const [voiceShowcaseEngineFilter, setVoiceShowcaseEngineFilter] = useState<"all" | TtsEngine>("all");

  // My Voices (F5-TTS reference recordings)
  const [newVoiceName, setNewVoiceName] = useState("");
  const [newVoiceTranscript, setNewVoiceTranscript] = useState("");
  const [newVoiceLang, setNewVoiceLang] = useState("bn");
  const [newVoiceFile, setNewVoiceFile] = useState<File | null>(null);
  const [newVoiceUrl, setNewVoiceUrl] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [isSavingVoice, setIsSavingVoice] = useState(false);
  const [voiceUploadError, setVoiceUploadError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const recordTimerRef = useRef<number | null>(null);
  
  // Production Form State
  const [videoType, setVideoType] = useState<VideoType>("story");
  const [targetDuration, setTargetDuration] = useState<number>(120); // Default to 2 minutes
  const [motionMode, setMotionMode] = useState<"kenburns" | "wan" | "static">("kenburns");
  const [musicTheme, setMusicTheme] = useState<string>("cinematic_epic");
  const [musicTracks, setMusicTracks] = useState<MusicTrack[]>([]);
  const [musicLoadFailed, setMusicLoadFailed] = useState(false);
  const [musicSettings, setMusicSettings] = useState<MusicSettings>(DEFAULT_MUSIC_SETTINGS);
  const [storyPrompt, setStoryPrompt] = useState("");
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState<string>("bn");
  const [aspectRatio, setAspectRatio] = useState<"9:16" | "16:9">("9:16");
  const [enableSubtitles, setEnableSubtitles] = useState<boolean>(true);
  const [resolution, setResolution] = useState<480 | 720 | 1080 | 1440>(1080);
  const [localTtsModel, setLocalTtsModel] = useState<string>("f5");
  const [localTtsModels, setLocalTtsModels] = useState<Record<string, { label: string; clone: boolean; languages: string; licence: string }>>({});
  const [fps, setFps] = useState<24 | 25 | 30 | 60>(30);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showInspirations, setShowInspirations] = useState(false);
  const [dismissedFailedJobIds, setDismissedFailedJobIds] = useState<string[]>([]);
  // Projects: thumbnail editor, refine/regenerate dialog, and the "video ready" prompt
  const [thumbStudioJobId, setThumbStudioJobId] = useState<string | null>(null);
  const [reviseTarget, setReviseTarget] = useState<{ id: string; mode: "refine" | "regenerate" } | null>(null);
  const [justFinishedId, setJustFinishedId] = useState<string | null>(null);
  const [jobToDelete, setJobToDelete] = useState<Job | null>(null);
  const [showDeleteAllConfirm, setShowDeleteAllConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const jobStatusRef = useRef<Record<string, Job['status']>>({});


  // Ollama Story Studio State
  const [ollamaModel, setOllamaModel] = useState<string>("qwen3.5:9b");
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
  const [narratorStyle, setNarratorStyle] = useState("");
  const [generatedScenes, setGeneratedScenes] = useState<Scene[]>([]);
  const [copySuccess, setCopySuccess] = useState(false);

  // Audio Preview State
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);
  const [loadingVoice, setLoadingVoice] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Switch tab safely with audio cleanup
  const switchTab = (tab: TabId, fromHistory = false) => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setPlayingVoice(null);
    }
    setActiveTab(tab);
    if (!fromHistory) {
      const url = new URL(window.location.href);
      if (url.searchParams.get("tab") !== TAB_SLUGS[tab]) {
        url.searchParams.set("tab", TAB_SLUGS[tab]);
        window.history.pushState({ tab }, "", url);
      }
    }
  };

  // Browser back/forward moves between tabs
  useEffect(() => {
    const onPop = () => switchTab(tabFromUrl(), true);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

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
        const err = await res.json().catch(() => ({}));
        toast.error("Chat error", err.detail || "Failed to get a response from Ollama.");
      }
    } catch (e: any) {
      toast.error("Chat connection error", e.message);
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
        const data: Job[] = await res.json();
        const previous = jobStatusRef.current;
        const finished = data.find(j => j.status === 'DONE' && previous[j.id] && previous[j.id] !== 'DONE');
        if (finished) setJustFinishedId(finished.id);
        jobStatusRef.current = Object.fromEntries(data.map(j => [j.id, j.status]));
        setJobs(data);
      }
    } catch (e) {
      console.error("Jobs error:", e);
    }
  };

  const fetchEngines = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/tts/engines`);
      if (res.ok) {
        setEngines(await res.json());
      }
    } catch (e) {
      console.error("TTS engines error:", e);
    }
  };

  const fetchMusicTracks = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/music`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setMusicTracks((await res.json()).tracks || []);
      setMusicLoadFailed(false);
    } catch (e) {
      console.error("Music library error:", e);
      setMusicLoadFailed(true);
    }
  };

  // Background music fields for /api/jobs ("" track = no music)
  const musicJobFields = () => ({
    music_track: musicSettings.enabled ? musicSettings.track : "",
    music_volume: musicSettings.musicVolume,
    voice_volume: musicSettings.voiceVolume,
    music_ducking: musicSettings.ducking,
  });

  const fetchTtsConfig = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/tts/config`);
      if (res.ok) {
        const data = await res.json();
        setHasElevenLabsKey(data.has_elevenlabs_key);
        setMaskedKey(data.masked_key || "");
        setHasGeminiKey(data.has_gemini_key);
        setGeminiMaskedKey(data.gemini_masked_key || "");
        if (data.default_engine) {
          setTtsEngine(data.default_engine);
        }
        if (data.local_tts_model) setLocalTtsModel(data.local_tts_model);
        if (data.local_tts_models) setLocalTtsModels(data.local_tts_models);
      }
    } catch (e) {
      console.error("Failed to fetch TTS config", e);
    }
  };

  // The local voice model applies to every new job (saved to the backend config)
  const chooseLocalTtsModel = async (model: string) => {
    const previous = localTtsModel;
    setLocalTtsModel(model);
    try {
      const res = await fetch(`${API_BASE}/api/tts/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ local_tts_model: model })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch (e) {
      console.error("Failed to save local voice model", e);
      setLocalTtsModel(previous);
    }
  };

  const openKeyModal = (provider: KeyProvider) => {
    setKeyInput("");
    setKeyStatus(null);
    setKeyModal(provider);
  };

  // Close the settings popup on Escape or a click outside it (the key dialog stays usable)
  useEffect(() => {
    if (!showSettings) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape" && !keyModal) setShowSettings(false); };
    const onClick = (e: MouseEvent) => {
      if (!keyModal && settingsRef.current && !settingsRef.current.contains(e.target as Node)) setShowSettings(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [showSettings, keyModal]);

  // Apply the theme and remember it for this browser (index.html applies it before first paint)
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("vidforge-theme", theme);
    } catch {
      // storage unavailable (private mode); the theme still applies for this visit
    }
  }, [theme]);

  const toggleTheme = () => setTheme(t => (t === "dark" ? "light" : "dark"));

  const setDefaultEngine = async (engine: TtsEngine) => {
    setTtsEngine(engine);
    try {
      await fetch(`${API_BASE}/api/tts/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ default_engine: engine })
      });
    } catch (e) {
      console.error("Failed to save default voice engine", e);
    }
  };

  const providerName = (provider: KeyProvider) => provider === "gemini" ? "Gemini" : "ElevenLabs";

  const handleSaveKey = async () => {
    if (!keyModal || !keyInput.trim()) return;
    setIsSavingKey(true);
    try {
      const field = keyModal === "gemini" ? "gemini_api_key" : "elevenlabs_api_key";
      const res = await fetch(`${API_BASE}/api/tts/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [field]: keyInput.trim() })
      });
      if (res.ok) {
        await Promise.all([fetchTtsConfig(), fetchEngines()]);
        setKeyModal(null);
      }
    } catch {
      toast.error(`Failed to save ${providerName(keyModal)} API key`);
    } finally {
      setIsSavingKey(false);
    }
  };

  const handleTestKey = async () => {
    const keyToTest = keyInput.trim();
    if (!keyModal || !keyToTest) return;
    setIsTestingKey(true);
    setKeyStatus(null);
    try {
      const res = await fetch(`${API_BASE}/api/tts/test_key`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: keyToTest, provider: keyModal })
      });
      const data = await res.json();
      setKeyStatus({ valid: data.valid, message: data.message, tier: data.tier });
    } catch {
      setKeyStatus({ valid: false, message: "Connection test failed" });
    } finally {
      setIsTestingKey(false);
    }
  };

  const setVoiceRecording = (blob: Blob, filename: string) => {
    if (newVoiceUrl) URL.revokeObjectURL(newVoiceUrl);
    setNewVoiceFile(new File([blob], filename, { type: blob.type }));
    setNewVoiceUrl(URL.createObjectURL(blob));
  };

  const startRecording = async () => {
    setVoiceUploadError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
      recorder.onstop = () => {
        stream.getTracks().forEach(track => track.stop());
        if (recordTimerRef.current) window.clearInterval(recordTimerRef.current);
        const mime = recorder.mimeType || "audio/webm";
        setVoiceRecording(new Blob(chunks, { type: mime }), mime.includes("mp4") ? "recording.m4a" : "recording.webm");
        setIsRecording(false);
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecordSeconds(0);
      setIsRecording(true);
      recordTimerRef.current = window.setInterval(() => setRecordSeconds(sec => sec + 1), 1000);
    } catch {
      setVoiceUploadError("Microphone access was blocked. Allow it in your browser, or upload a recording instead.");
    }
  };

  const stopRecording = () => {
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
  };

  useEffect(() => {
    if (isRecording && recordSeconds >= MAX_RECORD_SECONDS) stopRecording();
  }, [isRecording, recordSeconds]);

  const handleSaveCustomVoice = async () => {
    if (!newVoiceFile || !newVoiceName.trim() || !newVoiceTranscript.trim()) return;
    setIsSavingVoice(true);
    setVoiceUploadError(null);
    try {
      const form = new FormData();
      form.append("name", newVoiceName.trim());
      form.append("transcript", newVoiceTranscript.trim());
      form.append("language", newVoiceLang);
      form.append("file", newVoiceFile);
      const res = await fetch(`${API_BASE}/api/voices/custom`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) {
        setVoiceUploadError(data.detail || "Could not save this voice");
        return;
      }
      await fetchEngines();
      setTtsEngine("f5tts");
      setF5Voice(data.id);
      setNewVoiceName("");
      setNewVoiceTranscript("");
      setNewVoiceFile(null);
      if (newVoiceUrl) URL.revokeObjectURL(newVoiceUrl);
      setNewVoiceUrl(null);
    } catch {
      setVoiceUploadError("Upload failed. Is the VidForge backend running?");
    } finally {
      setIsSavingVoice(false);
    }
  };

  const handleDeleteCustomVoice = async (voiceId: string, voiceName: string) => {
    if (!confirm(`Delete your voice "${voiceName}"? The recording is removed from this computer.`)) return;
    try {
      await fetch(`${API_BASE}/api/voices/custom/${voiceId}`, { method: "DELETE" });
      await fetchEngines();
    } catch (e) {
      console.error("Delete voice failed", e);
    }
  };

  const geminiVoiceEntries = Object.entries(engines.gemini?.voices || {});
  const f5Voices = engines.f5tts?.voices || [];

  // Keep the F5 selection valid after a custom voice is deleted
  useEffect(() => {
    if (f5Voices.length > 0 && !f5Voices.some(v => v.id === f5Voice)) setF5Voice(f5Voices[0].id);
  }, [f5Voices, f5Voice]);

  const selectedVoiceId = () => {
    if (ttsEngine === "elevenlabs") {
      return elevenVoice === "custom" ? (elevenCustomId.trim() || "pNInz6obpgDQGcFmaJgB") : elevenVoice;
    }
    return ttsEngine === "f5tts" ? f5Voice : geminiVoice;
  };

  useEffect(() => {
    fetchStatus();
    fetchJobs();
    fetchEngines();
    fetchTtsConfig();
    fetchMusicTracks();
    const interval = setInterval(() => {
      fetchJobs();
      fetchStatus();
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  // Wan 2.1 cannot run on every platform (e.g. macOS); fall back to Ken Burns there
  const wanAvailable = systemStatus.wan_available !== false;
  useEffect(() => {
    if (!wanAvailable && motionMode === 'wan') setMotionMode('kenburns');
  }, [wanAvailable, motionMode]);

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
      const res = await fetch(`${API_BASE}/api/voices/preview?voice=${encodeURIComponent(vId)}&engine=${eng}&language=${language}`);
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

  const renderPreviewButton = (vId: string, engine: TtsEngine, accent: string) => {
    const playKey = `${engine}:${vId}`;
    const isPlaying = playingVoice === playKey;
    const isLoading = loadingVoice === playKey;
    return (
      <button
        type="button"
        onClick={() => playVoiceSample(vId, engine)}
        disabled={isLoading}
        style={{ background: isPlaying ? '#ef4444' : 'var(--line-soft)', color: isPlaying ? '#fff' : accent, border: `1px solid color-mix(in srgb, ${accent} 40%, transparent)`, padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 5 }}
      >
        {isPlaying ? <Square size={10} /> : <Play size={10} />}
        {isPlaying ? 'Stop' : (isLoading ? 'Generating...' : '🔊 Test Voice')}
      </button>
    );
  };

  const renderKeyWarning = (provider: KeyProvider) => (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgb(234 179 8 / calc(0.12 * var(--tint)))', border: '1px solid rgb(234 179 8 / calc(0.3 * var(--tint)))', padding: '8px 12px', borderRadius: 8, marginBottom: 10 }}>
      <span style={{ fontSize: 11, color: 'var(--a-yellow)', display: 'flex', alignItems: 'center', gap: 6 }}>
        <AlertTriangle size={13} /> {providerName(provider)} API Key প্রয়োজন
      </span>
      <button
        type="button"
        onClick={() => openKeyModal(provider)}
        style={{ background: '#ca8a04', color: '#000', padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700 }}
      >
        Set Key
      </button>
    </div>
  );

  const renderKeyBanner = (provider: KeyProvider) => {
    const hasKey = provider === "gemini" ? hasGeminiKey : hasElevenLabsKey;
    const masked = provider === "gemini" ? geminiMaskedKey : maskedKey;
    const model = provider === "gemini" ? engines.gemini?.model : engines.elevenlabs?.model;
    return (
      <div className={`key-banner ${hasKey ? 'ok' : 'warn'}`}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
          <span className="key-banner-icon"><Key size={16} /></span>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--t-strong)' }}>
              {providerName(provider)} API · {hasKey ? `Connected (${masked})` : 'Key not configured'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--t-muted)' }}>
              {hasKey
                ? `Model ${model || ''} — scene-by-scene emotion, whispers and pauses are active.`
                : `${providerName(provider)} API key যোগ করুন আবেগপূর্ণ, মানুষের মতো স্বাভাবিক কণ্ঠ তৈরি করতে।`}
            </div>
          </div>
        </div>
        <button type="button" className={`btn ${hasKey ? 'btn-ghost' : 'btn-primary'}`} onClick={() => openKeyModal(provider)}>
          <Key size={13} /> {hasKey ? 'Manage key' : `Set ${providerName(provider)} key`}
        </button>
      </div>
    );
  };

  const renderVoiceCard = (card: { engine: TtsEngine; id: string; name: string; desc: string; badge: string; mine?: boolean; previewable?: boolean; onDelete?: () => void }) => {
    const isSelected = ttsEngine === card.engine && selectedVoiceId() === card.id;
    const playKey = `${card.engine}:${card.id}`;
    const isPlaying = playingVoice === playKey;
    const isLoading = loadingVoice === playKey;
    const selectVoice = () => {
      setTtsEngine(card.engine);
      if (card.engine === 'gemini') setGeminiVoice(card.id);
      else if (card.engine === 'elevenlabs') setElevenVoice(card.id);
      else setF5Voice(card.id);
      switchTab("production");
    };

    return (
      <div key={playKey} className={`voice-card ${isSelected ? 'active' : ''}`}>
        <div className="voice-card-top">
          <span className={`voice-avatar ${card.mine ? 'mine' : ''}`} aria-hidden="true">
            {card.name.trim().charAt(0).toUpperCase()}
          </span>
          <div className="voice-card-id">
            <h4>{card.name}</h4>
            <span>{card.badge}</span>
          </div>
          {isSelected && (
            <span className="voice-active-tag"><CheckCircle2 size={12} /> Active</span>
          )}
        </div>

        <p className="voice-desc" title={card.desc}>{card.desc}</p>

        <div className="voice-card-actions">
          {card.previewable === false ? (
            <span className="voice-note">Enter the ID in the production form</span>
          ) : (
            <button
              type="button"
              className={`btn ${isPlaying ? 'btn-secondary' : 'btn-ghost'}`}
              onClick={() => playVoiceSample(card.id, card.engine)}
              disabled={isLoading}
              style={{ flex: 1 }}
            >
              {isPlaying ? <Square size={12} /> : <Play size={12} />}
              {isPlaying ? 'Stop' : (isLoading ? 'Generating...' : 'Listen')}
            </button>
          )}
          {card.onDelete && (
            <button type="button" className="btn btn-icon btn-danger-ghost" onClick={card.onDelete} title="Delete this voice" aria-label={`Delete ${card.name}`}>
              <Trash2 size={13} />
            </button>
          )}
          <button
            type="button"
            className={`btn ${isSelected ? 'btn-primary' : 'btn-ghost'}`}
            onClick={selectVoice}
          >
            {isSelected ? <><Check size={13} /> Selected</> : 'Use voice'}
          </button>
        </div>
      </div>
    );
  };

  // Submit standard production job
  const handleProductionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!storyPrompt.trim()) return;

    const selectedVoice = selectedVoiceId();

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
          music_theme: musicTheme,
          enable_subtitles: enableSubtitles,
          resolution,
          fps,
          ...musicJobFields()
        })
      });

      if (res.ok) {
        setStoryPrompt("");
        setTitle("");
        await fetchJobs();
      }
    } catch {
      toast.error("Error adding job to queue");
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
      setNarratorStyle(data.narrator_style || "");
    } catch (err: any) {
      setStoryError(err.message || "Failed to generate story with Ollama");
    } finally {
      setIsGeneratingStory(false);
    }
  };

  // Send Ollama Story directly to Video Production Queue
  const handleSendStoryToProduction = async () => {
    if (generatedScenes.length === 0) return;

    const selectedVoice = selectedVoiceId();

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
          narrator_style: narratorStyle,
          video_type: videoType,
          target_duration: targetDuration,
          motion_mode: motionMode,
          music_theme: musicTheme,
          enable_subtitles: enableSubtitles,
          resolution,
          fps,
          ...musicJobFields()
        })
      });

      if (res.ok) {
        await fetchJobs();
        switchTab("production");
      }
    } catch {
      toast.error("Failed to submit story to production");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Copy full script to clipboard
  const handleCopyScript = () => {
    if (generatedScenes.length === 0) return;
    const fullScript = `🎬 ${generatedTitle}\n📖 ${generatedSynopsis}\n\n` + 
      generatedScenes.map((sc, i) => `[দৃশ্য ${i + 1}]\nভয়েসওভার: ${sc.narration}\nডেলিভারি: ${sc.delivery || 'N/A'}\nচিত্রায়ন: ${sc.visual_prompt}\nমোশন: ${sc.motion_prompt || 'N/A'}`).join("\n\n");
    
    navigator.clipboard.writeText(fullScript);
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2500);
  };

  // Open project delete confirmation modal
  const handleDelete = (job: Job) => {
    setJobToDelete(job);
  };

  // Perform project deletion after user confirmation
  const confirmDeleteProject = async (job: Job) => {
    setIsDeleting(true);
    try {
      const res = await fetch(`${API_BASE}/api/jobs/${job.id}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      setJobs(prev => prev.filter(j => j.id !== job.id));
      if (justFinishedId === job.id) setJustFinishedId(null);
      if (reviseTarget?.id === job.id) setReviseTarget(null);
      if (thumbStudioJobId === job.id) setThumbStudioJobId(null);
      setDismissedFailedJobIds(prev => prev.filter(id => id !== job.id));
      setJobToDelete(null);
      fetchJobs();
    } catch (e: any) {
      console.error("Delete failed", e);
      toast.error("Could not delete the project", String(e.message || e));
    } finally {
      setIsDeleting(false);
    }
  };

  // Open delete all projects confirmation modal
  const handleDeleteAll = () => {
    if (jobs.length === 0) return;
    setShowDeleteAllConfirm(true);
  };

  // Perform delete all projects after user confirmation
  const confirmDeleteAllProjects = async () => {
    setIsDeleting(true);
    try {
      const res = await fetch(`${API_BASE}/api/jobs`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      setJobs([]);
      setJustFinishedId(null);
      setReviseTarget(null);
      setThumbStudioJobId(null);
      setDismissedFailedJobIds([]);
      setShowDeleteAllConfirm(false);
      fetchJobs();
    } catch (e: any) {
      console.error("Delete all failed", e);
      toast.error("Could not delete all projects", String(e.message || e));
    } finally {
      setIsDeleting(false);
    }
  };


  // Hides the banner only; the failed project stays in Projects so it can be regenerated
  const handleDismissFailed = (jobId: string) => {
    setDismissedFailedJobIds(prev => [...prev, jobId]);
  };

  // Resumes a failed or canceled project from where it left off
  const handleResumeFailed = async (jobId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/jobs/${jobId}/retry`, { method: "POST" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      setDismissedFailedJobIds(prev => prev.filter(id => id !== jobId));
      fetchJobs();
    } catch (e: any) {
      console.error("Resume failed", e);
      toast.error("Could not resume project", e.message);
    }
  };

  const downloadUrl = (jobId: string, kind: "video" | "thumbnail" | "subtitles") => `${API_BASE}/api/jobs/${jobId}/download/${kind}`;

  const RUNNING_STATUSES: Job['status'][] = ['SCRIPTING', 'VOICEOVER', 'GENERATING_IMAGES', 'ANIMATING_VIDEO', 'COMPOSING'];
  const runningJobs = jobs.filter(j => RUNNING_STATUSES.includes(j.status));
  const activeJob = runningJobs[0] || null;
  const queuedJobs = jobs.filter(j => j.status === 'QUEUED');
  const completedJobs = jobs.filter(j => j.status === 'DONE');
  const latestFailedJob = jobs.find(j => j.status === 'FAILED' && !dismissedFailedJobIds.includes(j.id));
  const justFinishedJob = jobs.find(j => j.id === justFinishedId && j.status === 'DONE') || null;
  const thumbStudioJob = jobs.find(j => j.id === thumbStudioJobId) || null;
  const reviseJob = reviseTarget ? jobs.find(j => j.id === reviseTarget.id) || null : null;
  const hasSceneImages = (job: Job) => !!job.scenes?.some(sc => sc.image_url);

  const getStatusBadge = (status: Job['status']) => {
    switch (status) {
      case 'QUEUED':
        return <span style={{ background: 'rgb(245 158 11 / calc(0.15 * var(--tint)))', color: 'var(--a-amber)', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, border: '1px solid rgb(245 158 11 / calc(0.3 * var(--tint)))' }}>Waiting in Queue</span>;
      case 'SCRIPTING':
        return <span style={{ background: 'rgb(56 189 248 / calc(0.18 * var(--tint)))', color: 'var(--a-sky)', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, border: '1px solid rgb(56 189 248 / calc(0.35 * var(--tint)))' }}>Scripting (AI)</span>;
      case 'VOICEOVER':
        return <span style={{ background: 'rgb(168 85 247 / calc(0.18 * var(--tint)))', color: 'var(--a-purple)', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, border: '1px solid rgb(168 85 247 / calc(0.35 * var(--tint)))' }}>Voiceover</span>;
      case 'GENERATING_IMAGES':
        return <span style={{ background: 'rgb(6 182 212 / calc(0.18 * var(--tint)))', color: 'var(--a-cyan)', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, border: '1px solid rgb(6 182 212 / calc(0.35 * var(--tint)))' }}>Rendering Visuals</span>;
      case 'ANIMATING_VIDEO':
        return <span style={{ background: 'rgb(59 130 246 / calc(0.18 * var(--tint)))', color: 'var(--a-blue)', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, border: '1px solid rgb(59 130 246 / calc(0.35 * var(--tint)))' }}>Animating Motion</span>;
      case 'COMPOSING':
        return <span style={{ background: 'rgb(99 102 241 / calc(0.18 * var(--tint)))', color: 'var(--a-indigo)', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, border: '1px solid rgb(99 102 241 / calc(0.35 * var(--tint)))' }}>Mastering Video</span>;
      case 'DONE':
        return <span style={{ background: 'rgb(16 185 129 / calc(0.18 * var(--tint)))', color: 'var(--a-green)', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, border: '1px solid rgb(16 185 129 / calc(0.3 * var(--tint)))' }}>Completed</span>;
      case 'FAILED':
        return <span style={{ background: 'rgb(239 68 68 / calc(0.18 * var(--tint)))', color: 'var(--a-red)', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, border: '1px solid rgb(239 68 68 / calc(0.3 * var(--tint)))' }}>Failed</span>;
      default:
        return <span style={{ background: 'rgb(59 130 246 / calc(0.18 * var(--tint)))', color: 'var(--a-blue)', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600, border: '1px solid rgb(59 130 246 / calc(0.35 * var(--tint)))' }}>Processing...</span>;
    }
  };

  return (
    <div className="studio-container">
      
      {/* Premium Glassmorphic Sticky Top Navbar (Single Slim Row) */}
      <header className="studio-header">
        {/* Brand (left) */}
        <a href="/" className="studio-brand" title="Go to home page" aria-label="VidForge AI Studio home">
          <span className="brand-logo-badge">
            <Film size={16} color="#ffffff" />
          </span>
          <h1 className="brand-title">
            VidForge <span className="brand-title-accent">AI Studio</span>
          </h1>
          <span className="brand-badge">PRO v1.0</span>
        </a>

        {/* Right: queue status (only while there is work) + theme toggle in one box */}
        <div className="header-tools">
          {(activeJob || queuedJobs.length > 0) && (
            <button
              type="button"
              className={`header-queue ${activeJob ? 'busy' : ''}`}
              onClick={() => switchTab('production')}
              title="Open the production queue"
            >
              <span className="header-queue-dot" />
              {activeJob ? (
                <>
                  <span className="header-queue-title">Rendering “{activeJob.title}”</span>
                  <span className="header-queue-bar"><span style={{ width: `${activeJob.progress}%` }} /></span>
                  <strong>{activeJob.progress}%</strong>
                </>
              ) : (
                <span>Starting next job…</span>
              )}
              {queuedJobs.length > 0 && <span className="header-queue-meta">· {queuedJobs.length} queued</span>}
            </button>
          )}
          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            title={theme === "dark" ? "Light mode" : "Dark mode"}
          >
            {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
          </button>
        </div>
      </header>

      {/* Floating Vertical Navigation Dock (Left Side) */}
      <nav className="floating-tabs-dock" aria-label="Studio Navigation">
        {([
          { id: 'production', label: 'Video Production', meta: null, Icon: Film },
          { id: 'chat', label: 'Ollama AI Chat', meta: 'ChatGPT mode', Icon: MessageSquare },
          { id: 'ollama', label: 'Story & Script Studio', meta: 'Director Lab', Icon: Wand2 },
          { id: 'voices', label: 'Voice Artists', meta: 'F5 & Eleven', Icon: Volume2 },
          { id: 'gallery', label: 'Projects', meta: `${jobs.length} saved · ${completedJobs.length} ready`, Icon: FolderOpen },
          { id: 'models', label: 'AI Models & Hardware', meta: 'Downloads, sizes, requirements', Icon: Boxes },
          { id: 'workflow', label: 'About & How It Works', meta: 'Author, about VidForge, pipeline', Icon: Workflow },
        ] as const).map(({ id, label, meta, Icon }, i) => (
          <Fragment key={id}>
            {(i === 4 || i === 5) && <span className="floating-dock-divider" aria-hidden="true" />}
            <button
              type="button"
              className={`floating-tab-btn ${activeTab === id ? 'active' : ''}`}
              onClick={() => switchTab(id)}
              aria-label={label}
              aria-current={activeTab === id ? 'page' : undefined}
            >
              <Icon size={19} strokeWidth={activeTab === id ? 2.2 : 1.8} />
              {id === 'gallery' && jobs.length > 0 && (
                <span className="floating-count-badge">{jobs.length}</span>
              )}
              <span className="floating-tab-tooltip" role="tooltip">
                <span className="tooltip-title">{label}</span>
                {meta && <span className="tooltip-sub">{meta}</span>}
              </span>
            </button>
          </Fragment>
        ))}
      </nav>

      {/* Main Tab Viewport - Zero-blink persistent panels */}
      <main className="tab-viewport">
        
        {/* ========================================================================= */}
        {/* TAB 1: PRODUCTION STUDIO                                                  */}
        {/* ========================================================================= */}
        <div className={`tab-pane ${activeTab === 'production' ? 'active' : ''}`}>
          <div className="production-layout">
            
            {/* Creator Form */}
            <section className="glass-panel" style={{ padding: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Sparkles size={18} color="var(--a-blue)" />
                  <h2 style={{ fontSize: 17, fontWeight: 700, margin: 0 }}>Fast Video Production</h2>
                </div>
                <button
                  type="button"
                  onClick={() => switchTab("ollama")}
                  style={{ background: 'rgb(37 99 235 / calc(0.15 * var(--tint)))', color: 'var(--a-blue)', border: '1px solid rgb(59 130 246 / calc(0.35 * var(--tint)))', padding: '5px 10px', borderRadius: 8, fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 5 }}
                >
                  <Wand2 size={13} /> Write in Ollama Lab
                </button>
              </div>

              {/* Video Format / Production Type Selector */}
              <div style={{ marginBottom: 18 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--t-body)', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                  <Film size={14} color="var(--a-blue)" /> ভিডিওর ধরণ ও উদ্দেশ্য (Production Type):
                </label>
                <div className="type-grid">
                  {VIDEO_TYPES.map(({ id, label, desc, Icon, music }) => (
                    <button
                      key={id}
                      type="button"
                      className={`type-tile ${videoType === id ? 'active' : ''}`}
                      aria-pressed={videoType === id}
                      onClick={() => { setVideoType(id); setMusicTheme(music); }}
                    >
                      <span className="type-tile-icon"><Icon size={16} /></span>
                      <span className="type-tile-text">
                        <span className="type-tile-label">{label}</span>
                        <span className="type-tile-desc">{desc}</span>
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Target Video Duration System */}
              {(() => {
                const DURATION_MIN = 15;
                const DURATION_MAX = 360;
                const sceneCount = Math.max(3, Math.min(36, Math.round(targetDuration / 5.2)));
                const wordCount = Math.round(Math.max(10, targetDuration - sceneCount * 0.6) * 2.0);
                const fill = ((targetDuration - DURATION_MIN) / (DURATION_MAX - DURATION_MIN)) * 100;
                const mins = Math.floor(targetDuration / 60);
                const secs = targetDuration % 60;
                return (
                  <div className="duration-card">
                    <div className="duration-head">
                      <label htmlFor="duration-range" style={{ fontSize: 12, fontWeight: 700, color: 'var(--t-body)', display: 'flex', alignItems: 'center', gap: 6, margin: 0 }}>
                        <Clock size={14} color="var(--a-blue)" /> টার্গেট সময় ও দৈর্ঘ্য (Estimated Duration):
                      </label>
                      <div className="duration-value">
                        {mins > 0 && <><strong>{mins}</strong><span>মি.</span></>}
                        {(secs > 0 || mins === 0) && <><strong>{secs}</strong><span>সে.</span></>}
                      </div>
                    </div>

                    <input
                      id="duration-range"
                      type="range"
                      className="duration-range"
                      min={DURATION_MIN}
                      max={DURATION_MAX}
                      step={15}
                      value={targetDuration}
                      onChange={e => setTargetDuration(Number(e.target.value))}
                      style={{ '--fill': `${fill}%` } as React.CSSProperties}
                    />

                    <div className="duration-presets">
                      {[
                        { sec: 30, label: '30s', desc: 'Teaser' },
                        { sec: 60, label: '1m', desc: 'Short' },
                        { sec: 120, label: '2m', desc: 'Standard' },
                        { sec: 180, label: '3m', desc: 'In-Depth' },
                        { sec: 300, label: '5m', desc: 'Full' },
                      ].map(p => (
                        <button
                          key={p.sec}
                          type="button"
                          className={`duration-preset ${targetDuration === p.sec ? 'active' : ''}`}
                          aria-pressed={targetDuration === p.sec}
                          onClick={() => setTargetDuration(p.sec)}
                        >
                          <strong>{p.label} <LoadDot level={optionLoad.duration(p.sec)} /></strong>
                          <span>{p.desc}</span>
                        </button>
                      ))}
                    </div>

                    <div className="duration-stats">
                      <div><span>দৃশ্য</span><strong>{sceneCount} টি</strong></div>
                      <div><span>স্ক্রিপ্ট</span><strong>~{wordCount} শব্দ</strong></div>
                      <div><span>রেঞ্জ</span><strong>{Math.max(10, targetDuration - 10)}–{targetDuration + 10}s</strong></div>
                    </div>
                  </div>
                );
              })()}

              {/* Visual Quality & Motion Mode */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--t-body)', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 7 }}>
                  <Sparkles size={14} color="#a855f7" /> ভিজ্যুয়াল কোয়ালিটি ও মোশন (Motion Engine):
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 7 }}>
                  <div
                    onClick={() => setMotionMode('kenburns')}
                    style={{
                      padding: '8px 10px',
                      borderRadius: 10,
                      background: motionMode === 'kenburns' ? 'rgb(168 85 247 / calc(0.18 * var(--tint)))' : 'var(--surface)',
                      border: '1px solid var(--line)', outline: motionMode === 'kenburns' ? '2px solid #a855f7' : 'none', outlineOffset: -2,
                      cursor: 'pointer',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 3 }}>
                      <span style={{ fontSize: 13 }}>🌟</span>
                      <strong style={{ fontSize: 11.5, color: motionMode === 'kenburns' ? 'var(--a-purple)' : 'var(--t-strong)' }}>Ultra HD Ken Burns</strong>
                      <LoadDot level={optionLoad.motion('kenburns')} />
                      <span style={{ fontSize: 9, background: 'rgb(34 197 94 / calc(0.2 * var(--tint)))', color: 'var(--a-green-bright)', padding: '1px 4px', borderRadius: 4, fontWeight: 700 }}>প্রস্তাবিত</span>
                    </div>
                    <div style={{ fontSize: 9.5, color: 'var(--t-muted)', lineHeight: 1.3 }}>
                      স্পষ্ট 8K ছবি + সিনেম্যাটিক জুম-ইন, জুম-আউট ও ফেড ইফেক্ট (ছবি ভাঙার কোনো ঝুঁকি নেই)।
                    </div>
                  </div>

                  <div
                    onClick={() => wanAvailable && setMotionMode('wan')}
                    title={wanAvailable ? undefined : `Wan 2.1 is not supported on this platform (${systemStatus.platform})`}
                    style={{
                      padding: '8px 10px',
                      borderRadius: 10,
                      background: motionMode === 'wan' ? 'rgb(59 130 246 / calc(0.18 * var(--tint)))' : 'var(--surface)',
                      border: '1px solid var(--line)', outline: motionMode === 'wan' ? '2px solid #3b82f6' : 'none', outlineOffset: -2,
                      cursor: wanAvailable ? 'pointer' : 'not-allowed',
                      opacity: wanAvailable ? 1 : 0.45,
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 3 }}>
                      <span style={{ fontSize: 13 }}>🤖</span>
                      <strong style={{ fontSize: 11.5, color: motionMode === 'wan' ? 'var(--a-blue)' : 'var(--t-strong)' }}>Wan 2.1 AI Motion</strong>
                      <LoadDot level={optionLoad.motion('wan')} />
                      <span style={{ fontSize: 9, background: 'rgb(234 179 8 / calc(0.2 * var(--tint)))', color: 'var(--a-yellow)', padding: '1px 4px', borderRadius: 4, fontWeight: 700 }}>পরীক্ষামূলক</span>
                    </div>
                    <div style={{ fontSize: 9.5, color: 'var(--t-muted)', lineHeight: 1.3 }}>
                      {wanAvailable
                        ? 'ComfyUI I2V নিউরাল ভিডিও এনিমেশন। ক্যারেক্টার নড়াচড়া তৈরি করে।'
                        : 'এই প্ল্যাটফর্মে সমর্থিত নয় (Not supported on this platform)।'}
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
                    background: showInspirations ? 'rgb(37 99 235 / calc(0.16 * var(--tint)))' : 'var(--surface)',
                    border: '1px solid',
                    borderColor: showInspirations ? 'rgb(59 130 246 / calc(0.4 * var(--tint)))' : 'var(--line)',
                    color: showInspirations ? 'var(--a-blue)' : 'var(--t-body)',
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
                  <span style={{ fontSize: 11, color: 'var(--t-muted)' }}>
                    {showInspirations ? '▲ Hide' : '▼ Show Ideas'}
                  </span>
                </button>

                {showInspirations && (
                  <div className="inspiration-list">
                    {(FORMAT_INSPIRATIONS[videoType] || FORMAT_INSPIRATIONS.story).map((qs, i) => (
                      <button
                        key={i}
                        type="button"
                        className={`inspiration-item ${storyPrompt === qs.prompt ? 'active' : ''}`}
                        onClick={() => {
                          setStoryPrompt(qs.prompt);
                          setTitle(qs.title);
                          setLanguage(qs.lang);
                          if (qs.duration) setTargetDuration(qs.duration);
                        }}
                      >
                        <strong>{qs.title}</strong>
                        <span>
                          {qs.lang === 'bn' ? 'বাংলা' : qs.lang === 'hi' ? 'हिन्दी' : 'English'}
                          {qs.duration ? ` · ${qs.duration >= 60 ? `${Math.round(qs.duration / 6) / 10} min` : `${qs.duration}s`}` : ''}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <form onSubmit={handleProductionSubmit}>
                {/* Optional Custom Title */}
                <div style={{ marginBottom: 14 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--t-body)', display: 'block', marginBottom: 5 }}>
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
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--t-body)', display: 'block', marginBottom: 5 }}>
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
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--t-body)', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 7 }}>
                    <Languages size={14} color="var(--a-blue)" /> ভাষার নির্বাচন (Narrator Language):
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
                    {[
                      { id: 'bn', label: '🇧🇩 বাংলা' },
                      { id: 'hi', label: '🇮🇳 हिन्दी' },
                      { id: 'en', label: '🇬🇧 English' }
                    ].map(item => (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => setLanguage(item.id)}
                        style={{
                          padding: '8px 6px',
                          borderRadius: 8,
                          background: language === item.id ? 'rgb(37 99 235 / calc(0.2 * var(--tint)))' : 'var(--surface)',
                          border: '1px solid var(--line)', outline: language === item.id ? '2px solid #3b82f6' : 'none', outlineOffset: -2,
                          color: language === item.id ? 'var(--a-blue)' : 'var(--t-muted)',
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
                  <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--t-body)', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                    <Volume2 size={14} color="var(--a-sky)" /> ভয়েস ইঞ্জিন ও আর্টিস্ট (TTS Engine & Voice):
                  </label>

                  {/* Engine Switcher */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 12 }}>
                    {ENGINE_OPTIONS.map(opt => (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => setTtsEngine(opt.id)}
                        style={{
                          padding: '9px 10px',
                          borderRadius: 9,
                          background: ttsEngine === opt.id ? 'rgb(37 99 235 / calc(0.22 * var(--tint)))' : 'var(--surface)',
                          border: '1px solid var(--line)', outline: ttsEngine === opt.id ? `2px solid ${opt.accent}` : 'none', outlineOffset: -2,
                          color: ttsEngine === opt.id ? opt.accent : 'var(--t-muted)',
                          textAlign: 'center',
                          cursor: 'pointer',
                          fontSize: 12,
                          fontWeight: 700
                        }}
                      >
                        <div>{opt.label} <LoadDot level={optionLoad.voice(opt.id)} /></div>
                        <div style={{ fontSize: 10, opacity: 'var(--sub-label-opacity)', fontWeight: 500, marginTop: 2 }}>{opt.sub}</div>
                      </button>
                    ))}
                  </div>

                  {/* Engine 1: Gemini TTS */}
                  {ttsEngine === "gemini" && (
                    <div style={{ background: 'rgb(168 85 247 / calc(0.08 * var(--tint)))', border: '1px solid rgb(168 85 247 / calc(0.28 * var(--tint)))', padding: '12px 14px', borderRadius: 10 }}>
                      {!hasGeminiKey && renderKeyWarning("gemini")}
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                        <span style={{ fontSize: 11, color: 'var(--a-violet)', fontWeight: 600 }}>Gemini স্টুডিও ভয়েস ({engines.gemini?.model || 'gemini-3.8-flash-tts'}):</span>
                        {renderPreviewButton(geminiVoice, "gemini", 'var(--a-purple)')}
                      </div>
                      <select
                        value={geminiVoice}
                        onChange={e => setGeminiVoice(e.target.value)}
                        style={{ width: '100%', padding: '9px 12px', fontSize: 13 }}
                      >
                        {geminiVoiceEntries.map(([id, gv]) => (
                          <option key={id} value={id}>{gv.name} — {gv.description}</option>
                        ))}
                      </select>
                      <div style={{ fontSize: 10.5, color: 'var(--t-muted)', marginTop: 6, lineHeight: 1.4 }}>
                        প্রতিটি দৃশ্যের আবেগ অনুযায়ী ফিসফিস, বিরতি ও কণ্ঠের ওঠানামা স্বয়ংক্রিয়ভাবে প্রয়োগ হয়।
                      </div>
                    </div>
                  )}

                  {/* Engine 2: ElevenLabs */}
                  {ttsEngine === "elevenlabs" && (
                    <div style={{ background: 'rgb(37 99 235 / calc(0.08 * var(--tint)))', border: '1px solid rgb(59 130 246 / calc(0.25 * var(--tint)))', padding: '12px 14px', borderRadius: 10 }}>
                      {!hasElevenLabsKey && renderKeyWarning("elevenlabs")}
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                        <span style={{ fontSize: 11, color: 'var(--t-muted)', fontWeight: 600 }}>ElevenLabs স্টুডিও ভয়েস ({engines.elevenlabs?.model || 'eleven_v4'}):</span>
                        {elevenVoice !== 'custom' && renderPreviewButton(elevenVoice, "elevenlabs", 'var(--a-blue)')}
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

                  {/* Engine 3: F5-TTS local cloning */}
                  {ttsEngine === "f5tts" && (
                    <div style={{ background: 'rgb(56 189 248 / calc(0.08 * var(--tint)))', border: '1px solid rgb(56 189 248 / calc(0.28 * var(--tint)))', padding: '12px 14px', borderRadius: 10 }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                        <span style={{ fontSize: 11, color: 'var(--a-sky)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 5 }}>
                          <Zap size={13} /> Local Voice (offline)
                        </span>
                        {renderPreviewButton(f5Voice, "f5tts", 'var(--a-sky)')}
                      </div>
                      {Object.keys(localTtsModels).length > 0 && (
                        <label className="local-model-picker">
                          <span>Voice model</span>
                          <select value={localTtsModel} onChange={e => chooseLocalTtsModel(e.target.value)}>
                            {Object.entries(localTtsModels).map(([id, m]) => (
                              <option key={id} value={id}>{m.label} — {m.languages}</option>
                            ))}
                          </select>
                          {localTtsModels[localTtsModel] && (
                            <small>
                              {localTtsModels[localTtsModel].clone ? 'Clones the reference voice below' : 'One built-in voice (no cloning)'} · Licence: {localTtsModels[localTtsModel].licence}
                            </small>
                          )}
                        </label>
                      )}
                      {localTtsModels[localTtsModel]?.clone === false ? (
                        <div style={{ fontSize: 12, color: 'var(--t-muted)', padding: '6px 2px' }}>
                          {localTtsModels[localTtsModel].label} speaks with its own built-in voice, so no reference recording is needed.
                        </div>
                      ) : (
                        <select
                          value={f5Voice}
                          onChange={e => setF5Voice(e.target.value)}
                          style={{ width: '100%', padding: '9px 12px', fontSize: 13 }}
                        >
                          {f5Voices.map(fv => (
                            <option key={fv.id} value={fv.id}>{fv.custom ? '🎤 ' : ''}{fv.name}</option>
                          ))}
                        </select>
                      )}
                      <button
                        type="button"
                        onClick={() => { setVoiceShowcaseEngineFilter('f5tts'); switchTab('voices'); }}
                        style={{ marginTop: 8, width: '100%', background: 'rgb(56 189 248 / calc(0.12 * var(--tint)))', color: 'var(--a-sky)', border: '1px dashed rgb(56 189 248 / calc(0.45 * var(--tint)))', padding: '7px 10px', borderRadius: 8, fontSize: 12, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
                      >
                        <Mic size={13} /> নিজের কণ্ঠ যোগ করুন (Add my voice)
                      </button>
                    </div>
                  )}
                </div>

                {/* Aspect Ratio */}
                <div style={{ marginBottom: 22 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--t-body)', display: 'block', marginBottom: 7 }}>
                    ভিডিও রেজোলিউশন ও ফ্রেম ফরম্যাট:
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <button
                      type="button"
                      onClick={() => setAspectRatio("9:16")}
                      style={{
                        padding: '10px 12px',
                        borderRadius: 10,
                        background: aspectRatio === "9:16" ? 'rgb(37 99 235 / calc(0.2 * var(--tint)))' : 'var(--surface)',
                        border: '1px solid var(--line)', outline: aspectRatio === "9:16" ? '2px solid #3b82f6' : 'none', outlineOffset: -2,
                        color: aspectRatio === "9:16" ? 'var(--a-blue)' : 'var(--t-muted)',
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
                        <div style={{ fontSize: 10, opacity: 'var(--sub-label-opacity)' }}>Shorts / Reels</div>
                      </div>
                    </button>

                    <button
                      type="button"
                      onClick={() => setAspectRatio("16:9")}
                      style={{
                        padding: '10px 12px',
                        borderRadius: 10,
                        background: aspectRatio === "16:9" ? 'rgb(37 99 235 / calc(0.2 * var(--tint)))' : 'var(--surface)',
                        border: '1px solid var(--line)', outline: aspectRatio === "16:9" ? '2px solid #3b82f6' : 'none', outlineOffset: -2,
                        color: aspectRatio === "16:9" ? 'var(--a-blue)' : 'var(--t-muted)',
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
                        <div style={{ fontSize: 10, opacity: 'var(--sub-label-opacity)' }}>YouTube Standard</div>
                      </div>
                    </button>
                  </div>
                </div>

                {/* Output resolution & frame rate */}
                <div className="render-options">
                  <div>
                    <div className="render-options-label">ভিডিও রেজোলিউশন (Resolution)</div>
                    <div className="segmented" role="radiogroup" aria-label="Video resolution">
                      {([480, 720, 1080, 1440] as const).map(r => (
                        <button
                          key={r}
                          type="button"
                          role="radio"
                          aria-checked={resolution === r}
                          className={`segmented-btn ${resolution === r ? 'active' : ''}`}
                          onClick={() => setResolution(r)}
                        >
                          {r}p <LoadDot level={optionLoad.resolution(r)} />
                        </button>
                      ))}
                    </div>
                    <div className="render-options-hint">
                      {(() => {
                        const long = Math.round(resolution * 16 / 9 / 2) * 2;
                        const [w, h] = aspectRatio === '9:16' ? [resolution, long] : [long, resolution];
                        return `${w}×${h}${resolution === 1440 ? ' · slower render, larger file' : resolution === 480 ? ' · fastest, smallest file' : ''}`;
                      })()}
                    </div>
                  </div>
                  <div>
                    <div className="render-options-label">ফ্রেম রেট (FPS)</div>
                    <div className="segmented" role="radiogroup" aria-label="Frame rate">
                      {([24, 25, 30, 60] as const).map(f => (
                        <button
                          key={f}
                          type="button"
                          role="radio"
                          aria-checked={fps === f}
                          className={`segmented-btn ${fps === f ? 'active' : ''}`}
                          onClick={() => setFps(f)}
                        >
                          {f} <LoadDot level={optionLoad.fps(f)} />
                        </button>
                      ))}
                    </div>
                    <div className="render-options-hint">
                      {fps === 24 ? 'Cinematic film look' : fps === 25 ? 'PAL broadcast standard' : fps === 30 ? 'Standard for YouTube & social' : 'Smoothest motion · twice the frames to render'}
                    </div>
                  </div>
                </div>

                {/* Optional background music */}
                <BackgroundMusicPicker
                  apiBase={API_BASE}
                  tracks={musicTracks}
                  loadFailed={musicLoadFailed}
                  onRetry={fetchMusicTracks}
                  value={musicSettings}
                  onChange={setMusicSettings}
                />
                
                {/* Subtitles / Captions Toggle */}
                <div className="form-option">
                  <div className="music-head">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                      <span className="form-option-icon"><Subtitles size={16} /></span>
                      <div style={{ minWidth: 0 }}>
                        <div className="music-head-title">Subtitles & Captions (সাবটাইটেল)</div>
                        <div className="music-head-sub">
                          {enableSubtitles ? 'Burn synchronized captions onto the video' : 'Render clean video without on-screen captions'}
                        </div>
                      </div>
                    </div>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={enableSubtitles}
                      aria-label="Burn subtitles onto the video"
                      className={`switch ${enableSubtitles ? 'on' : ''}`}
                      onClick={() => setEnableSubtitles(!enableSubtitles)}
                    >
                      <span />
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
                    background: 'var(--primary)',
                    color: '#ffffff',
                    fontWeight: 700,
                    fontSize: 14,
                    boxShadow: '0 4px 18px var(--primary-glow)',
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
            <section className="production-side">

              {/* Live system-load estimate for the options chosen in the form */}
              <LoadMeter
                options={{ duration: targetDuration, motion: motionMode, resolution, fps, voice: ttsEngine, subtitles: enableSubtitles }}
                vramTotalGb={systemStatus.vram_total_gb}
              />

              {/* Video-ready prompt: next steps for the project that just finished */}
              {justFinishedJob && (
                <div className="glass-panel ready-banner">
                  <div className="ready-banner-head">
                    <PartyPopper size={18} color="var(--a-green)" />
                    <h4>Your video is ready: {justFinishedJob.title}</h4>
                    <button type="button" className="btn btn-icon btn-ghost" onClick={() => setJustFinishedId(null)} aria-label="Dismiss">
                      <X size={14} />
                    </button>
                  </div>
                  <p>It's saved in Projects. Design a thumbnail for it, or refine it if it isn't quite right.</p>
                  <div className="ready-banner-actions">
                    {hasSceneImages(justFinishedJob) && (
                      <button type="button" className="btn btn-primary" onClick={() => setThumbStudioJobId(justFinishedJob.id)}>
                        <ImageIcon size={14} /> Design thumbnail
                      </button>
                    )}
                    <button type="button" className="btn btn-ghost" onClick={() => setReviseTarget({ id: justFinishedJob.id, mode: "refine" })}>
                      <Wand2 size={14} /> Refine
                    </button>
                    <a className="btn btn-ghost" href={downloadUrl(justFinishedJob.id, "video")}>
                      <Download size={14} /> Download
                    </a>
                    <button
                      type="button"
                      className="btn btn-danger-ghost"
                      onClick={() => handleDelete(justFinishedJob)}
                      style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 5 }}
                      title="Delete this project"
                    >
                      <Trash2 size={14} /> Delete
                    </button>
                  </div>
                </div>
              )}

              {/* Failed Job Banner (if any) */}
              {latestFailedJob && (
                <div className="glass-panel" style={{ padding: 18, background: 'rgb(239 68 68 / calc(0.08 * var(--tint)))' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <AlertTriangle size={18} color="#ef4444" />
                      <h4 style={{ margin: 0, fontSize: 13.5, fontWeight: 700, color: 'var(--a-red)' }}>
                        Job Failed: {latestFailedJob.title}
                      </h4>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDismissFailed(latestFailedJob.id)}
                      style={{ background: 'rgb(239 68 68 / calc(0.2 * var(--tint)))', border: '1px solid rgb(239 68 68 / calc(0.4 * var(--tint)))', color: 'var(--a-pink)', padding: '2px 8px', borderRadius: 6, fontSize: 11, cursor: 'pointer' }}
                    >
                      Dismiss
                    </button>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--t-body)', lineHeight: 1.4, wordBreak: 'break-word', maxHeight: 90, overflowY: 'auto', background: 'var(--well)', padding: '6px 10px', borderRadius: 6 }}>
                    {latestFailedJob.error_message || 'An error occurred during video production.'}
                  </div>
                  <div style={{ display: 'flex', gap: 6, marginTop: 10, alignItems: 'center' }}>
                    <button type="button" className="btn btn-primary" onClick={() => handleResumeFailed(latestFailedJob.id)}>
                      <RefreshCw size={14} /> Resume Job
                    </button>
                    <button type="button" className="btn btn-ghost" onClick={() => setReviseTarget({ id: latestFailedJob.id, mode: "regenerate" })}>
                      <Wand2 size={14} /> Regenerate
                    </button>
                    <button
                      type="button"
                      className="btn btn-danger-ghost"
                      onClick={() => handleDelete(latestFailedJob)}
                      style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px', fontSize: 12 }}
                      title="Permanently delete this failed project"
                    >
                      <Trash2 size={13} /> Delete Project
                    </button>
                  </div>
                </div>
              )}

              {/* SECTION 1: RUNNING TASKS SPOTLIGHT */}
              {activeJob ? (
                <div className="glass-panel active-job-glow" style={{ padding: 22 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div className="pulse-dot" style={{ width: 10, height: 10, borderRadius: '50%', background: '#3b82f6', boxShadow: '0 0 10px #3b82f6' }} />
                      <div>
                        <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--a-blue)', fontWeight: 800 }}>
                          Currently Running Task
                        </div>
                        <h3 style={{ fontSize: 16, fontWeight: 700, margin: '2px 0 0 0', color: 'var(--t-strong)' }}>
                          {activeJob.title}
                        </h3>
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <button
                        type="button"
                        className="btn btn-danger-ghost"
                        onClick={() => handleDelete(activeJob)}
                        style={{ fontSize: 11, padding: '4px 10px', display: 'flex', alignItems: 'center', gap: 5 }}
                        title="Cancel this running project and delete its files"
                      >
                        <Trash2 size={13} /> Cancel & Delete
                      </button>
                      {getStatusBadge(activeJob.status)}
                    </div>
                  </div>

                  {/* Progress Bar & Current Step */}
                  <div style={{ marginBottom: 14 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--t-muted)', marginBottom: 6 }}>
                      <span style={{ color: 'var(--t-body)', fontWeight: 500 }}>{activeJob.current_step || 'Processing...'}</span>
                      <span style={{ fontWeight: 700, color: 'var(--a-blue)' }}>{activeJob.progress}%</span>
                    </div>
                    <div style={{ width: '100%', height: 8, background: 'var(--line)', borderRadius: 10, overflow: 'hidden' }}>
                      <div className="progress-bar-animated" style={{ width: `${activeJob.progress}%`, height: '100%', transition: 'width 0.4s ease' }} />
                    </div>
                  </div>

                  {/* Live Scenes Preview */}
                  {activeJob.scenes && activeJob.scenes.length > 0 && (
                    <div style={{ marginTop: 16, borderTop: '1px solid var(--line-soft)', paddingTop: 14 }}>
                      <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--t-muted)', display: 'block', marginBottom: 8 }}>
                        Planned Scenes ({activeJob.scenes.length} দৃশ্য):
                      </label>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: 10 }}>
                        {activeJob.scenes.map((sc, i) => (
                          <div key={i} style={{ background: 'var(--surface)', padding: 10, borderRadius: 8, border: '1px solid var(--line-soft)', fontSize: 12 }}>
                            <div style={{ fontWeight: 700, color: 'var(--a-blue)', marginBottom: 4 }}>Scene {sc.id}</div>
                            <p style={{ color: 'var(--t-body)', margin: 0, fontSize: 12, lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                              "{sc.narration}"
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Other Running Tasks if multiple */}
                  {runningJobs.length > 1 && (
                    <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--line-soft)' }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--t-muted)', marginBottom: 8 }}>
                        Other In-Progress Tasks ({runningJobs.length - 1}):
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        {runningJobs.slice(1).map(rj => (
                          <div key={rj.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--well)', padding: '6px 10px', borderRadius: 6, fontSize: 12 }}>
                            <span style={{ color: 'var(--t-body)' }}>{rj.title}</span>
                            <span style={{ color: 'var(--a-blue)', fontWeight: 600 }}>{rj.progress}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : queuedJobs.length > 0 ? (
                <div className="glass-panel" style={{ padding: 20, display: 'flex', alignItems: 'center', gap: 14, background: 'rgb(245 158 11 / calc(0.05 * var(--tint)))' }}>
                  <Clock size={24} color="#f59e0b" className="spin" />
                  <div>
                    <div style={{ fontWeight: 700, color: 'var(--t-strong)', fontSize: 14 }}>Preparing to Process Queue</div>
                    <div style={{ fontSize: 12, color: 'var(--t-body)', marginTop: 2 }}>
                      Worker is picking up the next queued task: <strong style={{ color: 'var(--a-orange)' }}>{queuedJobs[0].title}</strong>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="glass-panel" style={{ padding: 20 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                    <CheckCircle2 size={16} color="#3b82f6" />
                    <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: 'var(--t-strong)' }}>
                      Production Pipeline is Idle
                    </h3>
                  </div>
                  <div style={{ padding: 24, textAlign: 'center', color: 'var(--t-faint)', fontSize: 13, background: 'var(--well)', borderRadius: 8 }}>
                    Submit a story on the left, or use the <strong>Ollama Story Studio</strong> tab to write and fine-tune your script.
                  </div>
                </div>
              )}

              {/* SECTION 2: WAITING IN QUEUE LIST */}
              <div className="glass-panel" style={{ padding: 20 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Clock size={16} color="#f59e0b" />
                    <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0, color: 'var(--t-strong)' }}>
                      Waiting in Queue ({queuedJobs.length})
                    </h3>
                  </div>
                  {queuedJobs.length > 0 && (
                    <span style={{ fontSize: 11, color: 'var(--a-orange)', background: 'rgb(245 158 11 / calc(0.12 * var(--tint)))', padding: '2px 8px', borderRadius: 12, fontWeight: 600, border: '1px solid rgb(245 158 11 / calc(0.25 * var(--tint)))' }}>
                      FIFO Order
                    </span>
                  )}
                </div>

                {queuedJobs.length === 0 ? (
                  <div style={{ padding: 24, textAlign: 'center', color: 'var(--t-faint)', fontSize: 13, background: 'var(--well)', borderRadius: 8 }}>
                    No videos waiting in queue. Any new video you submit will begin immediately.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {queuedJobs.map((qj, idx) => (
                      <div key={qj.id} style={{ background: 'var(--surface)', padding: '12px 16px', borderRadius: 10, border: '1px solid var(--line-soft)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--a-orange)', background: 'rgb(245 158 11 / calc(0.15 * var(--tint)))', width: 28, height: 28, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgb(245 158 11 / calc(0.3 * var(--tint)))' }}>
                            #{idx + 1}
                          </span>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: 13.5, color: 'var(--t-strong)' }}>{qj.title}</div>
                            <div style={{ fontSize: 11, color: 'var(--t-muted)', display: 'flex', gap: 8, marginTop: 3 }}>
                              <span>Format: {qj.aspect_ratio}</span>
                              <span>•</span>
                              <span>Lang: {qj.language.toUpperCase()}</span>
                              <span>•</span>
                              <span>Target: ~{qj.target_duration}s</span>
                              <span>•</span>
                              <span style={{ textTransform: 'capitalize' }}>{qj.video_type}</span>
                            </div>
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <span style={{ background: 'rgb(245 158 11 / calc(0.15 * var(--tint)))', color: 'var(--a-amber)', padding: '4px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600, border: '1px solid rgb(245 158 11 / calc(0.3 * var(--tint)))' }}>
                            Waiting in Queue
                          </span>
                          <button 
                            type="button"
                            onClick={() => handleDelete(qj)}
                            title="Cancel & Remove from Queue"
                            style={{ background: 'rgb(239 68 68 / calc(0.12 * var(--tint)))', border: '1px solid rgb(239 68 68 / calc(0.25 * var(--tint)))', color: 'var(--a-red-strong)', padding: '5px 8px', borderRadius: 6, cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                          >
                            <Trash2 size={14} />
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
                      <CheckCircle2 size={16} color="var(--a-green)" />
                      <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Latest Completed Videos</h3>
                    </div>
                    <button
                      onClick={() => switchTab("gallery")}
                      style={{ background: 'none', color: 'var(--a-blue)', fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}
                    >
                      View All Projects <ArrowRight size={13} />
                    </button>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 14 }}>
                    {completedJobs.slice(0, 2).map(cj => (
                      <div key={cj.id} style={{ background: 'var(--surface)', borderRadius: 10, overflow: 'hidden', border: '1px solid var(--line-soft)' }}>
                        {cj.output_video && (
                          <video
                            src={`${API_BASE}${cj.output_video}`}
                            controls
                            style={{ width: '100%', maxHeight: 160, background: '#000', objectFit: 'contain' }}
                          />
                        )}
                        <div style={{ padding: 10 }}>
                          <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--t-strong)', marginBottom: 4 }}>{cj.title}</div>
                          <a
                            href={downloadUrl(cj.id, "video")}
                            style={{ color: 'var(--a-green)', fontSize: 11, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600 }}
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
              <div className="chat-title">
                <span className="section-icon"><MessageSquare size={17} /></span>
                <div style={{ minWidth: 0 }}>
                  <h3>Ollama AI Chat</h3>
                  <span>আপনার লোকাল LLM-এর সাথে বাংলায় বা ইংরেজিতে চ্যাট করুন</span>
                </div>
              </div>

              <div className="chat-controls">
                <label className="chat-select">
                  <span>Persona</span>
                  <select value={chatPersona} onChange={e => setChatPersona(e.target.value)}>
                    <option value="film_director">Film Director & Storyteller</option>
                    <option value="bangla_writer">বাংলা সাহিত্যিক ও ঐতিহাসিক</option>
                    <option value="screenwriter">Hollywood Screenwriter</option>
                    <option value="general">General AI Assistant</option>
                  </select>
                </label>

                <label className="chat-select">
                  <span>Model</span>
                  <select value={chatModel} onChange={e => setChatModel(e.target.value)}>
                    {systemStatus.models.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </label>

                <button
                  type="button"
                  className="btn btn-danger-ghost"
                  title="Clear this conversation"
                  onClick={() => {
                    if (confirm("Are you sure you want to clear this chat?")) {
                      setChatMessages([
                        {
                          id: `welcome_${Date.now()}`,
                          role: "assistant",
                          content: "নতুন কথোপকথন শুরু হলো! আপনি যেকোনো কাহিনী, ডায়ালগ বা পরামর্শ নিয়ে বলতে পারেন।",
                          timestamp: Date.now()
                        }
                      ]);
                    }
                  }}
                >
                  <Trash2 size={13} /> Clear
                </button>
              </div>
            </div>

            {/* Scrollable Messages Area */}
            <div className="chat-scroll-area">
              <div className="chat-thread">
                {chatMessages.map(msg => (
                  <div key={msg.id} className={`chat-msg-row ${msg.role}`}>
                    {msg.role === 'assistant' && (
                      <div className="chat-avatar assistant"><Bot size={16} /></div>
                    )}

                    <div className="chat-msg-body">
                      <div className={`chat-bubble ${msg.role}`}>{msg.content}</div>

                      {/* Actions for assistant messages */}
                      {msg.role === 'assistant' && msg.id !== 'welcome' && !msg.id.startsWith('welcome_') && (
                        <div className="chat-actions">
                          <button type="button" className="chat-action" onClick={() => copyMessage(msg.id, msg.content)}>
                            {copiedMsgId === msg.id ? <Check size={12} /> : <Copy size={12} />}
                            {copiedMsgId === msg.id ? 'Copied' : 'Copy'}
                          </button>
                          <button
                            type="button"
                            className="chat-action"
                            onClick={() => { setStoryPrompt(msg.content); switchTab("production"); }}
                          >
                            <Film size={12} /> Use in Video Production
                          </button>
                          <button
                            type="button"
                            className="chat-action"
                            onClick={() => { setStoryTopic(msg.content); switchTab("ollama"); }}
                          >
                            <Wand2 size={12} /> Convert to Storyboard
                          </button>
                        </div>
                      )}
                    </div>

                    {msg.role === 'user' && (
                      <div className="chat-avatar user"><User size={16} /></div>
                    )}
                  </div>
                ))}

                {/* Typing indicator */}
                {isChatLoading && (
                  <div className="chat-msg-row assistant">
                    <div className="chat-avatar assistant"><Bot size={16} /></div>
                    <div className="chat-bubble assistant chat-typing">
                      <span>{chatModel} উত্তর তৈরি করছে</span>
                      <div style={{ display: 'flex', gap: 3 }}>
                        <div className="typing-dot" />
                        <div className="typing-dot" />
                        <div className="typing-dot" />
                      </div>
                    </div>
                  </div>
                )}

                {/* Quick Starter Suggestions */}
                {chatMessages.length <= 2 && !isChatLoading && (
                  <div className="chat-suggestions">
                    {[
                      "পলাশীর যুদ্ধে মীর জাফরের বিশ্বাসঘাতকতার একটি নাটকীয় দৃশ্য লিখে দাও",
                      "কনস্টান্টিনোপল বিজয়ের দিনে সুলতান মুহাম্মদ ফাতিহের একটি রণহুংকার সংলাপ",
                      "তিতুমীরের বাঁশের কেল্লার বীরত্ব নিয়ে একটি সংক্ষিপ্ত আবেগঘন দৃশ্য রচনা করো",
                      "Write an intense dialogue between two commanders on the night before battle"
                    ].map((sugg, i) => (
                      <button key={i} type="button" className="chat-suggestion" onClick={() => handleSendChatMessage(sugg)}>
                        <Sparkles size={13} />
                        <span>{sugg}</span>
                      </button>
                    ))}
                  </div>
                )}

                <div ref={chatBottomRef} />
              </div>
            </div>

            {/* Composer */}
            <div className="chat-input-bar">
              <form
                className="chat-composer"
                onSubmit={e => {
                  e.preventDefault();
                  handleSendChatMessage();
                }}
              >
                <textarea
                  rows={1}
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendChatMessage();
                    }
                  }}
                  placeholder="এখানে লিখুন..."
                  aria-label="Message"
                />
                <button
                  type="submit"
                  className="chat-send"
                  disabled={isChatLoading || !chatInput.trim()}
                  aria-label="Send message"
                  title="Send"
                >
                  <Send size={16} />
                </button>
              </form>
              <div className="chat-hint">Enter পাঠাতে · Shift + Enter নতুন লাইন</div>
            </div>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* TAB 3: OLLAMA STORY STUDIO                                                */}
        {/* ========================================================================= */}
        <div className={`tab-pane ${activeTab === 'ollama' ? 'active' : ''}`}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            
            {/* Studio Hero Banner with Blue Glow */}
            <div className="glass-panel" style={{ padding: '22px 26px', background: 'rgb(37 99 235 / calc(0.1 * var(--tint)))' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  <div style={{ width: 44, height: 44, borderRadius: 12, background: 'rgb(37 99 235 / calc(0.25 * var(--tint)))', border: '1px solid rgb(59 130 246 / calc(0.45 * var(--tint)))', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Wand2 size={24} color="var(--a-blue)" />
                  </div>
                  <div>
                    <h2 style={{ fontSize: 20, fontWeight: 800, margin: '0 0 4px 0', color: 'var(--t-strong)' }}>
                      Ollama AI Story & Script Studio
                    </h2>
                    <p style={{ fontSize: 13, color: 'var(--t-muted)', margin: 0 }}>
                      আপনার লোকাল Ollama LLM মডেল ব্যবহার করে মুহূর্তেই যেকোনো ঐতিহাসিক বা কাল্পনিক ঘটনার দৃশ্যভিত্তিক সম্পূর্ণ চিত্রনাট্য তৈরি ও সম্পাদনা করুন।
                    </p>
                  </div>
                </div>

                {/* Model Selector */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--surface-strong)', padding: '6px 14px', borderRadius: 10, border: '1px solid rgb(59 130 246 / calc(0.3 * var(--tint)))' }}>
                  <Bot size={16} color="var(--a-blue)" />
                  <span style={{ fontSize: 12, color: 'var(--t-muted)', fontWeight: 600 }}>Ollama Model:</span>
                  <select
                    value={ollamaModel}
                    onChange={e => setOllamaModel(e.target.value)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--a-blue)', fontWeight: 700, fontSize: 13, cursor: 'pointer', outline: 'none' }}
                  >
                    {systemStatus.models.map(m => (
                      <option key={m} value={m} style={{ background: '#0f172a', color: 'var(--t-strong)' }}>{m}</option>
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
                  <label style={{ fontSize: 13, fontWeight: 700, color: 'var(--t-body)', display: 'block', marginBottom: 8 }}>
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
                    <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--t-faint)', display: 'block', marginBottom: 6 }}>জনপ্রিয় আইডিয়া (ক্লিক করে নির্বাচন করুন):</span>
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
                          style={{ background: 'var(--surface)', border: '1px solid var(--line)', padding: '5px 10px', borderRadius: 20, fontSize: 11, color: 'var(--t-body)' }}
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
                    <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--t-body)', display: 'block', marginBottom: 6 }}>
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
                    </select>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                    {/* Genre */}
                    <div>
                      <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--t-body)', display: 'block', marginBottom: 6 }}>
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
                      <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--t-body)', display: 'block', marginBottom: 6 }}>
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
                    <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--t-body)', display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <span>দৃশ্যের সংখ্যা (Scenes Count):</span>
                      <span style={{ color: 'var(--a-blue)', fontWeight: 700 }}>{storySceneCount} টি দৃশ্য (~{storySceneCount * 7} সেকেন্ড)</span>
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
                            background: storySceneCount === cnt ? 'rgb(37 99 235 / calc(0.25 * var(--tint)))' : 'var(--surface)',
                            border: '1px solid var(--line)', outline: storySceneCount === cnt ? '2px solid #3b82f6' : 'none', outlineOffset: -2,
                            color: storySceneCount === cnt ? 'var(--a-blue)' : 'var(--t-muted)',
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
                      background: 'var(--primary)',
                      color: '#ffffff',
                      fontWeight: 700,
                      fontSize: 14,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 8,
                      boxShadow: '0 4px 20px var(--primary-glow)'
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
                <div style={{ marginTop: 16, padding: '12px 16px', background: 'rgb(239 68 68 / calc(0.15 * var(--tint)))', border: '1px solid rgb(239 68 68 / calc(0.3 * var(--tint)))', borderRadius: 8, color: 'var(--a-pink)', display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
                  <AlertTriangle size={16} />
                  <span>{storyError}</span>
                </div>
              )}
            </div>

            {/* Generated Storyboard & Scene Editor */}
            {generatedScenes.length > 0 && (
              <div className="glass-panel" style={{ padding: 24 }}>
                
                {/* Header with Title & Synopsis */}
                <div style={{ borderBottom: '1px solid var(--line)', paddingBottom: 18, marginBottom: 20 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <BookOpen size={20} color="var(--a-blue)" />
                      <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--a-blue)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Ollama Generated Storyboard ({generatedScenes.length} Scenes)
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <button
                        type="button"
                        onClick={handleCopyScript}
                        style={{ background: 'var(--line-soft)', color: 'var(--t-body)', padding: '7px 12px', borderRadius: 8, fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}
                      >
                        {copySuccess ? <Check size={14} color="var(--a-green)" /> : <Copy size={14} />}
                        {copySuccess ? 'Copied Script!' : 'Copy Script'}
                      </button>
                      
                      <button
                        type="button"
                        onClick={() => setEnableSubtitles(!enableSubtitles)}
                        style={{
                          background: enableSubtitles ? 'rgba(79, 70, 229, 0.12)' : 'var(--line-soft)',
                          border: `1px solid ${enableSubtitles ? 'var(--primary)' : 'var(--line)'}`,
                          color: enableSubtitles ? 'var(--primary)' : 'var(--t-muted)',
                          padding: '7px 12px',
                          borderRadius: 8,
                          fontSize: 12,
                          fontWeight: 600,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6,
                          cursor: 'pointer',
                          transition: 'all 0.15s ease'
                        }}
                        title={enableSubtitles ? "Subtitles will be burned into video" : "No subtitles will be burned"}
                      >
                        <Subtitles size={14} />
                        <span>Subtitles: {enableSubtitles ? 'ON' : 'OFF'}</span>
                      </button>

                      <button
                        type="button"
                        onClick={handleSendStoryToProduction}
                        disabled={isSubmitting}
                        style={{
                          background: 'var(--primary)',
                          color: '#fff',
                          padding: '8px 16px',
                          borderRadius: 8,
                          fontSize: 13,
                          fontWeight: 700,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 7,
                          boxShadow: '0 4px 18px var(--primary-glow)'
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
                    style={{ width: '100%', fontSize: 20, fontWeight: 800, padding: '8px 12px', marginBottom: 8, background: 'var(--surface-soft)' }}
                  />

                  {/* Editable Synopsis */}
                  <textarea
                    rows={2}
                    value={generatedSynopsis}
                    onChange={e => setGeneratedSynopsis(e.target.value)}
                    placeholder="Story synopsis / summary..."
                    style={{ width: '100%', fontSize: 13, padding: '8px 12px', background: 'var(--surface-soft)', color: 'var(--t-muted)' }}
                  />
                </div>

                {/* Scene Cards List */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {generatedScenes.map((scene, idx) => (
                    <div key={idx} className="scene-card">
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12, borderBottom: '1px solid var(--line-soft)', paddingBottom: 8 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', minWidth: 0 }}>
                          <span style={{ background: '#2563eb', color: '#ffffff', fontWeight: 800, fontSize: 12, padding: '2px 8px', borderRadius: 6 }}>
                            Scene {idx + 1}
                          </span>
                          {(scene.characters || []).map(name => (
                            <span key={name} className="chip chip-primary" title={scene.cast?.find(c => c.name === name)?.look}>
                              <User size={11} /> {name}
                            </span>
                          ))}
                          {scene.location && <span className="chip">{scene.location}</span>}
                          <label className="chip" title="Background music level for this scene">
                            <Music size={11} />
                            <select
                              className="scene-music-select"
                              value={scene.music_level || 'medium'}
                              onChange={e => {
                                const updated = [...generatedScenes];
                                updated[idx] = { ...updated[idx], music_level: e.target.value as Scene["music_level"] };
                                setGeneratedScenes(updated);
                              }}
                            >
                              <option value="low">Music low</option>
                              <option value="medium">Music medium</option>
                              <option value="high">Music high</option>
                            </select>
                          </label>
                        </div>

                        <button
                          type="button"
                          onClick={() => {
                            const updated = generatedScenes.filter((_, i) => i !== idx);
                            setGeneratedScenes(updated);
                          }}
                          style={{ background: 'none', color: 'var(--a-red-strong)', padding: 4 }}
                          title="Delete Scene"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>

                      {scene.continuity && idx > 0 && (
                        <p className="scene-continuity"><ArrowRight size={12} /> {scene.continuity}</p>
                      )}

                      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 14 }}>
                        {/* Narration voiceover text */}
                        <div>
                          <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--a-blue)', display: 'flex', alignItems: 'center', gap: 5, marginBottom: 5 }}>
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
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 92px', gap: 8, marginTop: 6 }}>
                            <div>
                              <label style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--a-purple)', display: 'block', marginBottom: 3 }}>
                                🎭 Delivery (কীভাবে বলবে):
                              </label>
                              <input
                                type="text"
                                value={scene.delivery || ""}
                                placeholder="e.g. hushed, slow, suspenseful"
                                onChange={e => {
                                  const updated = [...generatedScenes];
                                  updated[idx].delivery = e.target.value;
                                  setGeneratedScenes(updated);
                                }}
                                style={{ width: '100%', padding: '6px 10px', fontSize: 12 }}
                              />
                            </div>
                            <div>
                              <label style={{ fontSize: 10.5, fontWeight: 700, color: 'var(--a-purple)', display: 'block', marginBottom: 3 }}>
                                ⏸ Pause (s):
                              </label>
                              <input
                                type="number"
                                min={0.2}
                                max={2}
                                step={0.1}
                                value={scene.pause_after ?? 0.6}
                                onChange={e => {
                                  const updated = [...generatedScenes];
                                  updated[idx].pause_after = Number(e.target.value);
                                  setGeneratedScenes(updated);
                                }}
                                style={{ width: '100%', padding: '6px 8px', fontSize: 12 }}
                              />
                            </div>
                          </div>
                          <div style={{ fontSize: 10, color: 'var(--t-faint)', marginTop: 4 }}>
                            Cues: [whispers] [softly] [excited] [sad] [sighs] [laughs] [gasps] [short pause] [long pause]
                          </div>
                        </div>

                        {/* Visual & Motion Prompts */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          <div>
                            <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--a-sky)', display: 'block', marginBottom: 4 }}>
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
                            <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--a-green)', display: 'block', marginBottom: 4 }}>
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
                        motion_prompt: "Slow cinematic camera push in...",
                        delivery: "calm, steady, warm",
                        pause_after: 0.6
                      };
                      setGeneratedScenes([...generatedScenes, newScene]);
                    }}
                    style={{ background: 'var(--line-soft)', color: 'var(--t-body)', border: '1px dashed rgb(59 130 246 / calc(0.4 * var(--tint)))', padding: '9px 18px', borderRadius: 8, fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}
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
            <div className="glass-panel page-head">
              <div>
                <h2 className="page-title"><Mic size={18} color="var(--a-blue)" /> Voice Studio</h2>
                <p className="page-sub">
                  Gemini ও ElevenLabs-এর আবেগপূর্ণ কণ্ঠ শুনুন, অথবা নিজের কণ্ঠ রেকর্ড করে লোকাল F5-TTS দিয়ে ক্লোন করুন।
                </p>
              </div>

              {/* Engine filter (segmented) */}
              <div className="segmented" role="tablist" aria-label="Filter voices by engine">
                {([
                  { id: 'all', label: 'All', count: geminiVoiceEntries.length + ELEVENLABS_VOICE_LIST.length + f5Voices.length },
                  { id: 'gemini', label: 'Gemini', count: geminiVoiceEntries.length },
                  { id: 'elevenlabs', label: 'ElevenLabs', count: ELEVENLABS_VOICE_LIST.length },
                  { id: 'f5tts', label: 'F5-TTS', count: f5Voices.length },
                ] as const).map(item => (
                  <button
                    key={item.id}
                    type="button"
                    role="tab"
                    aria-selected={voiceShowcaseEngineFilter === item.id}
                    className={`segmented-btn ${voiceShowcaseEngineFilter === item.id ? 'active' : ''}`}
                    onClick={() => setVoiceShowcaseEngineFilter(item.id)}
                  >
                    {item.label}
                    <span className="segmented-count">{item.count}</span>
                  </button>
                ))}
              </div>
            </div>

            {(voiceShowcaseEngineFilter === "all" || voiceShowcaseEngineFilter === "gemini") && renderKeyBanner("gemini")}
            {(voiceShowcaseEngineFilter === "all" || voiceShowcaseEngineFilter === "elevenlabs") && renderKeyBanner("elevenlabs")}

            {/* My Voices: record or upload a reference for F5-TTS */}
            {(voiceShowcaseEngineFilter === "all" || voiceShowcaseEngineFilter === "f5tts") && (
              <div className="glass-panel" style={{ padding: '20px 22px' }}>
                <div className="section-head">
                  <span className="section-icon secondary"><Mic size={16} /></span>
                  <div>
                    <div className="section-title">My Voices — নিজের কণ্ঠ সংরক্ষণ করুন</div>
                    <p className="section-sub">
                      ৮–১২ সেকেন্ডের পরিষ্কার, আবেগপূর্ণ আসল মানুষের কণ্ঠ রেকর্ড বা আপলোড করুন, এবং ঠিক যা বলেছেন তা হুবহু লিখুন। F5-TTS রেকর্ডিংয়ের আবেগ ও বিরতি অনুকরণ করে। রেকর্ডিং শুধু এই কম্পিউটারেই থাকে।
                    </p>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 120px', gap: 8 }}>
                      <input
                        type="text"
                        value={newVoiceName}
                        onChange={e => setNewVoiceName(e.target.value)}
                        placeholder="Voice name (e.g. My Narrator)"
                        style={{ padding: '9px 12px', fontSize: 13 }}
                      />
                      <select value={newVoiceLang} onChange={e => setNewVoiceLang(e.target.value)} style={{ padding: '9px 10px', fontSize: 13 }}>
                        <option value="bn">বাংলা</option>
                        <option value="hi">हिन्दी</option>
                        <option value="en">English</option>
                      </select>
                    </div>
                    <textarea
                      rows={3}
                      value={newVoiceTranscript}
                      onChange={e => setNewVoiceTranscript(e.target.value)}
                      placeholder="রেকর্ডিংয়ে ঠিক যা বলেছেন, হুবহু লিখুন (Exact transcript of the recording)"
                      style={{ padding: '9px 12px', fontSize: 13, lineHeight: 1.5 }}
                    />
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button
                        type="button"
                        className={`btn ${isRecording ? 'btn-secondary' : 'btn-secondary-soft'}`}
                        onClick={isRecording ? stopRecording : startRecording}
                        style={{ flex: 1 }}
                      >
                        {isRecording ? <Square size={12} /> : <Mic size={13} />}
                        {isRecording ? `Stop (${recordSeconds}s / ${MAX_RECORD_SECONDS}s)` : 'Record'}
                      </button>
                      <label className="btn btn-ghost" style={{ flex: 1 }}>
                        <Upload size={13} /> Upload file
                        <input
                          type="file"
                          accept="audio/*"
                          style={{ display: 'none' }}
                          onChange={e => {
                            const file = e.target.files?.[0];
                            if (file) setVoiceRecording(file, file.name);
                            e.target.value = "";
                          }}
                        />
                      </label>
                    </div>
                    {newVoiceUrl && <audio controls src={newVoiceUrl} style={{ width: '100%', height: 36 }} />}
                    <div style={{ fontSize: 11, color: 'var(--t-faint)', lineHeight: 1.45 }}>
                      টিপ: আবেগ দিয়ে, স্বাভাবিক বিরতি ও কণ্ঠের ওঠানামাসহ একটি নাটকীয় বাক্য পড়ুন। শান্ত ঘরে, মাইক থেকে এক হাত দূরে রেকর্ড করুন।
                    </div>
                    {voiceUploadError && (
                      <div style={{ fontSize: 12, color: 'var(--a-red)', background: 'rgb(239 68 68 / calc(0.12 * var(--tint)))', padding: '8px 10px', borderRadius: 8 }}>
                        {voiceUploadError}
                      </div>
                    )}
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={handleSaveCustomVoice}
                      disabled={isSavingVoice || isRecording || !newVoiceFile || !newVoiceName.trim() || !newVoiceTranscript.trim()}
                    >
                      {isSavingVoice ? 'Saving...' : 'Save my voice'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Voices, grouped by engine */}
            {([
              {
                engine: 'gemini' as const, title: 'Gemini TTS', sub: 'Expressive studio voices with scene-by-scene emotion',
                cards: geminiVoiceEntries.map(([id, gv]) => ({ engine: 'gemini' as const, id, name: gv.name, desc: gv.description, badge: 'Gemini TTS' })),
              },
              {
                engine: 'elevenlabs' as const, title: 'ElevenLabs', sub: 'Ultra-realistic human narrators',
                cards: ELEVENLABS_VOICE_LIST.map(ev => ({ engine: 'elevenlabs' as const, id: ev.id, name: ev.name, desc: ev.desc, badge: 'ElevenLabs', previewable: ev.id !== 'custom' })),
              },
              {
                engine: 'f5tts' as const, title: 'F5-TTS', sub: 'Local voice cloning — your recordings and presets',
                cards: f5Voices.map(fv => ({
                  engine: 'f5tts' as const,
                  id: fv.id,
                  name: fv.name,
                  desc: fv.custom ? `My recording · ${fv.duration ?? '?'}s · ${fv.transcript || ''}` : 'Preset reference voice — a clear recording of a real human voice usually sounds more natural',
                  badge: fv.custom ? 'My voice · F5-TTS' : 'F5-TTS preset',
                  mine: fv.custom,
                  onDelete: fv.custom ? () => handleDeleteCustomVoice(fv.id, fv.name) : undefined,
                })),
              },
            ]).filter(group => (voiceShowcaseEngineFilter === 'all' || voiceShowcaseEngineFilter === group.engine) && group.cards.length > 0).map(group => (
              <section key={group.engine} className="voice-group">
                <div className="voice-group-head">
                  <h3>{group.title}</h3>
                  <span className="segmented-count">{group.cards.length}</span>
                  <span className="voice-group-sub">{group.sub}</span>
                </div>
                <div className="voice-grid">
                  {group.cards.map(card => renderVoiceCard(card))}
                </div>
              </section>
            ))}
          </div>
        </div>

        {/* ========================================================================= */}
        {/* TAB 4: PROJECTS (every generated video, with its thumbnail and revisions) */}
        {/* ========================================================================= */}
        <div className={`tab-pane ${activeTab === 'gallery' ? 'active' : ''}`}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div className="glass-panel page-head">
              <div>
                <h2 className="page-title"><FolderOpen size={18} color="var(--a-blue)" /> Projects</h2>
                <p className="page-sub">
                  Every video you generate is saved here as a project. Design its thumbnail, refine or regenerate it, and download the video and thumbnail any time.
                </p>
                {jobs.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <button
                      type="button"
                      className="btn btn-danger-ghost"
                      onClick={handleDeleteAll}
                      style={{ fontSize: 12, padding: '5px 12px', display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 600 }}
                      title="Permanently delete all projects and their files"
                    >
                      <Trash2 size={13} /> Delete All Projects ({jobs.length})
                    </button>
                  </div>
                )}
              </div>
              <div className="page-stats">
                <div><strong>{jobs.length}</strong><span>Projects</span></div>
                <div><strong>{completedJobs.length}</strong><span>Ready</span></div>
                <div>
                  <strong>{Math.round(completedJobs.reduce((sum, j) => sum + (j.target_duration || 0), 0) / 60)}</strong>
                  <span>Minutes</span>
                </div>
              </div>
            </div>

            {jobs.length === 0 ? (
              <div className="glass-panel empty-state">
                <span className="empty-state-icon"><FolderOpen size={26} /></span>
                <div className="empty-state-title">No projects yet</div>
                <div className="empty-state-sub">Generate a video from the Production Studio or Story Studio and it will be saved here as a project.</div>
                <button type="button" className="btn btn-primary" onClick={() => switchTab('production')}>
                  <Plus size={14} /> Start a production
                </button>
              </div>
            ) : (
              <div className="gallery-grid">
                {jobs.map(cj => {
                  const typeInfo = VIDEO_TYPES.find(t => t.id === cj.video_type);
                  const busy = cj.status === 'QUEUED' || RUNNING_STATUSES.includes(cj.status);
                  return (
                    <article key={cj.id} className="glass-panel gallery-card">
                      <div className="gallery-media">
                        {cj.output_video ? (
                          <video
                            src={`${API_BASE}${cj.output_video}`}
                            poster={cj.thumbnail ? `${API_BASE}${cj.thumbnail}` : undefined}
                            controls
                            preload="metadata"
                          />
                        ) : cj.thumbnail ? (
                          <img src={`${API_BASE}${cj.thumbnail}`} alt="" className="gallery-poster" />
                        ) : (
                          <Video size={32} color="var(--t-faint)" />
                        )}
                        <span className="gallery-aspect">{cj.aspect_ratio}</span>
                        {(cj.revision || 1) > 1 && <span className="gallery-revision">v{cj.revision}</span>}
                      </div>

                      <div className="gallery-body">
                        <div className="project-title-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                          <h4 className="gallery-title" title={cj.title} style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {cj.title}
                          </h4>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                            {cj.status !== 'DONE' && getStatusBadge(cj.status)}
                            <button
                              type="button"
                              className="btn btn-icon btn-danger-ghost"
                              onClick={() => handleDelete(cj)}
                              title={`Delete project "${cj.title}"`}
                              style={{ color: 'var(--a-rose)', width: 28, height: 28, padding: 0 }}
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                        <div className="gallery-meta">
                          {typeInfo && <span className="chip chip-primary"><typeInfo.Icon size={11} /> {typeInfo.desc}</span>}
                          <span className="chip">{cj.language === 'bn' ? 'বাংলা' : cj.language === 'hi' ? 'हिन्दी' : 'English'}</span>
                          {cj.target_duration ? <span className="chip"><Clock size={11} /> {cj.target_duration >= 60 ? `${Math.round(cj.target_duration / 6) / 10}m` : `${cj.target_duration}s`}</span> : null}
                          {cj.scenes && cj.scenes.length > 0 && <span className="chip">{cj.scenes.length} scenes</span>}
                          {cj.music_track && <span className="chip" title={cj.music_track}><Music size={11} /> Music</span>}
                          {cj.resolution ? <span className="chip">{cj.resolution}p · {cj.fps || 30} fps</span> : null}
                          {cj.thumbnail_design && <span className="chip"><ImageIcon size={11} /> Custom thumbnail</span>}
                        </div>

                        {busy && (
                          <div className="project-progress">
                            <div className="project-progress-text">
                              <span>{cj.current_step || 'Waiting in queue'}</span>
                              <strong>{cj.progress}%</strong>
                            </div>
                            <div className="project-progress-track"><div style={{ width: `${cj.progress}%` }} /></div>
                            {cj.output_video && <span className="project-progress-note">The previous version stays available until this one finishes.</span>}
                          </div>
                        )}
                        {cj.status === 'FAILED' && (
                          <div className="project-error" title={cj.error_message}>
                            <AlertTriangle size={13} /> {cj.error_message || 'Generation failed'}
                          </div>
                        )}

                        <div className="gallery-sub">
                          {new Date(cj.created_at * 1000).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })} · {cj.voice}
                        </div>

                        <div className="gallery-actions">
                          {cj.output_video ? (
                            <a className="btn btn-primary" href={downloadUrl(cj.id, "video")} style={{ flex: 1 }}>
                              <Download size={14} /> Video
                            </a>
                          ) : (
                            <button type="button" className="btn btn-primary" disabled style={{ flex: 1 }}>
                              <Download size={14} /> Video
                            </button>
                          )}
                          {cj.thumbnail ? (
                            <a className="btn btn-ghost" href={downloadUrl(cj.id, "thumbnail")} style={{ flex: 1 }}>
                              <Download size={14} /> Thumbnail
                            </a>
                          ) : (
                            <button type="button" className="btn btn-ghost" disabled style={{ flex: 1 }}>
                              <Download size={14} /> Thumbnail
                            </button>
                          )}
                          {cj.status === 'DONE' && (
                            <a className="btn btn-ghost" href={downloadUrl(cj.id, "subtitles")} style={{ padding: '0 10px' }} title="Download SRT Subtitles (.srt)">
                              <Subtitles size={14} />
                            </a>
                          )}
                        </div>
                        <div className="gallery-actions" style={{ paddingTop: 0, marginTop: 0 }}>
                          <button
                            type="button"
                            className="btn btn-ghost"
                            style={{ flex: 1 }}
                            onClick={() => setThumbStudioJobId(cj.id)}
                            disabled={!hasSceneImages(cj)}
                            title={hasSceneImages(cj) ? "Design a thumbnail" : "Available once the scene images are rendered"}
                          >
                            <ImageIcon size={14} /> Design thumbnail
                          </button>
                          {cj.status === 'FAILED' && (
                            <button
                              type="button"
                              className="btn btn-primary"
                              style={{ flex: 1 }}
                              onClick={() => handleResumeFailed(cj.id)}
                              disabled={busy}
                              title="Resume this failed project from where it stopped"
                            >
                              <RefreshCw size={14} /> Resume
                            </button>
                          )}
                          <button
                            type="button"
                            className="btn btn-ghost"
                            style={{ flex: 1 }}
                            onClick={() => setReviseTarget({ id: cj.id, mode: cj.status === 'FAILED' ? "regenerate" : "refine" })}
                            disabled={busy}
                            title={busy ? "Wait for the current render to finish" : "Refine with a prompt or regenerate"}
                          >
                            <Wand2 size={14} /> {cj.status === 'FAILED' ? "Redo" : "Refine / Redo"}
                          </button>
                          <button
                            type="button"
                            className="btn btn-danger-ghost"
                            onClick={() => handleDelete(cj)}
                            title={`Delete project "${cj.title}" and all its files`}
                            aria-label={`Delete ${cj.title}`}
                            style={{ color: 'var(--a-rose)', display: 'inline-flex', alignItems: 'center', gap: 4, padding: '7px 10px', fontSize: 12, fontWeight: 600 }}
                          >
                            <Trash2 size={13} /> Delete
                          </button>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* ========================================================================= */}
        {/* TAB 6: AI MODELS & HARDWARE REQUIREMENTS                                  */}
        {/* ========================================================================= */}
        <div className={`tab-pane ${activeTab === 'models' ? 'active' : ''}`}>
          <ModelsPage apiBase={API_BASE} active={activeTab === 'models'} />
        </div>

        <div className={`tab-pane ${activeTab === 'workflow' ? 'active' : ''}`}>
          <WorkflowPage />
        </div>

      </main>

      {/* Studio Settings: floating button + popup (bottom-right) */}
      <div className="settings-fab-wrap" ref={settingsRef}>
        {showSettings && (
          <div className="settings-popup glass-panel" role="dialog" aria-label="Studio settings">
            <div className="settings-popup-head">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Settings size={16} color="var(--a-blue)" />
                <strong style={{ fontSize: 14, color: 'var(--t-strong)' }}>Studio Settings</strong>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button
                  type="button"
                  className="settings-icon-btn"
                  onClick={() => { fetchJobs(); fetchStatus(); fetchTtsConfig(); fetchEngines(); fetchMusicTracks(); }}
                  title="Refresh status"
                >
                  <RefreshCw size={13} />
                </button>
                <button type="button" className="settings-icon-btn" onClick={() => setShowSettings(false)} title="Close">
                  <X size={14} />
                </button>
              </div>
            </div>

            {/* Appearance */}
            <div className="settings-section">
              <div className="settings-section-title">Appearance</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                {(["dark", "light"] as const).map(mode => (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => setTheme(mode)}
                    style={{ padding: '7px 4px', borderRadius: 8, fontSize: 12, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, background: theme === mode ? 'rgb(37 99 235 / calc(0.22 * var(--tint)))' : 'var(--surface)', border: '1px solid var(--line)', outline: theme === mode ? '1.5px solid #3b82f6' : 'none', outlineOffset: -1.5, color: theme === mode ? 'var(--a-blue)' : 'var(--t-muted)' }}
                  >
                    {mode === "dark" ? <Moon size={13} /> : <Sun size={13} />}
                    {mode === "dark" ? 'Dark' : 'Light'}
                  </button>
                ))}
              </div>
            </div>

            {/* Services */}
            <div className="settings-section">
              <div className="settings-section-title">Services</div>
              <div className="settings-row">
                <span className="settings-label"><Bot size={13} /> Story LLM (Ollama)</span>
                <span className={`settings-pill ${systemStatus.ollama_online ? 'ok' : 'bad'}`}>{systemStatus.ollama_online ? 'Online' : 'Offline'}</span>
              </div>
              {systemStatus.ollama_online && systemStatus.models.length > 0 && (
                <select
                  value={ollamaModel}
                  onChange={e => setOllamaModel(e.target.value)}
                  style={{ width: '100%', padding: '7px 10px', fontSize: 12, marginBottom: 8 }}
                  title="Model used to write scripts"
                >
                  {systemStatus.models.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              )}
              <div className="settings-row">
                <span className="settings-label"><Cpu size={13} /> Image &amp; Video (ComfyUI)</span>
                <span className={`settings-pill ${systemStatus.comfyui_online ? 'ok' : 'bad'}`}>{systemStatus.comfyui_online ? 'Port 8188' : 'Offline'}</span>
              </div>
              <div className="settings-row">
                <span className="settings-label"><Zap size={13} /> F5-TTS voice cloning</span>
                <span className={`settings-pill ${engines.f5tts?.ready ? 'ok' : 'warn'}`}>{engines.f5tts?.ready ? 'Ready' : 'Not set up'}</span>
              </div>
              <div className="settings-row" style={{ color: 'var(--t-faint)', fontSize: 11 }}>
                <span>Platform: {systemStatus.platform || '—'}</span>
                <span>Encoder: {systemStatus.video_encoder || '—'}</span>
              </div>
            </div>

            {/* Voice engine */}
            <div className="settings-section">
              <div className="settings-section-title">Default voice engine</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
                {ENGINE_OPTIONS.map(opt => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setDefaultEngine(opt.id)}
                    style={{ padding: '7px 4px', borderRadius: 8, fontSize: 11, fontWeight: 700, background: ttsEngine === opt.id ? 'rgb(37 99 235 / calc(0.22 * var(--tint)))' : 'var(--surface)', border: '1px solid var(--line)', outline: ttsEngine === opt.id ? `1.5px solid ${opt.accent}` : 'none', outlineOffset: -1.5, color: ttsEngine === opt.id ? opt.accent : 'var(--t-muted)' }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* API keys */}
            <div className="settings-section">
              <div className="settings-section-title">API keys</div>
              {(["gemini", "elevenlabs"] as KeyProvider[]).map(provider => {
                const hasKey = provider === "gemini" ? hasGeminiKey : hasElevenLabsKey;
                const masked = provider === "gemini" ? geminiMaskedKey : maskedKey;
                return (
                  <div className="settings-row" key={provider}>
                    <span className="settings-label"><Key size={13} /> {providerName(provider)}</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span className={`settings-pill ${hasKey ? 'ok' : 'warn'}`}>{hasKey ? masked : 'Not set'}</span>
                      <button type="button" className="settings-link-btn" onClick={() => openKeyModal(provider)}>
                        {hasKey ? 'Manage' : 'Set key'}
                      </button>
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Production queue */}
            <div className="settings-section" style={{ borderBottom: 'none', paddingBottom: 0 }}>
              <div className="settings-section-title">Production queue</div>
              <div className="settings-row">
                <span className="settings-label"><Video size={13} /> Running</span>
                <span className={`settings-pill ${runningJobs.length > 0 ? 'info' : ''}`}>{runningJobs.length > 0 ? `${runningJobs[0].progress}%` : 'Idle'}</span>
              </div>
              <div className="settings-row">
                <span className="settings-label"><Clock size={13} /> Waiting</span>
                <span className="settings-pill">{queuedJobs.length}</span>
              </div>
            </div>
          </div>
        )}

        <button
          type="button"
          className={`settings-fab ${showSettings ? 'open' : ''}`}
          onClick={() => setShowSettings(open => !open)}
          aria-label={showSettings ? 'Close studio settings' : 'Open studio settings'}
          aria-expanded={showSettings}
          title="Studio settings"
        >
          <span className="settings-fab-icon">
            {showSettings ? <X size={16} /> : <Settings size={16} />}
          </span>
          <span className="settings-fab-label">Settings</span>
          {!showSettings && (runningJobs.length + queuedJobs.length) > 0 && (
            <span className="settings-fab-count" title="Jobs in queue">{runningJobs.length + queuedJobs.length}</span>
          )}
        </button>
      </div>

      {/* Voice API Key Modal (Gemini + ElevenLabs) */}
      {thumbStudioJob && (
        <ThumbnailStudio
          key={thumbStudioJob.id}
          apiBase={API_BASE}
          project={thumbStudioJob}
          onClose={() => setThumbStudioJobId(null)}
          onSaved={fetchJobs}
        />
      )}

      {reviseJob && reviseTarget && (
        <ProjectReviseDialog
          key={reviseJob.id}
          apiBase={API_BASE}
          project={reviseJob}
          initialMode={reviseTarget.mode}
          onClose={() => setReviseTarget(null)}
          onQueued={() => {
            if (justFinishedId === reviseJob.id) setJustFinishedId(null);
            fetchJobs();
          }}
        />
      )}

      {/* Delete Single Project Confirmation Modal */}
      {jobToDelete && (
        <div className="studio-overlay" role="dialog" aria-modal="true" style={{ zIndex: 10000 }}>
          <div className="glass-panel modal-panel" style={{ maxWidth: 440, padding: 24, textAlign: 'left' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
              <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'rgb(244 63 94 / 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--a-rose)', flexShrink: 0 }}>
                <Trash2 size={20} />
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--t-strong)' }}>
                  Delete Project?
                </h3>
                <span style={{ fontSize: 12, color: 'var(--t-muted)' }}>
                  This action permanently removes all files
                </span>
              </div>
            </div>

            <div style={{ background: 'var(--well)', padding: 12, borderRadius: 8, fontSize: 13, color: 'var(--t-body)', marginBottom: 18, lineHeight: 1.5 }}>
              Are you sure you want to delete <strong>"{jobToDelete.title}"</strong>?
              <div style={{ fontSize: 11.5, color: 'var(--t-muted)', marginTop: 6 }}>
                The video, thumbnail, voiceover audio, images, and storyboard will be deleted permanently.
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setJobToDelete(null)}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                style={{ background: 'var(--a-rose)', color: '#fff', display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, border: 'none', padding: '8px 14px', borderRadius: 8, cursor: 'pointer' }}
                onClick={() => confirmDeleteProject(jobToDelete)}
                disabled={isDeleting}
              >
                <Trash2 size={14} />
                {isDeleting ? "Deleting..." : "Delete Project"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete ALL Projects Confirmation Modal */}
      {showDeleteAllConfirm && (
        <div className="studio-overlay" role="dialog" aria-modal="true" style={{ zIndex: 10000 }}>
          <div className="glass-panel modal-panel" style={{ maxWidth: 460, padding: 24, textAlign: 'left' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
              <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'rgb(244 63 94 / 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--a-rose)', flexShrink: 0 }}>
                <Trash2 size={20} />
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--t-strong)' }}>
                  Delete All Projects?
                </h3>
                <span style={{ fontSize: 12, color: 'var(--t-muted)' }}>
                  Permanently wipe all {jobs.length} projects
                </span>
              </div>
            </div>

            <div style={{ background: 'var(--well)', padding: 12, borderRadius: 8, fontSize: 13, color: 'var(--t-body)', marginBottom: 18, lineHeight: 1.5 }}>
              Are you sure you want to delete <strong>ALL {jobs.length} projects</strong>? Every video, audio, image and asset on this computer will be permanently deleted.
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setShowDeleteAllConfirm(false)}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                style={{ background: 'var(--a-rose)', color: '#fff', display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, border: 'none', padding: '8px 14px', borderRadius: 8, cursor: 'pointer' }}
                onClick={confirmDeleteAllProjects}
                disabled={isDeleting}
              >
                <Trash2 size={14} />
                {isDeleting ? "Deleting All..." : `Yes, Delete All (${jobs.length})`}
              </button>
            </div>
          </div>
        </div>
      )}


      {keyModal && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 9999, background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
          <div className="glass-panel modal-panel" style={{ width: '100%', maxWidth: 520, padding: 28 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 36, height: 36, borderRadius: 10, background: '#f59e0b', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Key size={18} color="#000" />
                </div>
                <div>
                  <h3 style={{ fontSize: 17, fontWeight: 800, color: 'var(--t-strong)', margin: 0 }}>Voice API Configuration</h3>
                  <p style={{ fontSize: 12, color: 'var(--t-muted)', margin: 0 }}>Expressive, human-like narration</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setKeyModal(null)}
                style={{ background: 'none', color: 'var(--t-muted)', fontSize: 18, cursor: 'pointer', padding: 4 }}
              >
                ✕
              </button>
            </div>

            {/* Provider switch */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 16 }}>
              {(["gemini", "elevenlabs"] as KeyProvider[]).map(provider => {
                const hasKey = provider === "gemini" ? hasGeminiKey : hasElevenLabsKey;
                return (
                  <button
                    key={provider}
                    type="button"
                    onClick={() => openKeyModal(provider)}
                    style={{ padding: '8px 10px', borderRadius: 8, fontSize: 12, fontWeight: 700, background: keyModal === provider ? 'rgb(37 99 235 / calc(0.25 * var(--tint)))' : 'var(--surface)', border: '1px solid var(--line)', outline: keyModal === provider ? '2px solid #3b82f6' : 'none', outlineOffset: -2, color: keyModal === provider ? 'var(--a-blue)' : 'var(--t-muted)' }}
                  >
                    {provider === "gemini" ? '✨ Gemini' : '👑 ElevenLabs'} {hasKey ? '✓' : ''}
                  </button>
                );
              })}
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 700, color: 'var(--a-blue)', display: 'block', marginBottom: 6 }}>
                {keyModal === "gemini" ? 'Gemini API Key (Google AI Studio):' : 'ElevenLabs API Key (xi-api-key):'}
              </label>
              <input
                type="password"
                value={keyInput}
                onChange={e => setKeyInput(e.target.value)}
                placeholder={keyModal === "gemini"
                  ? (hasGeminiKey ? `Current Key: ${geminiMaskedKey}` : "Paste your Gemini API key")
                  : (hasElevenLabsKey ? `Current Key: ${maskedKey}` : "Paste your key (e.g. sk_... or xi-...)")}
                style={{ width: '100%', padding: '10px 14px', fontSize: 13, borderRadius: 8 }}
              />
              <div style={{ marginTop: 6, display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <span style={{ color: 'var(--t-faint)' }}>
                  {keyModal === "gemini"
                    ? (hasGeminiKey ? `Active Key: ${geminiMaskedKey}` : 'No key saved yet')
                    : (hasElevenLabsKey ? `Active Key: ${maskedKey}` : 'No key saved yet')}
                </span>
                <a
                  href={keyModal === "gemini" ? "https://aistudio.google.com/apikey" : "https://elevenlabs.io"}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: 'var(--a-blue)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}
                >
                  <ExternalLink size={11} /> {keyModal === "gemini" ? 'Get a key from Google AI Studio' : 'Get a key from elevenlabs.io'}
                </a>
              </div>
            </div>

            {keyStatus && (
              <div style={{
                background: keyStatus.valid ? 'rgb(16 185 129 / calc(0.15 * var(--tint)))' : 'rgb(239 68 68 / calc(0.15 * var(--tint)))',
                border: keyStatus.valid ? '1px solid rgb(16 185 129 / calc(0.35 * var(--tint)))' : '1px solid rgb(239 68 68 / calc(0.35 * var(--tint)))',
                padding: '10px 14px',
                borderRadius: 8,
                fontSize: 12,
                color: keyStatus.valid ? 'var(--a-green)' : 'var(--a-red)',
                marginBottom: 16,
                fontWeight: 600
              }}>
                {keyStatus.valid ? '✅ ' : '❌ '}
                {keyStatus.message}
              </div>
            )}

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10, borderTop: '1px solid var(--line)', paddingTop: 16 }}>
              <button
                type="button"
                onClick={handleTestKey}
                disabled={isTestingKey || !keyInput.trim()}
                style={{ background: 'var(--line-soft)', color: 'var(--t-body)', border: '1px solid var(--line)', padding: '9px 16px', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer' }}
              >
                {isTestingKey ? 'Verifying...' : '🔍 Test Key'}
              </button>
              <button
                type="button"
                onClick={handleSaveKey}
                disabled={isSavingKey || !keyInput.trim()}
                style={{ background: 'var(--primary)', color: '#ffffff', border: 'none', padding: '9px 20px', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer', boxShadow: '0 0 16px var(--primary-glow)' }}
              >
                {isSavingKey ? 'Saving...' : '💾 Save & Activate'}
              </button>
            </div>
          </div>
        </div>
      )}

      <Toaster />
    </div>
  );
}
