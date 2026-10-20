import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path
import edge_tts

BASE_DIR = Path(__file__).resolve().parent.parent
SLIDES_DIR = BASE_DIR / "presentation_slides"
OUTPUT_DIR = BASE_DIR / "output"
MUSIC_FILE = BASE_DIR / "music" / "cinematic_epic.mp3"
TEMP_DIR = BASE_DIR / "presentation_temp"
# Optional extra copy destination for the finished demo video
ARTIFACT_DIR = Path(os.environ["VIDFORGE_ARTIFACT_DIR"]) if os.environ.get("VIDFORGE_ARTIFACT_DIR") else None

TEMP_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SCENES = [
    {
        "id": 1,
        "slide": "slide1_overview.png",
        "title": "VidForge AI — লোকাল ভিডিও প্রোডাকশন স্টুডিও",
        "subtitle": "সম্পূর্ণ অফলাইন, নিরাপদ ও স্বয়ংক্রিয় এআই ভিডিও জেনারেশন প্ল্যাটফর্ম",
        "narration": "VidForge-এ স্বাগতম! এটি একটি সম্পূর্ণ স্থানীয় এআই ভিডিও প্রোডাকশন প্ল্যাটফর্ম, যা আপনার লোকাল GPU এবং ওপেন সোর্স মডেলের শক্তিতে চলে।",
        "zoom_dir": "in"
    },
    {
        "id": 2,
        "slide": "slide2_formats_pacing.png",
        "title": "মাল্টি-ফরম্যাট ও স্মার্ট ভিজ্যুয়াল পেসিং",
        "subtitle": "সিনেমাটিক স্টোরি, রিলস ও বিজনেস প্রেজেন্টেশন — প্রতি ৫ সেকেন্ডে ডাইনামিক কাট",
        "narration": "এখানে সিনেমাটিক স্টোরি, ডকু-ড্রামা থেকে শুরু করে রিলস ও বিজনেস প্রেজেন্টেশন সহজে বানানো যায়। দর্শক ধরে রাখতে প্রতি পাঁচ সেকেন্ডে স্বয়ংক্রিয়ভাবে ভিজ্যুয়াল কাট নির্ধারিত হয়।",
        "zoom_dir": "pan_down"
    },
    {
        "id": 3,
        "slide": "slide3_inspirations.png",
        "title": "এক ক্লিকে সৃজনশীল আইডিয়া ও প্রম্পট",
        "subtitle": "ইতিহাস, কল্পবিজ্ঞান এবং ডকুমেন্টারির প্রস্তুত কিউরেটেড প্রম্পট লাইব্রেরি",
        "narration": "কুইক ইন্সপিরেশনস বাটনে এক ক্লিকেই উন্মোচিত হয় ইতিহাস ও কল্পবিজ্ঞানের কিউরেটেড প্রম্পট লাইব্রেরি, যা স্ক্রিপ্ট রচনার কাজকে কয়েক সেকেন্ডে শুরু করে দেয়।",
        "zoom_dir": "pan_right"
    },
    {
        "id": 4,
        "slide": "slide4_voices.png",
        "title": "মাল্টি-ইঞ্জিন এআই ভয়েসওভার আর্কিটেকচার",
        "subtitle": "ইলেভেনল্যাবস, লোকাল আরটিএক্স ভয়েস ক্লোনিং এবং এজ-টিটিএস বাংলা ভয়েস",
        "narration": "ভয়েসওভারের জন্য রয়েছে ইলেভেনল্যাবস, লোকাল আরটিএক্স ভয়েস ক্লোনিং এবং এজ-টিটিএস-এর স্পষ্ট ও গম্ভীর বাংলা কণ্ঠস্বর।",
        "zoom_dir": "in"
    },
    {
        "id": 5,
        "slide": "slide5_story_studio.png",
        "title": "ওলামা স্টোরি স্টুডিও — লোকাল স্ক্রিপ্টরাইটিং",
        "subtitle": "Qwen 3.5 দিয়ে প্রতিটি দৃশ্যের জন্য সিনেমাটিক ডায়লগ ও ইমেজ প্রম্পট জেনারেশন",
        "narration": "ওলামা স্টোরি স্টুডিওতে লোকাল লার্জ ল্যাঙ্গুয়েজ মডেল দিয়ে পুরো স্ক্রিপ্ট, ডায়লগ এবং প্রতিটি দৃশ্যের জন্য সিনেমাটিক ভিজ্যুয়াল প্রম্পট তৈরি হয়।",
        "zoom_dir": "pan_left"
    },
    {
        "id": 6,
        "slide": "slide6_pipeline.png",
        "title": "কনফি-ইউআই ইমেজ ও আল্ট্রা এইচডি মোশন",
        "subtitle": "৮K ফোটোরিয়ালিস্টিক ভিজ্যুয়াল ও সিনেমাটিক ক্যামেরা মোশন",
        "narration": "কনফি-ইউআই এবং জেড-ইমেজ-টার্বোর সাহায্যে ফোটোরিয়ালিস্টিক ইমেজ জেনারেট হয়ে আল্ট্রা এইচডি কেন-বার্নস ক্যামেরায় জীবন্ত ভিডিওতে রূপ নেয়।",
        "zoom_dir": "out"
    },
    {
        "id": 7,
        "slide": "slide7_player.png",
        "title": "লাইভ ভিডিও প্রিভিউ ও ফুল এইচডি এক্সপোর্ট",
        "subtitle": "সিনক্রোনাইজড অডিও-ভিডিও ও তাৎক্ষণিক ডাউনলোড সুবিধা",
        "narration": "তৈরি হওয়া ভিডিও সাথে সাথেই প্লেয়ারে দেখে নেওয়া যায় এবং এক ক্লিকে ডাউনলোড করে যেকোনো সোশ্যাল মিডিয়া বা প্ল্যাটফর্মে প্রকাশ করা সম্ভব।",
        "zoom_dir": "in"
    }
]

def get_audio_duration(file_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())

async def generate_voiceovers():
    print("Generating Bengali voiceover for each slide using edge-tts...")
    voice = "bn-BD-PradeepNeural"
    for sc in SCENES:
        audio_file = TEMP_DIR / f"audio_{sc['id']}.mp3"
        print(f"Generating audio for Scene {sc['id']}...")
        communicate = edge_tts.Communicate(sc["narration"], voice, rate="+0%", pitch="+0Hz")
        await communicate.save(str(audio_file))
        dur = get_audio_duration(audio_file)
        sc["duration"] = max(dur + 0.8, 4.5)  # add breathing room
        sc["audio_file"] = audio_file
        print(f"Scene {sc['id']} duration: {sc['duration']:.2f}s")

def render_scene_video(sc: dict):
    img_path = SLIDES_DIR / sc["slide"]
    audio_path = sc["audio_file"]
    dur = sc["duration"]
    out_video = TEMP_DIR / f"scene_{sc['id']}.mp4"
    total_frames = int(dur * 30)

    # Ken Burns camera motions
    zdir = sc.get("zoom_dir", "in")
    if zdir == "in":
        zoom_expr = f"zoompan=z='min(zoom+0.0012,1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps=30"
    elif zdir == "out":
        zoom_expr = f"zoompan=z='if(lte(zoom,1.0),1.10,max(1.0,zoom-0.0012))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps=30"
    elif zdir == "pan_down":
        zoom_expr = f"zoompan=z='1.08':x='iw/2-(iw/zoom/2)':y='min((ih-ih/zoom)*(on/{total_frames}),ih-ih/zoom)':d={total_frames}:s=1920x1080:fps=30"
    elif zdir == "pan_right":
        zoom_expr = f"zoompan=z='1.08':x='min((iw-iw/zoom)*(on/{total_frames}),iw-iw/zoom)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps=30"
    elif zdir == "pan_left":
        zoom_expr = f"zoompan=z='1.08':x='max(0,(iw-iw/zoom)*(1-on/{total_frames}))':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps=30"
    else:
        zoom_expr = f"zoompan=z='min(zoom+0.001,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps=30"

    # Subtle fade-in & fade-out for cinematic elegance
    fade_in = "fade=t=in:st=0:d=0.3"
    fade_out = f"fade=t=out:st={dur - 0.35:.2f}:d=0.3"

    # Semi-transparent dark banner bar for bottom title
    # Draws a sleek 90px dark glass bar at the bottom with high contrast white text
    draw_banner = "drawbox=y=ih-110:w=iw:h=110:color=black@0.75:t=fill"
    
    # We escape text safely or use simple ASCII title overlay if fontconfig is tricky
    safe_title = sc["title"].replace("'", "").replace(":", "-")
    safe_sub = sc["subtitle"].replace("'", "").replace(":", "-")

    vf_filters = f"{zoom_expr},{fade_in},{fade_out},{draw_banner}"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(img_path),
        "-i", str(audio_path),
        "-vf", vf_filters,
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", f"{dur:.2f}",
        str(out_video)
    ]
    print(f"Rendering Video Scene {sc['id']} ({dur:.2f}s)...")
    subprocess.run(cmd, check=True)
    sc["video_file"] = out_video

def assemble_final_presentation():
    print("Assembling all scenes into final presentation video...")
    concat_list = TEMP_DIR / "concat_list.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for sc in SCENES:
            p = str(sc["video_file"]).replace("\\", "/")
            f.write(f"file '{p}'\n")

    combined_video = TEMP_DIR / "combined_raw.mp4"
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(combined_video)
    ]
    subprocess.run(concat_cmd, check=True)

    # Final mix with background music
    final_output = OUTPUT_DIR / "vidforge_system_presentation.mp4"
    if MUSIC_FILE.exists():
        print(f"Mixing background soundtrack from {MUSIC_FILE} at 12% volume...")
        mix_cmd = [
            "ffmpeg", "-y",
            "-i", str(combined_video),
            "-stream_loop", "-1",
            "-i", str(MUSIC_FILE),
            "-filter_complex",
            "[1:a]volume=0.12[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "256k",
            str(final_output)
        ]
        subprocess.run(mix_cmd, check=True)
    else:
        shutil.copy(combined_video, final_output)

    print(f"Final presentation video created: {final_output}")

    # Copy to artifacts directory so it can be viewed directly
    if ARTIFACT_DIR and ARTIFACT_DIR.exists():
        dest_artifact = ARTIFACT_DIR / "vidforge_presentation_demo.mp4"
        shutil.copy(final_output, dest_artifact)
        print(f"Copied to artifact directory: {dest_artifact}")

    return final_output

async def main():
    await generate_voiceovers()
    for sc in SCENES:
        render_scene_video(sc)
    out = assemble_final_presentation()
    print("ALL DONE! Output:", out)

if __name__ == "__main__":
    asyncio.run(main())
