import bpy  # type: ignore # pyrefly: ignore[missing-import]
import json
import os
import mathutils  # type: ignore # pyrefly: ignore[missing-import]
import time

def build_single_line_project(strokes_json=None):
    t0 = time.time()
    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if strokes_json is None:
        default_candidate = os.path.join(workspace_dir, "cache", "strokes.json")
        legacy_candidate = os.path.join(workspace_dir, "cache", "toilet_bully_single_lines.json")
        strokes_json = default_candidate if os.path.exists(default_candidate) else legacy_candidate

    print("=" * 60)
    print("BUILDING CLEAN SINGLE-LINE PENCIL 2D SCENE IN BLENDER")
    print("=" * 60)

    if not os.path.exists(strokes_json):
        raise FileNotFoundError(f"Strokes file not found: {strokes_json}")

    with open(strokes_json, "r", encoding="utf-8") as f:
        strokes_data = json.load(f)

    scene = bpy.context.scene

    # 1. Setup Camera and Render Settings
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1920
    scene.render.resolution_percentage = 100
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end = max(1, len(strokes_data))
    scene.frame_current = 1

    # Standard color management for crisp line art & authentic paper colors
    scene.view_settings.view_transform = 'Standard'

    # 2. World Paper Background (#F5F3E9)
    if scene.world:
        scene.world.use_nodes = True
        if 'Background' in scene.world.node_tree.nodes:
            scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.96, 0.95, 0.91, 1.0)
            scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
        else:
            scene.world.color = (0.96, 0.95, 0.91)

    # 3. Camera Setup (2D Orthographic aligned to canvas)
    cam_obj = bpy.data.objects.get("Camera")
    if not cam_obj:
        cam_data = bpy.data.cameras.new("Camera")
        cam_obj = bpy.data.objects.new("Camera", cam_data)
        scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    cam_obj.location = (0.0, -12.0, 0.0)
    cam_obj.rotation_euler = (1.570796, 0.0, 0.0)
    cam_obj.data.type = 'ORTHO'
    cam_obj.data.ortho_scale = 10.24

    # 4. Remove default Cube or unused mesh objects
    for obj_name in ["Cube", "Light"]:
        old_obj = bpy.data.objects.get(obj_name)
        if old_obj:
            bpy.data.objects.remove(old_obj, do_unlink=True)

    # 5. Grease Pencil Object setup
    gp = bpy.data.objects.get("Stroke")
    if not gp:
        gp_data = bpy.data.grease_pencils.new("GreasePencil_Scene")
        gp = bpy.data.objects.new("Stroke", gp_data)
        scene.collection.objects.link(gp)

    # Master Material: Crisp Pencil Ink
    gp.data.materials.clear()
    mat_ink = bpy.data.materials.get("GP_Pencil_Ink") or bpy.data.materials.new("GP_Pencil_Ink")
    if not mat_ink.grease_pencil:
        bpy.data.materials.create_gpencil_data(mat_ink)
    mat_ink.grease_pencil.show_stroke = True
    mat_ink.grease_pencil.show_fill = False
    mat_ink.grease_pencil.color = (0.05, 0.05, 0.05, 1.0)
    gp.data.materials.append(mat_ink)

    # Single Clean Layer: "Lines"
    for l in list(gp.data.layers):
        if l.name != "Lines":
            gp.data.layers.remove(l)

    layer = gp.data.layers.get("Lines") or gp.data.layers.new("Lines")
    for f in list(layer.frames):
        layer.frames.remove(f.frame_number)

    # 6. Populate Clean Single Lines across Keyframes
    total_kf = len(strokes_data)
    print(f"Populating {total_kf} keyframes of pure single-line pencil strokes...")

    for f_str, lines_list in strokes_data.items():
        if not lines_list:
            continue
        f_num = int(f_str)
        kf_lines = layer.frames.new(f_num)
        d_lines = kf_lines.drawing
        d_lines.add_strokes([len(pts) for pts in lines_list])
        for s_idx, pts in enumerate(lines_list):
            st = d_lines.strokes[s_idx]
            st.material_index = 0 # GP_Pencil_Ink
            st.cyclic = False    # Single open pencil stroke (no double outline loops!)
            for p_idx, (bx, bz) in enumerate(pts):
                st.points[p_idx].position = mathutils.Vector((bx, 0.0, bz))
                st.points[p_idx].radius = 0.013 # Thin, crisp pencil stroke thickness
        d_lines.tag_positions_changed()

    # 7. Add Audio Strip & Set Real-time Sync
    audio_wav = os.path.join(workspace_dir, "cache", "audio.wav")
    audio_mp3 = os.path.join(workspace_dir, "cache", "audio.mp3")
    audio_target = audio_wav if os.path.exists(audio_wav) else audio_mp3

    if os.path.exists(audio_target):
        ed = scene.sequence_editor or scene.sequence_editor_create()
        for s in list(ed.strips):
            if s.type == 'SOUND':
                ed.strips.remove(s)
        ed.strips.new_sound(
            name="Reference_Audio",
            filepath=audio_target,
            channel=1,
            frame_start=1
        )
        scene.sync_mode = 'AUDIO_SYNC'
        print(f"Synced audio strip from {audio_target} at frame 1 with AUDIO_SYNC!")

    # 8. Set 3D Viewport to Camera View for immediate user review
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.region_3d.view_perspective = 'CAMERA'
                        space.shading.type = 'MATERIAL'

    # 9. Save project.blend
    scene.frame_set(1)
    project_blend = os.path.join(workspace_dir, "output", "blender", "project.blend")
    os.makedirs(os.path.dirname(project_blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=project_blend)
    print(f"Saved project cleanly to: {project_blend}")

    elapsed = time.time() - t0
    print(f"[SUCCESS] Clean single-line project built in {elapsed:.2f} seconds!")
    return elapsed

if __name__ == "__main__":
    build_single_line_project()
