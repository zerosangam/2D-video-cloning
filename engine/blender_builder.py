import bpy  # type: ignore # pyrefly: ignore[missing-import]
import sys
import os
import json
import mathutils  # type: ignore # pyrefly: ignore[missing-import]
import time

def hex_to_rgba(hex_str, alpha=1.0):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4)) + (alpha,)

def run_blender_build():
    # Parse custom arguments after '--'
    argv = sys.argv
    if "--" in argv:
        args = argv[argv.index("--") + 1:]
    else:
        args = []

    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = args[0] if len(args) > 0 else os.path.join(workspace_dir, "cache", "build_config.json")
    
    if not os.path.exists(config_path):
        print(f"Error: Build config not found: {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    meta = config["metadata"]
    strokes_data = json.load(open(config["strokes_path"], "r", encoding="utf-8"))
    palette = json.load(open(config["palette_path"], "r", encoding="utf-8"))
    
    output_mp4 = config["output_mp4"]
    output_blend = config["output_blend"]
    previews_dir = config["previews_dir"]
    audio_path = config.get("audio_source", "")
    os.makedirs(os.path.dirname(output_mp4), exist_ok=True)
    os.makedirs(previews_dir, exist_ok=True)

    print("==================================================")
    print("STARTING BLENDER 2D GREASE PENCIL REBUILD ENGINE")
    print("==================================================")

    # 1. Scene Reset & Configuration
    scene = bpy.context.scene
    scene.render.resolution_x = meta["width"]
    scene.render.resolution_y = meta["height"]
    scene.render.resolution_percentage = 100
    scene.render.fps = int(round(meta["fps"]))
    scene.frame_start = 1
    scene.frame_end = meta["total_frames"]

    # 2. Camera Setup (2D Orthographic)
    cam = scene.camera
    if not cam:
        cam_data = bpy.data.cameras.new("2D_Camera")
        cam = bpy.data.objects.new("Camera", cam_data)
        scene.collection.objects.link(cam)
        scene.camera = cam

    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 10.24
    cam.location = (0.0, -12.0, 0.0)
    cam.rotation_euler = (1.5707963, 0.0, 0.0) # 90 degrees on X

    # 3. World Background Configuration
    if not scene.world:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg_color = hex_to_rgba(palette.get("background_canvas", {}).get("hex", "#A7AA92"))
    scene.world.color = bg_color[:3]
    if scene.world.node_tree:
        bg_node = scene.world.node_tree.nodes.get("Background")
        if bg_node:
            bg_node.inputs[0].default_value = bg_color

    # 4. Grease Pencil Object Setup
    gp_obj = bpy.data.objects.get("Stroke")
    if not gp_obj:
        gp_data = bpy.data.grease_pencils.new("GreasePencil_Scene")
        gp_obj = bpy.data.objects.new("Stroke", gp_data)
        scene.collection.objects.link(gp_obj)

    gp_obj.data.materials.clear()

    # Materials mapping
    mat_defs = [
        ("GP_InkOutline", palette.get("ink_outline", {}).get("hex", "#0D0F0C"), True, False, "#0D0F0C"),
        ("GP_Whiteboard", palette.get("ink_outline", {}).get("hex", "#0D0F0C"), True, True, palette.get("whiteboard_highlight", {}).get("hex", "#D6D8CE")),
        ("GP_DeskWood", palette.get("ink_outline", {}).get("hex", "#0D0F0C"), True, True, palette.get("secondary_surface", {}).get("hex", "#8E856B")),
        ("GP_DarkShadow", palette.get("ink_outline", {}).get("hex", "#0D0F0C"), True, True, palette.get("shadow_prop", {}).get("hex", "#253035")),
        ("GP_SageBG", "#A7AA92", False, True, palette.get("background_canvas", {}).get("hex", "#A7AA92"))
    ]

    for name, s_hex, show_s, show_f, f_hex in mat_defs:
        mat = bpy.data.materials.new(name)
        bpy.data.materials.create_gpencil_data(mat)
        mat.grease_pencil.color = hex_to_rgba(s_hex)
        mat.grease_pencil.show_stroke = show_s
        mat.grease_pencil.show_fill = show_f
        mat.grease_pencil.fill_color = hex_to_rgba(f_hex)
        gp_obj.data.materials.append(mat)

    # Layers setup
    lines_layer = gp_obj.data.layers.get("Lines")
    if not lines_layer:
        lines_layer = gp_obj.data.layers.new("Lines")
    fills_layer = gp_obj.data.layers.get("Fills")
    if not fills_layer:
        fills_layer = gp_obj.data.layers.new("Fills")

    # Clear old frames
    for l in [lines_layer, fills_layer]:
        for f in list(l.frames):
            l.frames.remove(f.frame_number)

    # 5. Populate Strokes and Fills across all keyframes
    print(f"Drawing strokes for {len(strokes_data)} keyframes...")
    t_start = time.time()
    
    for f_str, frame_content in strokes_data.items():
        f_num = int(f_str)

        # Draw Fills
        kf_fills = fills_layer.frames.new(f_num)
        d_fills = kf_fills.drawing
        if frame_content.get("fills"):
            fills_list = frame_content["fills"]
            d_fills.add_strokes([len(item["pts"]) for item in fills_list])
            for s_idx, item in enumerate(fills_list):
                st = d_fills.strokes[s_idx]
                st.material_index = item.get("mat_index", 1)
                st.cyclic = True
                for p_idx, (bx, bz) in enumerate(item["pts"]):
                    st.points[p_idx].position = mathutils.Vector((bx, 0.0, bz))
                    st.points[p_idx].radius = 0.035
            d_fills.tag_positions_changed()

        # Draw Lines
        kf_lines = lines_layer.frames.new(f_num)
        d_lines = kf_lines.drawing
        if frame_content.get("ink"):
            ink_list = frame_content["ink"]
            d_lines.add_strokes([len(pts) for pts in ink_list])
            for s_idx, pts in enumerate(ink_list):
                st = d_lines.strokes[s_idx]
                st.material_index = 0 # GP_InkOutline
                st.cyclic = True
                for p_idx, (bx, bz) in enumerate(pts):
                    st.points[p_idx].position = mathutils.Vector((bx, 0.0, bz))
                    st.points[p_idx].radius = 0.038
            d_lines.tag_positions_changed()

    print(f"Finished stroke drawing in {time.time() - t_start:.2f} seconds!")

    # 6. Audio Track Sync in VSE
    if audio_path and os.path.exists(audio_path):
        if not scene.sequence_editor:
            scene.sequence_editor_create()
        for s in list(scene.sequence_editor.strips):
            scene.sequence_editor.strips.remove(s)
        snd = scene.sequence_editor.strips.new_sound(
            name="Audio_Sync",
            filepath=audio_path,
            channel=1,
            frame_start=1
        )
        print(f"Synchronized audio strip: {snd.name} (length: {snd.frame_duration} frames)")

    # 7. Generate Milestone Preview Screenshots
    milestones = [1, 35, 75, 120, 165, 210, 245]
    for mf in milestones:
        if mf <= meta["total_frames"]:
            scene.frame_set(mf)
            preview_file = os.path.join(previews_dir, f"preview_frame_{mf:04d}.png")
            scene.render.filepath = preview_file
            bpy.ops.render.render(write_still=True)
            print(f"Generated preview screenshot: {preview_file}")

    # 8. Save .blend Project File
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=output_blend)
    print(f"Saved project file to: {output_blend}")

    # 9. Render Final MP4
    scene.render.image_settings.media_type = 'VIDEO'
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'HIGH'
    scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
    scene.render.ffmpeg.audio_codec = 'AAC'
    scene.render.ffmpeg.audio_bitrate = 192
    scene.render.filepath = output_mp4

    print(f"Rendering final video animation to {output_mp4}...")
    r_start = time.time()
    bpy.ops.render.render(animation=True)
    print(f"Render completed in {time.time() - r_start:.2f} seconds!")
    print("ALL STAGES COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_blender_build()
