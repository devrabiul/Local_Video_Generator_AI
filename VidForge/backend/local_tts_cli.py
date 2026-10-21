"""Batch voice-cloning for VidForge's local voices.

Loads the model ONCE and voices every scene of a story from the same reference recording with
the same seed, so the narrator keeps one consistent voice, tone and pace from start to finish.

Backends (the cloning ones copy a reference clip + its exact transcript):
  f5          F5-TTS v1 Base (SWivid/F5-TTS) — English/Chinese only; poor for Bengali/Hindi
  f5_bengali  multilingual-tts/F5-TTS-OpenBible-Bengali — F5 trained on Bengali read speech (CC-BY-SA)
  mms_ben     facebook/mms-tts-ben — one fixed Bengali voice, no cloning (CC-BY-NC)
  indicf5     ai4bharat/IndicF5 — Bengali, Hindi and 9 more Indian languages (MIT licence)
  omnivoice   k2-fsa/OmniVoice — 600+ languages incl. Bengali/Hindi (weights CC-BY-NC: non-commercial)

Usage:
  python local_tts_cli.py --backend omnivoice --ref_audio ref.wav --ref_text "..." --jobs jobs.json
where jobs.json is a list of {"text": "...", "output": "/path/scene.wav", "language": "bn"}.
Prints "DONE <index>" after each finished scene.
"""
import argparse
import json
import random
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import soundfile as sf
import torch


def pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def seed_everything(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def to_float32(audio) -> np.ndarray:
    audio = np.asarray(audio)
    if audio.dtype == np.int16:
        return audio.astype(np.float32) / 32768.0
    return audio.astype(np.float32).reshape(-1)


class OmniVoiceBackend:
    sample_rate = 24000

    def __init__(self, ref_audio: str, ref_text: str, device: str):
        from omnivoice import OmniVoice
        # Loading onto Apple MPS hung indefinitely in testing (omnivoice 0.2.1, torch 2.14) while CPU loaded
        # in seconds, so OmniVoice runs on CUDA when available and on the CPU otherwise.
        device = "cuda" if device == "cuda" else "cpu"
        dtype = torch.float32 if device == "cpu" else torch.float16
        self.model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=device, dtype=dtype)
        # Build the voice once and reuse it for every scene
        self.prompt = self.model.create_voice_clone_prompt(ref_audio=ref_audio, ref_text=ref_text)

    def __call__(self, text: str, language: str) -> np.ndarray:
        lang_map = {
            "bn": "Bengali", "hi": "Hindi", "en": "English",
            "es": "Spanish", "fr": "French", "de": "German",
            "ar": "Arabic", "zh": "Chinese", "ja": "Japanese"
        }
        lang = lang_map.get(language, language) or "Bengali"
        return to_float32(self.model.generate(text=text, language=lang, voice_clone_prompt=self.prompt)[0])


class IndicF5Backend:
    sample_rate = 24000

    def __init__(self, ref_audio: str, ref_text: str, device: str):
        from transformers import AutoModel
        # Gated on Hugging Face: accept the terms on huggingface.co/ai4bharat/IndicF5 and log in first.
        # Needs AI4Bharat's own f5_tts package: pip install git+https://github.com/ai4bharat/IndicF5.git
        self.model = AutoModel.from_pretrained("ai4bharat/IndicF5", trust_remote_code=True)
        try:
            self.model = self.model.to(device)
        except Exception:
            pass
        self.ref_audio, self.ref_text = ref_audio, ref_text

    def __call__(self, text: str, language: str) -> np.ndarray:
        return to_float32(self.model(text, ref_audio_path=self.ref_audio, ref_text=self.ref_text))


class MMSBengaliBackend:
    """facebook/mms-tts-ben (VITS). One built-in voice: the reference recording is not used."""

    def __init__(self, ref_audio: str, ref_text: str, device: str):
        from transformers import AutoTokenizer, VitsModel
        self.model = VitsModel.from_pretrained("facebook/mms-tts-ben")
        self.tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-ben")
        self.sample_rate = self.model.config.sampling_rate  # 16 kHz

    def __call__(self, text: str, language: str) -> np.ndarray:
        with torch.no_grad():
            return to_float32(self.model(**self.tokenizer(text, return_tensors="pt")).waveform[0].numpy())


class F5BengaliBackend:
    """multilingual-tts/F5-TTS-OpenBible-Bengali, loaded as its model card shows (Hydra config + EMA weights)."""
    sample_rate = 24000
    REPO = "multilingual-tts/F5-TTS-OpenBible-Bengali"

    def __init__(self, ref_audio: str, ref_text: str, device: str):
        from huggingface_hub import hf_hub_download
        from hydra.utils import get_class
        from omegaconf import OmegaConf
        from f5_tts.infer.utils_infer import load_model, load_vocoder, preprocess_ref_audio_text
        # The card mentions F5-TTS_OpenBible_Bengali.yaml; the file actually in the repo is this one
        cfg = OmegaConf.load(hf_hub_download(self.REPO, "F5TTS_v1_Base_Open_Bible_Bengali.yaml"))
        self.device = device
        self.vocoder = load_vocoder(vocoder_name="vocos", is_local=False, device=device)
        self.model = load_model(
            get_class(f"f5_tts.model.{cfg.model.backbone}"), cfg.model.arch,
            hf_hub_download(self.REPO, "model_last.pt"),
            mel_spec_type="vocos", vocab_file=hf_hub_download(self.REPO, "vocab.txt"), use_ema=True, device=device,
        )
        self.ref_audio, self.ref_text = preprocess_ref_audio_text(ref_audio, ref_text)

    def __call__(self, text: str, language: str) -> np.ndarray:
        from f5_tts.infer.utils_infer import infer_process
        wav, sr, _ = infer_process(self.ref_audio, self.ref_text, text, self.model, self.vocoder,
                                   mel_spec_type="vocos", device=self.device)
        self.sample_rate = sr
        return to_float32(wav)


class F5Backend:
    sample_rate = 24000

    def __init__(self, ref_audio: str, ref_text: str, device: str, ckpt_file: str = "", vocab_file: str = ""):
        import f5_infer_cli  # applies its Windows torchaudio / safetensors fixes on import
        from f5_tts.api import F5TTS
        local = Path(__file__).resolve().parent / "models" / "F5-TTS"
        ckpt = ckpt_file or next((str(p) for p in (local / "model_1250000.pt", local / "model_1250000.safetensors") if p.exists()), "")
        self.f5 = F5TTS(ckpt_file=ckpt, vocab_file=vocab_file)
        self.ref_audio = ref_audio
        self.ref_text = f5_infer_cli.transliterate_indic_to_latin(ref_text)
        self._fix = f5_infer_cli.transliterate_indic_to_latin

    def __call__(self, text: str, language: str) -> np.ndarray:
        wav, sr, _ = self.f5.infer(ref_file=self.ref_audio, ref_text=self.ref_text, gen_text=self._fix(text), speed=1.0)
        self.sample_rate = sr
        return to_float32(wav)


def main():
    parser = argparse.ArgumentParser(description="VidForge local voice-cloning batch")
    parser.add_argument("--backend", choices=("f5", "f5_bengali", "mms_ben", "indicf5", "omnivoice"), required=True)
    parser.add_argument("--ref_audio", required=True)
    parser.add_argument("--ref_text", required=True)
    parser.add_argument("--jobs", required=True, help="JSON list of {text, output, language}")
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--ckpt_file", default="")
    parser.add_argument("--vocab_file", default="")
    args = parser.parse_args()

    jobs = json.loads(Path(args.jobs).read_text(encoding="utf-8"))
    device = pick_device()
    print(f"Loading {args.backend} on {device}...", flush=True)
    if args.backend == "omnivoice":
        backend = OmniVoiceBackend(args.ref_audio, args.ref_text, device)
    elif args.backend == "indicf5":
        backend = IndicF5Backend(args.ref_audio, args.ref_text, device)
    elif args.backend == "f5_bengali":
        backend = F5BengaliBackend(args.ref_audio, args.ref_text, device)
    elif args.backend == "mms_ben":
        backend = MMSBengaliBackend(args.ref_audio, args.ref_text, device)
    else:
        backend = F5Backend(args.ref_audio, args.ref_text, device, args.ckpt_file, args.vocab_file)

    for i, job in enumerate(jobs):
        seed_everything(args.seed)  # same seed for every scene keeps the delivery consistent
        audio = backend(job["text"], job.get("language", ""))
        out = Path(job["output"])
        out.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out), audio, backend.sample_rate)
        print(f"DONE {i}", flush=True)


if __name__ == "__main__":
    main()
