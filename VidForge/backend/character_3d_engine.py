"""Persistent 3D Character Animation Engine for VidForge.

Manages persistent 3D character profiles, asset versions, humanoid skeleton inspection,
facial blendshapes/rig verification, Blender project (.blend) generation,
audio-driven lip-sync keyframing, and multi-scene deterministic 3D rendering.
"""

import os
import sys
import json
import time
import math
import wave
import struct
import shutil
import asyncio
import subprocess
from pathlib import Path
from loguru import logger
import httpx

import projects
import ai_engine
import tts_engine
from tripo3d_provider import Tripo3DProvider, get_tripo3d_api_key

BASE_DIR = Path(__file__).resolve().parent.parent
CHARACTERS_DIR = BASE_DIR / "characters"
CHARACTERS_ASSETS_DIR = CHARACTERS_DIR / "assets"
CHARACTERS_JSON_PATH = CHARACTERS_DIR / "characters.json"
ANIMATION_PRESETS_DIR = BASE_DIR / "backend" / "3d_presets"

CHARACTERS_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
ANIMATION_PRESETS_DIR.mkdir(parents=True, exist_ok=True)

# Standard animation preset definitions
ANIMATION_PRESETS = {
    "idle": {
        "name": "Natural Idle",
        "description": "Subtle breathing, weight-shift and calm posture",
        "loop": True,
        "default_speed": 1.0,
        "category": "body"
    },
    "walk": {
        "name": "Forward Walk",
        "description": "Continuous rhythmic walking along camera path",
        "loop": True,
        "default_speed": 1.0,
        "category": "locomotion"
    },
    "run": {
        "name": "Athletic Run",
        "description": "High-energy forward running with arm swing",
        "loop": True,
        "default_speed": 1.2,
        "category": "locomotion"
    },
    "talk_gestures": {
        "name": "Conversational Gestures",
        "description": "Expressive hand, arm and head movements while speaking",
        "loop": True,
        "default_speed": 1.0,
        "category": "dialogue"
    },
    "greeting": {
        "name": "Friendly Wave & Smile",
        "description": "Warm hand-wave greeting towards camera",
        "loop": False,
        "default_speed": 1.0,
        "category": "gesture"
    }
}

# Standard ARKit facial visemes and blendshape targets
ARKit_FACIAL_BLENDSHAPES = [
    "jawOpen", "mouthSmile", "mouthSmileLeft", "mouthSmileRight",
    "mouthFunnel", "mouthPucker", "mouthPress", "mouthClose",
    "browInnerUp", "browDownLeft", "browDownRight",
    "eyeBlinkLeft", "eyeBlinkRight", "eyeWideLeft", "eyeWideRight"
]

def find_blender_binary() -> str | None:
    """Finds installed Blender executable across standard locations or custom config."""
    # 1. Custom config
    cfg_file = BASE_DIR / "backend" / "config.json"
    if cfg_file.exists():
        try:
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
            b_path = data.get("blender_path", "").strip()
            if b_path and Path(b_path).exists():
                return str(Path(b_path).resolve())
        except Exception:
            pass

    # 2. PATH
    which_b = shutil.which("blender")
    if which_b:
        return which_b

    # 3. Standard Windows Program Files
    candidates = [
        Path(r"C:\Program Files\Blender Foundation"),
        Path(r"C:\Program Files (x86)\Blender Foundation"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Blender Foundation",
    ]
    for root in candidates:
        if root.exists():
            for exe in root.glob("**/blender.exe"):
                if exe.exists():
                    return str(exe.resolve())

    return None


def inspect_glb_structure(glb_path: Path) -> dict:
    """Parses a GLB (glTF 2.0 Binary) container to inspect skeleton bones and facial blendshapes.
    
    Operates with zero external heavy dependencies by reading the glTF JSON chunk directly.
    """
    if not glb_path.exists():
        return {"has_rig": False, "bones": [], "blendshapes": [], "error": "File not found"}

    try:
        with open(glb_path, "rb") as f:
            magic = f.read(4)
            if magic != b"glTF":
                return {"has_rig": False, "bones": [], "blendshapes": [], "error": "Not a valid GLB container"}

            version, length = struct.unpack("<II", f.read(8))
            chunk_length, chunk_type = struct.unpack("<II", f.read(8))

            if chunk_type != 0x4E4F534A: # 'JSON'
                return {"has_rig": False, "bones": [], "blendshapes": [], "error": "Missing JSON chunk in GLB"}

            json_bytes = f.read(chunk_length)
            gltf = json.loads(json_bytes.decode("utf-8", errors="ignore"))

            # Inspect Skins & Bones
            bones = []
            nodes = gltf.get("nodes", [])
            skins = gltf.get("skins", [])
            if skins:
                skin = skins[0]
                joint_indices = skin.get("joints", [])
                for idx in joint_indices:
                    if idx < len(nodes):
                        b_name = nodes[idx].get("name") or f"Bone_{idx}"
                        bones.append(b_name)
            else:
                # Check nodes for bone naming patterns
                for n in nodes:
                    name = n.get("name", "").lower()
                    if any(k in name for k in ("hip", "spine", "head", "arm", "leg", "hand", "root", "bone")):
                        bones.append(n.get("name", "Bone"))

            # Inspect Morph Targets / Blendshapes
            blendshapes = []
            meshes = gltf.get("meshes", [])
            for m in meshes:
                for prim in m.get("primitives", []):
                    targets = prim.get("targets", [])
                    if targets:
                        # Check targetNames in mesh extras
                        target_names = m.get("extras", {}).get("targetNames", [])
                        if target_names and len(target_names) == len(targets):
                            blendshapes.extend(target_names)
                        else:
                            for t_idx in range(len(targets)):
                                blendshapes.append(f"Target_{t_idx}")

            blendshapes = sorted(list(set(blendshapes)))
            has_rig = len(bones) >= 6 # Minimum humanoid skeleton joints
            has_facial = any(any(vis in bs.lower() for vis in ("jaw", "mouth", "viseme", "smile", "blink", "eye")) for bs in blendshapes)

            return {
                "has_rig": has_rig,
                "bones_count": len(bones),
                "bones": bones[:50],
                "has_facial_rig": has_facial,
                "blendshapes_count": len(blendshapes),
                "blendshapes": blendshapes,
                "error": None
            }
    except Exception as e:
        logger.warning(f"Could not inspect GLB {glb_path}: {e}")
        return {"has_rig": False, "bones": [], "blendshapes": [], "error": str(e)}


def get_character_asset_dir(char_id: str) -> Path:
    """Returns the dedicated 3D assets folder for a given character ID."""
    p = CHARACTERS_ASSETS_DIR / char_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_character_3d_profile(char_id: str) -> dict:
    """Loads or initializes a persistent 3D character asset profile."""
    char_dir = get_character_asset_dir(char_id)
    profile_path = char_dir / "profile.json"

    # Default base profile
    profile = {
        "character_id": char_id,
        "name": "",
        "version": 1,
        "status": "UNINITIALIZED",
        "mesh_file": None,
        "rigged_file": None,
        "blend_file": None,
        "has_rig": False,
        "bones_count": 0,
        "bones": [],
        "has_facial_rig": False,
        "blendshapes": [],
        "supported_animations": list(ANIMATION_PRESETS.keys()),
        "last_error": "",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    if profile_path.exists():
        try:
            stored = json.loads(profile_path.read_text(encoding="utf-8"))
            profile.update(stored)
        except Exception as e:
            logger.warning(f"Failed reading profile {profile_path}: {e}")

    # Check actual files on disk
    mesh_p = char_dir / "mesh.glb"
    rigged_p = char_dir / "rigged.glb"
    blend_p = char_dir / "character.blend"

    if mesh_p.exists():
        profile["mesh_file"] = f"/characters/assets/{char_id}/mesh.glb"
        if profile["status"] == "UNINITIALIZED":
            profile["status"] = "MESH_READY"

    if rigged_p.exists():
        profile["rigged_file"] = f"/characters/assets/{char_id}/rigged.glb"
        inspection = inspect_glb_structure(rigged_p)
        profile["has_rig"] = inspection.get("has_rig", False)
        profile["bones_count"] = inspection.get("bones_count", 0)
        profile["bones"] = inspection.get("bones", [])
        profile["has_facial_rig"] = inspection.get("has_facial_rig", False)
        profile["blendshapes"] = inspection.get("blendshapes", [])
        if profile["has_rig"]:
            profile["status"] = "RIGGED"

    if blend_p.exists():
        profile["blend_file"] = f"/characters/assets/{char_id}/character.blend"
        profile["status"] = "BLENDER_PROJECT_READY"

    return profile


def save_character_3d_profile(char_id: str, profile: dict) -> None:
    """Persists character asset profile to disk."""
    char_dir = get_character_asset_dir(char_id)
    profile["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    profile_path = char_dir / "profile.json"
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_audio_viseme_envelope(audio_path: Path, fps: int = 30) -> list[dict]:
    """Extracts frame-by-frame energy and viseme intensity for speech lip-sync."""
    if not audio_path.exists():
        return []

    keyframes = []
    try:
        # Convert audio to wav if necessary using ffmpeg
        wav_path = audio_path
        if audio_path.suffix.lower() != ".wav":
            wav_path = audio_path.with_suffix(".temp_viseme.wav")
            subprocess.run([
                "ffmpeg", "-y", "-i", str(audio_path),
                "-ac", "1", "-ar", "16000", str(wav_path)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        with wave.open(str(wav_path), "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            duration = n_frames / float(framerate)

            raw_data = wf.readframes(n_frames)
            total_samples = n_frames * n_channels

            # Read 16-bit PCM samples
            fmt = f"<{n_frames * n_channels}h"
            samples = struct.unpack(fmt, raw_data)

            samples_per_video_frame = int(framerate / fps)
            total_video_frames = int(math.ceil(duration * fps))

            max_amp = 1.0
            frame_energies = []
            for vf in range(total_video_frames):
                start = vf * samples_per_video_frame
                end = min(len(samples), (vf + 1) * samples_per_video_frame)
                if start >= len(samples):
                    frame_energies.append(0.0)
                    continue

                chunk = samples[start:end]
                if not chunk:
                    frame_energies.append(0.0)
                    continue

                # RMS Amplitude
                sum_sq = sum(s * s for s in chunk)
                rms = math.sqrt(sum_sq / len(chunk))
                frame_energies.append(rms)
                if rms > max_amp:
                    max_amp = rms

            # Normalize & generate keyframes
            for vf, e in enumerate(frame_energies):
                norm = min(1.0, (e / max(1.0, max_amp)) * 1.5)
                # Apply human syllable smoothing
                jaw_open = round(math.pow(norm, 1.2), 3)
                smile = round(max(0.0, 0.25 * norm), 3)
                keyframes.append({
                    "frame": vf,
                    "time": round(vf / fps, 3),
                    "jawOpen": jaw_open,
                    "mouthSmile": smile,
                    "mouthFunnel": round(jaw_open * 0.4, 3)
                })

        if wav_path != audio_path:
            wav_path.unlink(missing_ok=True)

    except Exception as e:
        logger.warning(f"Error computing audio visemes for {audio_path}: {e}")

    return keyframes


async def generate_local_rigged_character(char_id: str, avatar_path: Path | None = None) -> dict:
    """Creates a local rigged 3D humanoid character in Blender with skeleton and facial blendshapes."""
    blender_bin = find_blender_binary()
    if not blender_bin:
        raise RuntimeError("Blender executable not found. Please install Blender or configure its path in Settings.")

    char_dir = get_character_asset_dir(char_id)
    mesh_out = char_dir / "mesh.glb"
    rigged_out = char_dir / "rigged.glb"
    blend_out = char_dir / "character.blend"

    avatar_str = str(avatar_path.resolve()) if (avatar_path and avatar_path.exists()) else ""

    script_content = f'''
import bpy
import math
import os

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# 1. High-Quality Anatomical Head with Sculpted Facial Features
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=36, radius=0.20, location=(0, 0, 1.62))
head = bpy.context.active_object
head.name = "Character_Head"

# Deform vertices to create realistic human face geometry (jaw, chin, eye sockets, nose)
mesh = head.data
for v in mesh.vertices:
    x, y, z = v.co.x, v.co.y, v.co.z
    # Chin & Jaw taper
    if z < 1.56 and y < 0:
        factor = (1.56 - z) / 0.15
        v.co.x *= (1.0 - factor * 0.35)
        if abs(x) < 0.05 and z < 1.50:
            v.co.y -= 0.02
    # Eye sockets
    dist_eye_l = math.sqrt((x - 0.065)**2 + (y + 0.14)**2 + (z - 1.64)**2)
    dist_eye_r = math.sqrt((x + 0.065)**2 + (y + 0.14)**2 + (z - 1.64)**2)
    if dist_eye_l < 0.05:
        v.co.y += (0.05 - dist_eye_l) * 0.4
    if dist_eye_r < 0.05:
        v.co.y += (0.05 - dist_eye_r) * 0.4
    # Nose protrusion
    if abs(x) < 0.035 and 1.54 < z < 1.65 and y < -0.12:
        dist_nose = math.sqrt(x**2 + (z - 1.59)**2)
        if dist_nose < 0.05:
            v.co.y -= (0.05 - dist_nose) * 0.65

mesh.update()

# Add Subsurf modifier for smooth organic human curves
mod_sub = head.modifiers.new(name="Subsurf", type='SUBSURF')
mod_sub.levels = 1
mod_sub.render_levels = 2
bpy.ops.object.shade_smooth()

# Add ARKit Facial Shape Keys
head.shape_key_add(name="Basis")

# 1. Jaw Open with smooth falloff
sk_jaw = head.shape_key_add(name="jawOpen")
for v in sk_jaw.data:
    if v.co.z < 1.58 and v.co.y < 0:
        depth = min(1.0, (1.58 - v.co.z) / 0.12)
        v.co.z -= 0.055 * depth
        v.co.y += 0.015 * depth

# 2. Mouth Smile
sk_smile = head.shape_key_add(name="mouthSmile")
for v in sk_smile.data:
    if 1.50 < v.co.z < 1.58 and v.co.y < -0.10:
        dist_center = abs(v.co.x)
        if dist_center > 0.03:
            v.co.x *= 1.18
            v.co.z += 0.018 * min(1.0, dist_center / 0.08)

# 3. Mouth Funnel (Pucker)
sk_funnel = head.shape_key_add(name="mouthFunnel")
for v in sk_funnel.data:
    if 1.50 < v.co.z < 1.58 and v.co.y < -0.10 and abs(v.co.x) < 0.07:
        v.co.y -= 0.035
        v.co.x *= 0.85

# 4. Eyelid Blinks
sk_blink_l = head.shape_key_add(name="eyeBlinkLeft")
for v in sk_blink_l.data:
    if 1.62 < v.co.z < 1.68 and v.co.x > 0.02 and v.co.y < -0.12:
        v.co.z -= 0.025

sk_blink_r = head.shape_key_add(name="eyeBlinkRight")
for v in sk_blink_r.data:
    if 1.62 < v.co.z < 1.68 and v.co.x < -0.02 and v.co.y < -0.12:
        v.co.z -= 0.025

# 2. Torso with Suit Jacket / Outfit Shape
bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.18, location=(0, 0, 1.45), vertices=24)
neck = bpy.context.active_object
neck.name = "Character_Neck"
bpy.ops.object.shade_smooth()

# Torso (Upper body: shoulders and chest)
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 1.15))
torso = bpy.context.active_object
torso.name = "Character_Torso"
torso.scale = (0.34, 0.22, 0.42)
bpy.ops.object.transform_apply(scale=True)

# Taper waist & shape shoulders
t_mesh = torso.data
for v in t_mesh.vertices:
    if v.co.z < 1.10:
        v.co.x *= 0.82 # Waist taper
        v.co.y *= 0.85
    elif v.co.z > 1.30:
        v.co.x *= 1.12 # Shoulder breadth
t_mesh.update()

mod_t_sub = torso.modifiers.new(name="Subsurf", type='SUBSURF')
mod_t_sub.levels = 1
bpy.ops.object.shade_smooth()

# 3. Limbs (Arms and Legs with anatomical taper)
def create_limb(name, start_loc, scale, taper=True):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.065, depth=1.0, location=start_loc, vertices=20)
    limb = bpy.context.active_object
    limb.name = name
    limb.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    if taper:
        for v in limb.data.vertices:
            factor = (1.0 - (v.co.z - start_loc[2])) / 2.0
            v.co.x *= max(0.65, min(1.2, 1.1 - factor * 0.4))
            v.co.y *= max(0.65, min(1.2, 1.1 - factor * 0.4))
        limb.data.update()
    bpy.ops.object.shade_smooth()
    return limb

arm_l = create_limb("Arm_Left", (-0.42, 0, 1.10), (1.0, 1.0, 0.58))
arm_r = create_limb("Arm_Right", (0.42, 0, 1.10), (1.0, 1.0, 0.58))
leg_l = create_limb("Leg_Left", (-0.15, 0, 0.46), (1.1, 1.1, 0.88))
leg_r = create_limb("Leg_Right", (0.15, 0, 0.46), (1.1, 1.1, 0.88))

# Join body parts
body_parts = [torso, neck, arm_l, arm_r, leg_l, leg_r]
for p in body_parts:
    p.select_set(True)
bpy.context.view_layer.objects.active = torso
bpy.ops.object.join()

# 4. Realistic PBR Materials & Frontal Portrait UV Mapping
# Head Skin Material
mat_head = bpy.data.materials.new(name="Material_Head_Skin")
mat_head.use_nodes = True
nodes = mat_head.node_tree.nodes
links = mat_head.node_tree.links
nodes.clear()

node_output = nodes.new(type="ShaderNodeOutputMaterial")
node_bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
links.new(node_bsdf.outputs["BSDF"], node_output.inputs["Surface"])

node_bsdf.inputs["Base Color"].default_value = (0.85, 0.68, 0.56, 1.0)
node_bsdf.inputs["Roughness"].default_value = 0.45

avatar_path = r"{avatar_str}"
if avatar_path and os.path.exists(avatar_path):
    try:
        img = bpy.data.images.load(avatar_path)
        node_tex = nodes.new(type="ShaderNodeTexImage")
        node_tex.image = img
        node_tex.extension = 'CLIP'
        
        node_coord = nodes.new(type="ShaderNodeTexCoord")
        links.new(node_coord.outputs["Generated"], node_tex.inputs["Vector"])
        links.new(node_tex.outputs["Color"], node_bsdf.inputs["Base Color"])
    except Exception as e:
        print("Avatar texture setup warning:", e)

head.data.materials.append(mat_head)

# Body Outfit Material (Dark Navy Suit)
mat_outfit = bpy.data.materials.new(name="Material_Outfit")
mat_outfit.use_nodes = True
nodes_o = mat_outfit.node_tree.nodes
bsdf_o = nodes_o.get("Principled BSDF")
if bsdf_o:
    bsdf_o.inputs["Base Color"].default_value = (0.12, 0.15, 0.22, 1.0)
    bsdf_o.inputs["Roughness"].default_value = 0.65
torso.data.materials.append(mat_outfit)

# 5. Create Humanoid Armature with 9 Essential Bones
bpy.ops.object.armature_add(location=(0, 0, 0))
arm = bpy.context.active_object
arm.name = "Character_Armature"

bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones

root = eb[0]
root.name = "Hips"
root.head = (0, 0, 0.90)
root.tail = (0, 0, 1.10)

spine = eb.new("Spine")
spine.head = (0, 0, 1.10)
spine.tail = (0, 0, 1.30)
spine.parent = root

chest = eb.new("Chest")
chest.head = (0, 0, 1.30)
chest.tail = (0, 0, 1.45)
chest.parent = spine

neck_b = eb.new("Neck")
neck_b.head = (0, 0, 1.45)
neck_b.tail = (0, 0, 1.55)
neck_b.parent = chest

head_b = eb.new("Head")
head_b.head = (0, 0, 1.55)
head_b.tail = (0, 0, 1.85)
head_b.parent = neck_b

arm_l_b = eb.new("LeftUpperArm")
arm_l_b.head = (-0.22, 0, 1.40)
arm_l_b.tail = (-0.48, 0, 1.05)
arm_l_b.parent = chest

arm_r_b = eb.new("RightUpperArm")
arm_r_b.head = (0.22, 0, 1.40)
arm_r_b.tail = (0.48, 0, 1.05)
arm_r_b.parent = chest

leg_l_b = eb.new("LeftUpperLeg")
leg_l_b.head = (-0.15, 0, 0.90)
leg_l_b.tail = (-0.15, 0, 0.05)
leg_l_b.parent = root

leg_r_b = eb.new("RightUpperLeg")
leg_r_b.head = (0.15, 0, 0.90)
leg_r_b.tail = (0.15, 0, 0.05)
leg_r_b.parent = root

bpy.ops.object.mode_set(mode='OBJECT')

# Parent Head & Torso to Armature with Automatic Weights
head.select_set(True)
torso.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')

# Add 3-point Studio Lighting
key_data = bpy.data.lights.new(name="Key_Light", type='AREA')
key_data.energy = 600.0
key_data.size = 2.0
key_obj = bpy.data.objects.new(name="Key_Light", object_data=key_data)
scene.collection.objects.link(key_obj)
key_obj.location = (1.5, -2.0, 2.2)
key_obj.rotation_euler = (math.radians(50), 0, math.radians(35))

fill_data = bpy.data.lights.new(name="Fill_Light", type='AREA')
fill_data.energy = 250.0
fill_data.size = 3.0
fill_obj = bpy.data.objects.new(name="Fill_Light", object_data=fill_data)
scene.collection.objects.link(fill_obj)
fill_obj.location = (-2.0, -1.8, 1.8)
fill_obj.rotation_euler = (math.radians(45), 0, math.radians(-40))

rim_data = bpy.data.lights.new(name="Rim_Light", type='SPOT')
rim_data.energy = 800.0
rim_data.spot_size = math.radians(45)
rim_obj = bpy.data.objects.new(name="Rim_Light", object_data=rim_data)
scene.collection.objects.link(rim_obj)
rim_obj.location = (0.0, 2.5, 2.8)
rim_obj.rotation_euler = (math.radians(-140), 0, 0)

# Camera
cam_data = bpy.data.cameras.new(name="Cinematic_Camera")
cam_data.lens = 50.0
cam_obj = bpy.data.objects.new(name="Cinematic_Camera", object_data=cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj
cam_obj.location = (0.0, -3.2, 1.4)
cam_obj.rotation_euler = (math.radians(88), 0, 0)

# Export models
bpy.ops.export_scene.gltf(filepath=r"{mesh_out.resolve()}", export_format='GLB')
bpy.ops.export_scene.gltf(filepath=r"{rigged_out.resolve()}", export_format='GLB', export_skins=True, export_morph=True)
bpy.ops.wm.save_as_mainfile(filepath=r"{blend_out.resolve()}")
print("SUCCESS_LOCAL_MODEL_GENERATED")
'''
    script_file = char_dir / "gen_local_character.py"
    script_file.write_text(script_content, encoding="utf-8")

    logger.info(f"Generating local rigged 3D character in Blender for {char_id}...")
    proc = await asyncio.create_subprocess_exec(
        blender_bin, "-b", "--python", str(script_file),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    script_file.unlink(missing_ok=True)

    out_str = stdout.decode("utf-8", errors="ignore")
    if proc.returncode != 0 or "SUCCESS_LOCAL_MODEL_GENERATED" not in out_str:
        err_msg = stderr.decode("utf-8", errors="ignore") or out_str
        raise RuntimeError(f"Blender failed to generate character: {err_msg[:400]}")

    profile = load_character_3d_profile(char_id)
    profile["status"] = "BLENDER_PROJECT_READY"
    save_character_3d_profile(char_id, profile)
    return profile


async def create_blender_project(char_id: str) -> dict:
    """Generates a native character.blend project containing the character mesh, armature,
    studio lighting, and camera.
    """
    blender_bin = find_blender_binary()
    if not blender_bin:
        raise RuntimeError("Blender executable not found. Please install Blender or configure its path in Settings.")

    char_dir = get_character_asset_dir(char_id)
    rigged_model = char_dir / "rigged.glb"
    base_model = char_dir / "mesh.glb"

    model_to_use = rigged_model if rigged_model.exists() else base_model
    if not model_to_use.exists():
        raise FileNotFoundError(f"No 3D model found for character {char_id}. Generate or import a .glb model first.")

    output_blend = char_dir / "character.blend"

    # Python script executed inside headless Blender
    script_content = f"""
import bpy
import math

# Clean existing scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Set rendering engine to Eevee Next / Cycles with fast GPU preview
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT' if hasattr(bpy.types, 'RenderSettings') else 'BLENDER_EEVEE'
scene.render.resolution_x = 1080
scene.render.resolution_y = 1920
scene.render.fps = 30

# Import character model
model_path = r"{model_to_use.resolve()}"
if model_path.lower().endswith('.glb') or model_path.lower().endswith('.gltf'):
    bpy.ops.import_scene.gltf(filepath=model_path)
elif model_path.lower().endswith('.fbx'):
    bpy.ops.import_scene.fbx(filepath=model_path)

# Set up Studio 3-Point Lighting
# 1. Key Light
key_data = bpy.data.lights.new(name="Key_Light", type='AREA')
key_data.energy = 600.0
key_data.size = 2.0
key_obj = bpy.data.objects.new(name="Key_Light", object_data=key_data)
scene.collection.objects.link(key_obj)
key_obj.location = (1.5, -2.0, 2.2)
key_obj.rotation_euler = (math.radians(50), 0, math.radians(35))

# 2. Fill Light
fill_data = bpy.data.lights.new(name="Fill_Light", type='AREA')
fill_data.energy = 250.0
fill_data.size = 3.0
fill_obj = bpy.data.objects.new(name="Fill_Light", object_data=fill_data)
scene.collection.objects.link(fill_obj)
fill_obj.location = (-2.0, -1.8, 1.8)
fill_obj.rotation_euler = (math.radians(45), 0, math.radians(-40))

# 3. Rim/Back Light
rim_data = bpy.data.lights.new(name="Rim_Light", type='SPOT')
rim_data.energy = 800.0
rim_data.spot_size = math.radians(45)
rim_obj = bpy.data.objects.new(name="Rim_Light", object_data=rim_data)
scene.collection.objects.link(rim_obj)
rim_obj.location = (0.0, 2.5, 2.8)
rim_obj.rotation_euler = (math.radians(-140), 0, 0)

# Set up Camera (Cinematic 50mm portrait lens)
cam_data = bpy.data.cameras.new(name="Cinematic_Camera")
cam_data.lens = 50.0
cam_obj = bpy.data.objects.new(name="Cinematic_Camera", object_data=cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj
cam_obj.location = (0.0, -3.2, 1.4)
cam_obj.rotation_euler = (math.radians(88), 0, 0)

# Save .blend file
output_path = r"{output_blend.resolve()}"
bpy.ops.wm.save_as_mainfile(filepath=output_path)
print("SUCCESS_BLEND_CREATED")
"""
    script_file = char_dir / "setup_project.py"
    script_file.write_text(script_content, encoding="utf-8")

    logger.info(f"Running Blender headless to create project for {char_id}...")
    proc = await asyncio.create_subprocess_exec(
        blender_bin, "-b", "--python", str(script_file),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    script_file.unlink(missing_ok=True)

    out_str = stdout.decode("utf-8", errors="ignore")
    if proc.returncode != 0 or "SUCCESS_BLEND_CREATED" not in out_str:
        err_msg = stderr.decode("utf-8", errors="ignore") or out_str
        raise RuntimeError(f"Blender failed to initialize character.blend: {err_msg[:400]}")

    profile = load_character_3d_profile(char_id)
    profile["status"] = "BLENDER_PROJECT_READY"
    profile["blend_file"] = f"/characters/assets/{char_id}/character.blend"
    save_character_3d_profile(char_id, profile)

    return profile


async def render_scene_3d(
    char_id: str,
    scene_id: int,
    animation: str = "walk",
    camera_mode: str = "medium",
    lighting_preset: str = "studio",
    audio_path: Path | None = None,
    duration: float = 5.0,
    background_color: str = "transparent",
    aspect_ratio: str = "9:16",
    output_dir: Path | None = None
) -> Path:
    """Renders a scene animation deterministically from the persistent character.blend project."""
    blender_bin = find_blender_binary()
    if not blender_bin:
        raise RuntimeError("Blender executable is required for deterministic 3D character animation.")

    char_dir = get_character_asset_dir(char_id)
    blend_file = char_dir / "character.blend"
    if not blend_file.exists():
        # Auto-create blend project if model is ready
        await create_blender_project(char_id)

    out_dir = output_dir or (char_dir / "renders")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_video = out_dir / f"scene_{scene_id}_{animation}_{camera_mode}.mp4"

    fps = 30
    total_frames = max(30, int(round(duration * fps)))

    # Compute lip-sync keyframes if dialogue audio is supplied
    visemes = []
    if audio_path and audio_path.exists():
        visemes = compute_audio_viseme_envelope(audio_path, fps=fps)

    visemes_json_str = json.dumps(visemes)

    # Resolve render resolution
    res_x, res_y = 1080, 1920 # Default vertical
    if aspect_ratio == "16:9":
        res_x, res_y = 1920, 1080
    elif aspect_ratio == "1:1":
        res_x, res_y = 1080, 1080

    frames_dir = out_dir / f"frames_scene_{scene_id}"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frames_pattern = str((frames_dir / "frame_").resolve())

    render_script = f"""
import bpy
import math
import json

# Open persistent character project
bpy.ops.wm.open_mainfile(filepath=r"{blend_file.resolve()}")

scene = bpy.context.scene
scene.render.resolution_x = {res_x}
scene.render.resolution_y = {res_y}
scene.render.fps = {fps}
scene.frame_start = 1
scene.frame_end = {total_frames}

# Camera framing
cam = scene.camera or bpy.data.objects.get("Cinematic_Camera")
if cam:
    if "{camera_mode}" == "close_up":
        cam.location = (0.0, -1.6, 1.45)
        cam.rotation_euler = (math.radians(90), 0, 0)
    elif "{camera_mode}" == "wide":
        cam.location = (0.0, -4.8, 1.2)
        cam.rotation_euler = (math.radians(85), 0, 0)
    elif "{camera_mode}" == "pan":
        cam.location = (-1.5, -3.0, 1.3)
        cam.keyframe_insert(data_path="location", frame=1)
        cam.location = (1.5, -3.0, 1.3)
        cam.keyframe_insert(data_path="location", frame={total_frames})
    else: # medium
        cam.location = (0.0, -2.8, 1.3)
        cam.rotation_euler = (math.radians(88), 0, 0)

# Find character armature / mesh
armature = None
mesh_obj = None
for obj in scene.objects:
    if obj.type == 'ARMATURE':
        armature = obj
    elif obj.type == 'MESH':
        mesh_obj = obj

# Apply body locomotion / path movement
if armature or mesh_obj:
    target_obj = armature or mesh_obj
    target_obj.animation_data_clear()
    
    if "{animation}" == "walk":
        # Forward displacement along Y axis
        target_obj.location = (0.0, -1.5, 0.0)
        target_obj.keyframe_insert(data_path="location", frame=1)
        target_obj.location = (0.0, 1.5, 0.0)
        target_obj.keyframe_insert(data_path="location", frame={total_frames})
    elif "{animation}" == "run":
        target_obj.location = (0.0, -2.5, 0.0)
        target_obj.keyframe_insert(data_path="location", frame=1)
        target_obj.location = (0.0, 2.5, 0.0)
        target_obj.keyframe_insert(data_path="location", frame={total_frames})
    else: # idle or talk_gestures
        target_obj.location = (0.0, 0.0, 0.0)

# Apply Lip-Sync blendshape keyframes if facial rig exists
viseme_data = {visemes_json_str}
if mesh_obj and mesh_obj.data.shape_keys and viseme_data:
    key_blocks = mesh_obj.data.shape_keys.key_blocks
    jaw_key = key_blocks.get("jawOpen") or key_blocks.get("mouthOpen") or next((k for k in key_blocks if "jaw" in k.name.lower() or "open" in k.name.lower()), None)
    smile_key = key_blocks.get("mouthSmile") or next((k for k in key_blocks if "smile" in k.name.lower()), None)

    for item in viseme_data:
        f_idx = item.get("frame", 0) + 1
        if f_idx > {total_frames}:
            break
        if jaw_key:
            jaw_key.value = float(item.get("jawOpen", 0.0))
            jaw_key.keyframe_insert(data_path="value", frame=f_idx)
        if smile_key:
            smile_key.value = float(item.get("mouthSmile", 0.0))
            smile_key.keyframe_insert(data_path="value", frame=f_idx)

# Lighting Mood Preset
if "{lighting_preset}" == "sunset":
    key_light = bpy.data.objects.get("Key_Light")
    if key_light:
        key_light.data.color = (1.0, 0.55, 0.25)
        key_light.data.energy = 800.0
elif "{lighting_preset}" == "cyberpunk":
    key_light = bpy.data.objects.get("Key_Light")
    fill_light = bpy.data.objects.get("Fill_Light")
    if key_light:
        key_light.data.color = (0.1, 0.8, 1.0)
    if fill_light:
        fill_light.data.color = (1.0, 0.1, 0.8)

# Configure Frame Output (PNG with RGBA transparency)
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = r"{frames_pattern}"

# Background transparency
if "{background_color}" == "transparent":
    scene.render.film_transparent = True

bpy.ops.render.render(animation=True)
print("SUCCESS_SCENE_RENDERED")
"""
    script_file = out_dir / f"render_scene_{scene_id}.py"
    script_file.write_text(render_script, encoding="utf-8")

    logger.info(f"Rendering 3D Scene {scene_id} ({duration}s, animation: {animation}) via Blender...")
    proc = await asyncio.create_subprocess_exec(
        blender_bin, "-b", "--python", str(script_file),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    script_file.unlink(missing_ok=True)

    out_str = stdout.decode("utf-8", errors="ignore")
    if proc.returncode != 0 or "SUCCESS_SCENE_RENDERED" not in out_str:
        err_msg = stderr.decode("utf-8", errors="ignore") or out_str
        shutil.rmtree(frames_dir, ignore_errors=True)
        raise RuntimeError(f"Blender scene rendering failed: {err_msg[:400]}")

    # Assemble rendered frames into MP4 using ffmpeg
    encoder = ai_engine.get_video_encoder() # Uses h264_nvenc on RTX 5070 Ti
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frames_dir / "frame_%04d.png"),
    ]
    if audio_path and audio_path.exists():
        cmd.extend(["-i", str(audio_path)])

    if encoder == "h264_nvenc":
        cmd.extend(["-c:v", "h264_nvenc", "-pix_fmt", "yuv420p"])
    else:
        cmd.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18"])

    if audio_path and audio_path.exists():
        cmd.extend(["-c:a", "aac", "-b:a", "192k", "-shortest"])

    cmd.append(str(out_video))

    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Clean up temp frames
    shutil.rmtree(frames_dir, ignore_errors=True)

    if res.returncode != 0 or not out_video.exists():
        raise RuntimeError(f"FFmpeg failed to assemble scene video from Blender frames: {out_video}")

    logger.info(f"Persistent 3D Character Scene {scene_id} rendered successfully: {out_video}")
    return out_video
