
import bpy
import math
import json

# Open persistent character project
bpy.ops.wm.open_mainfile(filepath=r"D:\AI\VidForge\characters\assets\char_38f853ba\character.blend")

scene = bpy.context.scene
scene.render.resolution_x = 1080
scene.render.resolution_y = 1920
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 150

# Camera framing
cam = scene.camera or bpy.data.objects.get("Cinematic_Camera")
if cam:
    if "medium" == "close_up":
        cam.location = (0.0, -1.6, 1.45)
        cam.rotation_euler = (math.radians(90), 0, 0)
    elif "medium" == "wide":
        cam.location = (0.0, -4.8, 1.2)
        cam.rotation_euler = (math.radians(85), 0, 0)
    elif "medium" == "pan":
        cam.location = (-1.5, -3.0, 1.3)
        cam.keyframe_insert(data_path="location", frame=1)
        cam.location = (1.5, -3.0, 1.3)
        cam.keyframe_insert(data_path="location", frame=150)
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
    
    if "walk" == "walk":
        # Forward displacement along Y axis
        target_obj.location = (0.0, -1.5, 0.0)
        target_obj.keyframe_insert(data_path="location", frame=1)
        target_obj.location = (0.0, 1.5, 0.0)
        target_obj.keyframe_insert(data_path="location", frame=150)
    elif "walk" == "run":
        target_obj.location = (0.0, -2.5, 0.0)
        target_obj.keyframe_insert(data_path="location", frame=1)
        target_obj.location = (0.0, 2.5, 0.0)
        target_obj.keyframe_insert(data_path="location", frame=150)
    else: # idle or talk_gestures
        target_obj.location = (0.0, 0.0, 0.0)

# Apply Lip-Sync blendshape keyframes if facial rig exists
viseme_data = [{"frame": 0, "time": 0.0, "jawOpen": 0.001, "mouthSmile": 0.001, "mouthFunnel": 0.0}, {"frame": 1, "time": 0.033, "jawOpen": 0.001, "mouthSmile": 0.001, "mouthFunnel": 0.0}, {"frame": 2, "time": 0.067, "jawOpen": 0.001, "mouthSmile": 0.001, "mouthFunnel": 0.0}, {"frame": 3, "time": 0.1, "jawOpen": 0.001, "mouthSmile": 0.001, "mouthFunnel": 0.0}, {"frame": 4, "time": 0.133, "jawOpen": 0.001, "mouthSmile": 0.001, "mouthFunnel": 0.0}, {"frame": 5, "time": 0.167, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 6, "time": 0.2, "jawOpen": 0.001, "mouthSmile": 0.001, "mouthFunnel": 0.0}, {"frame": 7, "time": 0.233, "jawOpen": 0.016, "mouthSmile": 0.008, "mouthFunnel": 0.006}, {"frame": 8, "time": 0.267, "jawOpen": 0.366, "mouthSmile": 0.108, "mouthFunnel": 0.146}, {"frame": 9, "time": 0.3, "jawOpen": 0.88, "mouthSmile": 0.225, "mouthFunnel": 0.352}, {"frame": 10, "time": 0.333, "jawOpen": 0.712, "mouthSmile": 0.188, "mouthFunnel": 0.285}, {"frame": 11, "time": 0.367, "jawOpen": 0.847, "mouthSmile": 0.218, "mouthFunnel": 0.339}, {"frame": 12, "time": 0.4, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 13, "time": 0.433, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 14, "time": 0.467, "jawOpen": 0.986, "mouthSmile": 0.247, "mouthFunnel": 0.394}, {"frame": 15, "time": 0.5, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 16, "time": 0.533, "jawOpen": 0.711, "mouthSmile": 0.188, "mouthFunnel": 0.284}, {"frame": 17, "time": 0.567, "jawOpen": 0.318, "mouthSmile": 0.096, "mouthFunnel": 0.127}, {"frame": 18, "time": 0.6, "jawOpen": 0.139, "mouthSmile": 0.048, "mouthFunnel": 0.056}, {"frame": 19, "time": 0.633, "jawOpen": 0.053, "mouthSmile": 0.022, "mouthFunnel": 0.021}, {"frame": 20, "time": 0.667, "jawOpen": 0.004, "mouthSmile": 0.002, "mouthFunnel": 0.002}, {"frame": 21, "time": 0.7, "jawOpen": 0.001, "mouthSmile": 0.001, "mouthFunnel": 0.0}, {"frame": 22, "time": 0.733, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 23, "time": 0.767, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 24, "time": 0.8, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 25, "time": 0.833, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 26, "time": 0.867, "jawOpen": 0.001, "mouthSmile": 0.001, "mouthFunnel": 0.0}, {"frame": 27, "time": 0.9, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 28, "time": 0.933, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 29, "time": 0.967, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 30, "time": 1.0, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 31, "time": 1.033, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 32, "time": 1.067, "jawOpen": 0.001, "mouthSmile": 0.001, "mouthFunnel": 0.0}, {"frame": 33, "time": 1.1, "jawOpen": 0.006, "mouthSmile": 0.004, "mouthFunnel": 0.002}, {"frame": 34, "time": 1.133, "jawOpen": 0.001, "mouthSmile": 0.001, "mouthFunnel": 0.0}, {"frame": 35, "time": 1.167, "jawOpen": 0.002, "mouthSmile": 0.001, "mouthFunnel": 0.001}, {"frame": 36, "time": 1.2, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 37, "time": 1.233, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 38, "time": 1.267, "jawOpen": 0.005, "mouthSmile": 0.003, "mouthFunnel": 0.002}, {"frame": 39, "time": 1.3, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 40, "time": 1.333, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 41, "time": 1.367, "jawOpen": 0.534, "mouthSmile": 0.148, "mouthFunnel": 0.214}, {"frame": 42, "time": 1.4, "jawOpen": 0.821, "mouthSmile": 0.212, "mouthFunnel": 0.328}, {"frame": 43, "time": 1.433, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 44, "time": 1.467, "jawOpen": 0.928, "mouthSmile": 0.235, "mouthFunnel": 0.371}, {"frame": 45, "time": 1.5, "jawOpen": 0.844, "mouthSmile": 0.217, "mouthFunnel": 0.338}, {"frame": 46, "time": 1.533, "jawOpen": 0.665, "mouthSmile": 0.178, "mouthFunnel": 0.266}, {"frame": 47, "time": 1.567, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 48, "time": 1.6, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 49, "time": 1.633, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 50, "time": 1.667, "jawOpen": 0.232, "mouthSmile": 0.074, "mouthFunnel": 0.093}, {"frame": 51, "time": 1.7, "jawOpen": 0.576, "mouthSmile": 0.158, "mouthFunnel": 0.23}, {"frame": 52, "time": 1.733, "jawOpen": 0.734, "mouthSmile": 0.193, "mouthFunnel": 0.294}, {"frame": 53, "time": 1.767, "jawOpen": 0.732, "mouthSmile": 0.193, "mouthFunnel": 0.293}, {"frame": 54, "time": 1.8, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 55, "time": 1.833, "jawOpen": 0.907, "mouthSmile": 0.23, "mouthFunnel": 0.363}, {"frame": 56, "time": 1.867, "jawOpen": 0.629, "mouthSmile": 0.17, "mouthFunnel": 0.252}, {"frame": 57, "time": 1.9, "jawOpen": 0.277, "mouthSmile": 0.086, "mouthFunnel": 0.111}, {"frame": 58, "time": 1.933, "jawOpen": 0.167, "mouthSmile": 0.056, "mouthFunnel": 0.067}, {"frame": 59, "time": 1.967, "jawOpen": 0.147, "mouthSmile": 0.051, "mouthFunnel": 0.059}, {"frame": 60, "time": 2.0, "jawOpen": 0.078, "mouthSmile": 0.03, "mouthFunnel": 0.031}, {"frame": 61, "time": 2.033, "jawOpen": 0.052, "mouthSmile": 0.021, "mouthFunnel": 0.021}, {"frame": 62, "time": 2.067, "jawOpen": 0.002, "mouthSmile": 0.001, "mouthFunnel": 0.001}, {"frame": 63, "time": 2.1, "jawOpen": 0.001, "mouthSmile": 0.001, "mouthFunnel": 0.0}, {"frame": 64, "time": 2.133, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 65, "time": 2.167, "jawOpen": 0.001, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 66, "time": 2.2, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 67, "time": 2.233, "jawOpen": 0.001, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 68, "time": 2.267, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 69, "time": 2.3, "jawOpen": 0.001, "mouthSmile": 0.001, "mouthFunnel": 0.0}, {"frame": 70, "time": 2.333, "jawOpen": 0.002, "mouthSmile": 0.001, "mouthFunnel": 0.001}, {"frame": 71, "time": 2.367, "jawOpen": 0.004, "mouthSmile": 0.003, "mouthFunnel": 0.002}, {"frame": 72, "time": 2.4, "jawOpen": 0.004, "mouthSmile": 0.002, "mouthFunnel": 0.002}, {"frame": 73, "time": 2.433, "jawOpen": 0.002, "mouthSmile": 0.001, "mouthFunnel": 0.001}, {"frame": 74, "time": 2.467, "jawOpen": 0.003, "mouthSmile": 0.002, "mouthFunnel": 0.001}, {"frame": 75, "time": 2.5, "jawOpen": 0.111, "mouthSmile": 0.04, "mouthFunnel": 0.044}, {"frame": 76, "time": 2.533, "jawOpen": 0.173, "mouthSmile": 0.058, "mouthFunnel": 0.069}, {"frame": 77, "time": 2.567, "jawOpen": 0.125, "mouthSmile": 0.044, "mouthFunnel": 0.05}, {"frame": 78, "time": 2.6, "jawOpen": 0.344, "mouthSmile": 0.103, "mouthFunnel": 0.138}, {"frame": 79, "time": 2.633, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 80, "time": 2.667, "jawOpen": 0.886, "mouthSmile": 0.226, "mouthFunnel": 0.354}, {"frame": 81, "time": 2.7, "jawOpen": 0.727, "mouthSmile": 0.192, "mouthFunnel": 0.291}, {"frame": 82, "time": 2.733, "jawOpen": 0.09, "mouthSmile": 0.034, "mouthFunnel": 0.036}, {"frame": 83, "time": 2.767, "jawOpen": 0.054, "mouthSmile": 0.022, "mouthFunnel": 0.022}, {"frame": 84, "time": 2.8, "jawOpen": 0.007, "mouthSmile": 0.004, "mouthFunnel": 0.003}, {"frame": 85, "time": 2.833, "jawOpen": 0.03, "mouthSmile": 0.013, "mouthFunnel": 0.012}, {"frame": 86, "time": 2.867, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 87, "time": 2.9, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 88, "time": 2.933, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 89, "time": 2.967, "jawOpen": 0.318, "mouthSmile": 0.096, "mouthFunnel": 0.127}, {"frame": 90, "time": 3.0, "jawOpen": 0.186, "mouthSmile": 0.061, "mouthFunnel": 0.074}, {"frame": 91, "time": 3.033, "jawOpen": 0.42, "mouthSmile": 0.121, "mouthFunnel": 0.168}, {"frame": 92, "time": 3.067, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 93, "time": 3.1, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 94, "time": 3.133, "jawOpen": 0.545, "mouthSmile": 0.151, "mouthFunnel": 0.218}, {"frame": 95, "time": 3.167, "jawOpen": 0.333, "mouthSmile": 0.1, "mouthFunnel": 0.133}, {"frame": 96, "time": 3.2, "jawOpen": 0.213, "mouthSmile": 0.069, "mouthFunnel": 0.085}, {"frame": 97, "time": 3.233, "jawOpen": 0.916, "mouthSmile": 0.232, "mouthFunnel": 0.366}, {"frame": 98, "time": 3.267, "jawOpen": 0.236, "mouthSmile": 0.075, "mouthFunnel": 0.094}, {"frame": 99, "time": 3.3, "jawOpen": 0.006, "mouthSmile": 0.004, "mouthFunnel": 0.002}, {"frame": 100, "time": 3.333, "jawOpen": 0.021, "mouthSmile": 0.01, "mouthFunnel": 0.008}, {"frame": 101, "time": 3.367, "jawOpen": 0.931, "mouthSmile": 0.236, "mouthFunnel": 0.372}, {"frame": 102, "time": 3.4, "jawOpen": 0.918, "mouthSmile": 0.233, "mouthFunnel": 0.367}, {"frame": 103, "time": 3.433, "jawOpen": 0.236, "mouthSmile": 0.075, "mouthFunnel": 0.094}, {"frame": 104, "time": 3.467, "jawOpen": 0.209, "mouthSmile": 0.068, "mouthFunnel": 0.084}, {"frame": 105, "time": 3.5, "jawOpen": 0.039, "mouthSmile": 0.017, "mouthFunnel": 0.016}, {"frame": 106, "time": 3.533, "jawOpen": 0.002, "mouthSmile": 0.002, "mouthFunnel": 0.001}, {"frame": 107, "time": 3.567, "jawOpen": 0.067, "mouthSmile": 0.026, "mouthFunnel": 0.027}, {"frame": 108, "time": 3.6, "jawOpen": 0.159, "mouthSmile": 0.054, "mouthFunnel": 0.064}, {"frame": 109, "time": 3.633, "jawOpen": 0.904, "mouthSmile": 0.23, "mouthFunnel": 0.362}, {"frame": 110, "time": 3.667, "jawOpen": 0.938, "mouthSmile": 0.237, "mouthFunnel": 0.375}, {"frame": 111, "time": 3.7, "jawOpen": 0.906, "mouthSmile": 0.23, "mouthFunnel": 0.362}, {"frame": 112, "time": 3.733, "jawOpen": 0.918, "mouthSmile": 0.233, "mouthFunnel": 0.367}, {"frame": 113, "time": 3.767, "jawOpen": 0.493, "mouthSmile": 0.139, "mouthFunnel": 0.197}, {"frame": 114, "time": 3.8, "jawOpen": 0.528, "mouthSmile": 0.147, "mouthFunnel": 0.211}, {"frame": 115, "time": 3.833, "jawOpen": 0.52, "mouthSmile": 0.145, "mouthFunnel": 0.208}, {"frame": 116, "time": 3.867, "jawOpen": 0.008, "mouthSmile": 0.004, "mouthFunnel": 0.003}, {"frame": 117, "time": 3.9, "jawOpen": 0.002, "mouthSmile": 0.002, "mouthFunnel": 0.001}, {"frame": 118, "time": 3.933, "jawOpen": 0.043, "mouthSmile": 0.018, "mouthFunnel": 0.017}, {"frame": 119, "time": 3.967, "jawOpen": 0.071, "mouthSmile": 0.027, "mouthFunnel": 0.028}, {"frame": 120, "time": 4.0, "jawOpen": 0.62, "mouthSmile": 0.168, "mouthFunnel": 0.248}, {"frame": 121, "time": 4.033, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 122, "time": 4.067, "jawOpen": 0.88, "mouthSmile": 0.225, "mouthFunnel": 0.352}, {"frame": 123, "time": 4.1, "jawOpen": 0.203, "mouthSmile": 0.066, "mouthFunnel": 0.081}, {"frame": 124, "time": 4.133, "jawOpen": 0.851, "mouthSmile": 0.219, "mouthFunnel": 0.34}, {"frame": 125, "time": 4.167, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 126, "time": 4.2, "jawOpen": 0.48, "mouthSmile": 0.136, "mouthFunnel": 0.192}, {"frame": 127, "time": 4.233, "jawOpen": 0.019, "mouthSmile": 0.009, "mouthFunnel": 0.008}, {"frame": 128, "time": 4.267, "jawOpen": 0.436, "mouthSmile": 0.125, "mouthFunnel": 0.174}, {"frame": 129, "time": 4.3, "jawOpen": 1.0, "mouthSmile": 0.25, "mouthFunnel": 0.4}, {"frame": 130, "time": 4.333, "jawOpen": 0.804, "mouthSmile": 0.209, "mouthFunnel": 0.322}, {"frame": 131, "time": 4.367, "jawOpen": 0.422, "mouthSmile": 0.122, "mouthFunnel": 0.169}, {"frame": 132, "time": 4.4, "jawOpen": 0.445, "mouthSmile": 0.127, "mouthFunnel": 0.178}, {"frame": 133, "time": 4.433, "jawOpen": 0.141, "mouthSmile": 0.049, "mouthFunnel": 0.056}, {"frame": 134, "time": 4.467, "jawOpen": 0.007, "mouthSmile": 0.004, "mouthFunnel": 0.003}, {"frame": 135, "time": 4.5, "jawOpen": 0.004, "mouthSmile": 0.003, "mouthFunnel": 0.002}, {"frame": 136, "time": 4.533, "jawOpen": 0.123, "mouthSmile": 0.044, "mouthFunnel": 0.049}, {"frame": 137, "time": 4.567, "jawOpen": 0.137, "mouthSmile": 0.048, "mouthFunnel": 0.055}, {"frame": 138, "time": 4.6, "jawOpen": 0.43, "mouthSmile": 0.124, "mouthFunnel": 0.172}, {"frame": 139, "time": 4.633, "jawOpen": 0.528, "mouthSmile": 0.147, "mouthFunnel": 0.211}, {"frame": 140, "time": 4.667, "jawOpen": 0.23, "mouthSmile": 0.074, "mouthFunnel": 0.092}, {"frame": 141, "time": 4.7, "jawOpen": 0.058, "mouthSmile": 0.023, "mouthFunnel": 0.023}, {"frame": 142, "time": 4.733, "jawOpen": 0.021, "mouthSmile": 0.01, "mouthFunnel": 0.008}, {"frame": 143, "time": 4.767, "jawOpen": 0.001, "mouthSmile": 0.001, "mouthFunnel": 0.0}, {"frame": 144, "time": 4.8, "jawOpen": 0.001, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 145, "time": 4.833, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 146, "time": 4.867, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 147, "time": 4.9, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 148, "time": 4.933, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}, {"frame": 149, "time": 4.967, "jawOpen": 0.0, "mouthSmile": 0.0, "mouthFunnel": 0.0}]
if mesh_obj and mesh_obj.data.shape_keys and viseme_data:
    key_blocks = mesh_obj.data.shape_keys.key_blocks
    jaw_key = key_blocks.get("jawOpen") or key_blocks.get("mouthOpen") or next((k for k in key_blocks if "jaw" in k.name.lower() or "open" in k.name.lower()), None)
    smile_key = key_blocks.get("mouthSmile") or next((k for k in key_blocks if "smile" in k.name.lower()), None)

    for item in viseme_data:
        f_idx = item.get("frame", 0) + 1
        if f_idx > 150:
            break
        if jaw_key:
            jaw_key.value = float(item.get("jawOpen", 0.0))
            jaw_key.keyframe_insert(data_path="value", frame=f_idx)
        if smile_key:
            smile_key.value = float(item.get("mouthSmile", 0.0))
            smile_key.keyframe_insert(data_path="value", frame=f_idx)

# Lighting Mood Preset
if "studio" == "sunset":
    key_light = bpy.data.objects.get("Key_Light")
    if key_light:
        key_light.data.color = (1.0, 0.55, 0.25)
        key_light.data.energy = 800.0
elif "studio" == "cyberpunk":
    key_light = bpy.data.objects.get("Key_Light")
    fill_light = bpy.data.objects.get("Fill_Light")
    if key_light:
        key_light.data.color = (0.1, 0.8, 1.0)
    if fill_light:
        fill_light.data.color = (1.0, 0.1, 0.8)

# Configure Frame Output (PNG with RGBA transparency)
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = r"D:\AI\VidForge\characters\assets\char_38f853ba\renders\frames_scene_1\frame_"

# Background transparency
if "transparent" == "transparent":
    scene.render.film_transparent = True

bpy.ops.render.render(animation=True)
print("SUCCESS_SCENE_RENDERED")
