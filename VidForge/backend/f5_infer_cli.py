import argparse
import sys
import os
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Fix Windows torchaudio 2.11+ torchcodec dependency
import soundfile as sf
import torch
import torchaudio

def _sf_load(uri, **kwargs):
    data, samplerate = sf.read(str(uri), dtype="float32")
    tensor = torch.from_numpy(data)
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)
    else:
        tensor = tensor.t()
    return tensor, samplerate

torchaudio.load = _sf_load

# Fix Windows safetensors direct CUDA mmap error: "The paging file is too small for this operation to complete. (os error 1455)"
import safetensors.torch
_orig_load_file = safetensors.torch.load_file

def _safe_load_file(filename, device="cpu"):
    with open(str(filename), "rb") as f:
        data = f.read()
    tensors = safetensors.torch.load(data)
    if device != "cpu":
        target_device = torch.device(device)
        return {k: v.to(target_device) for k, v in tensors.items()}
    return tensors

safetensors.torch.load_file = _safe_load_file

import re

def is_indic_text(text: str) -> bool:
    """Checks if text contains Bengali, Devanagari, or other South Asian script characters."""
    return any("\u0980" <= c <= "\u09ff" or "\u0900" <= c <= "\u097f" for c in text)

def transliterate_indic_to_latin(text: str) -> str:
    """Converts Bengali or Indic script text into clean, pronounceable Latin phonetic characters
    so that the default F5-TTS base model (trained on EN/ZH) can accurately synthesize the speech
    without dropping characters as unknown out-of-vocab tokens.
    """
    if not is_indic_text(text):
        return text

    t = text.replace("।", ".").replace("—", ", ").replace("–", ", ").replace("…", "...")
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')

    # Common word mappings for natural Bengali phonetics
    word_map = {
        "ক্ষিতিমোহন": "Khitimohon", "তিতুমীর": "Titumiir", "বাঁশের": "bansher", "কেল্লা": "kella",
        "ঐতিহাসিক": "oitihasik", "প্রতিরোধ": "protirodh", "প্রাচীন": "pracheen", "ইতিহাস": "itihas",
        "গৌরবময়": "gourob moy", "বীরত্ব": "birootbo", "ত্যাগ": "tyag", "কাহিনী": "kahini",
        "রূপকথা": "ruupkotha", "ধূলিকণা": "dhuulikona", "জনপদ": "jonopod", "বাংলা": "bangla",
        "বাংলাদেশ": "bangladesh", "স্বাধীনতা": "shadhinota", "সংগ্রাম": "songram", "যুদ্ধ": "juddho"
    }
    for bn_w, en_w in word_map.items():
        t = t.replace(bn_w, en_w)

    try:
        from unidecode import unidecode
        t = unidecode(t)
    except Exception:
        pass

    # Clean up artifacts from unidecode (e.g. / for ।)
    t = t.replace(" / ", ". ").replace("/", ". ")
    t = re.sub(r"['`]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def main():
    parser = argparse.ArgumentParser(description="VidForge F5-TTS CLI Inference Engine")
    parser.add_argument("--ref_audio", required=True, help="Path to reference audio file (.wav or .mp3)")
    parser.add_argument("--ref_text", default="", help="Transcript for reference audio (optional if transcribed)")
    parser.add_argument("--gen_text", required=True, help="Text to generate/synthesize")
    parser.add_argument("--output", required=True, help="Path to output audio (.wav or .mp3)")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed multiplier")
    parser.add_argument("--remove_silence", action="store_true", help="Remove long silences")
    parser.add_argument("--ckpt_file", default="", help="Checkpoint to use instead of the default base model (e.g. a Bengali fine-tune)")
    parser.add_argument("--vocab_file", default="", help="Vocabulary file that matches --ckpt_file")

    args = parser.parse_args()

    ref_audio_path = Path(args.ref_audio).resolve()
    if not ref_audio_path.exists():
        print(f"ERROR: Reference audio not found at: {ref_audio_path}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Use a temp wav output if target is mp3
    is_mp3 = out_path.suffix.lower() == ".mp3"
    target_wav = out_path.with_suffix(".wav") if is_mp3 else out_path

    print(f"Loading F5-TTS model on GPU...")
    from f5_tts.api import F5TTS
    local_pt = Path(__file__).resolve().parent / "models" / "F5-TTS" / "model_1250000.pt"
    local_safetensors = Path(__file__).resolve().parent / "models" / "F5-TTS" / "model_1250000.safetensors"
    if args.ckpt_file:
        ckpt_file = args.ckpt_file
    elif local_pt.exists():
        ckpt_file = str(local_pt)
    elif local_safetensors.exists():
        ckpt_file = str(local_safetensors)
    else:
        ckpt_file = ""
    if ckpt_file:
        print(f"Using local checkpoint: {ckpt_file}")
    f5 = F5TTS(ckpt_file=ckpt_file, vocab_file=args.vocab_file)

    vocab_has_bengali = False
    vocab_to_check = args.vocab_file
    if not vocab_to_check:
        try:
            from importlib.resources import files
            vocab_to_check = str(files("f5_tts").joinpath("infer/examples/vocab.txt"))
        except Exception:
            vocab_to_check = ""

    if vocab_to_check and Path(vocab_to_check).exists():
        try:
            vocab_data = Path(vocab_to_check).read_text(encoding="utf-8")
            vocab_has_bengali = any("\u0980" <= c <= "\u09ff" for c in vocab_data)
        except Exception:
            pass

    ref_text = args.ref_text or ""
    gen_text = args.gen_text or ""

    if not vocab_has_bengali:
        if is_indic_text(ref_text):
            trans_ref = transliterate_indic_to_latin(ref_text)
            print(f"Transliterated Bengali reference text for F5-TTS base model: '{trans_ref}'")
            ref_text = trans_ref
        if is_indic_text(gen_text):
            trans_gen = transliterate_indic_to_latin(gen_text)
            print(f"Transliterated Bengali generation text for F5-TTS base model: '{trans_gen}'")
            gen_text = trans_gen

    print(f"Synthesizing text: '{gen_text[:50]}...' with reference: {ref_audio_path.name}")
    f5.infer(
        ref_file=str(ref_audio_path),
        ref_text=ref_text,
        gen_text=gen_text,
        file_wave=str(target_wav),
        speed=args.speed,
        remove_silence=args.remove_silence
    )

    if is_mp3 and target_wav.exists():
        import subprocess
        # Convert wav to high quality mp3
        ffmpeg = os.environ.get("VIDFORGE_FFMPEG", "ffmpeg")
        cmd = [ffmpeg, "-y", "-i", str(target_wav), "-b:a", "192k", str(out_path)]
        subprocess.run(cmd, capture_output=True, check=True)
        try:
            target_wav.unlink(missing_ok=True)
        except Exception:
            pass

    print(f"SUCCESS: Generated {out_path} ({out_path.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
