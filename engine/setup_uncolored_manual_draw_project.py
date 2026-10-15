try:
    import bpy  # type: ignore
    import mathutils  # type: ignore
except ImportError:
    bpy = None  # type: ignore
    mathutils = None  # type: ignore

import json
import os
import time
import shutil

def configure_automated_single_line_project():
    """
    Configures automated single-line ink 2D Grease Pencil project in Blender 5.2.
    Adheres strictly to the 'NO MANUAL DRAWING' rule:
    - Zero manual drawing layers (deletes Manual_Drawing).
    - Preserves automated vector layers.
    - Sets viewport camera view and object mode.
    """
    t0 = time.time()
    print("=" * 60)
    print("CONFIGURING AUTOMATED SINGLE-LINE 2D PROJECT IN BLENDER 5.2")
    print("=" * 60)

    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_dir = os.path.join(workspace_dir, "cache", "current_video_workspace")
    os.makedirs(base_dir, exist_ok=True)
    out_blend = os.path.join(base_dir, "project.blend")
    out_blend_mirror = os.path.join(workspace_dir, "output", "blender", "project.blend")
    os.makedirs(os.path.dirname(out_blend_mirror), exist_ok=True)

    scene = bpy.context.scene

    # 1. Timeline & Resolution
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1920
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_current = 1
    scene.view_settings.view_transform = 'Standard'

    # 2. Paper Canvas World (Authentic #F5F3E9 off-white paper canvas)
    if scene.world:
        scene.world.use_nodes = True
        if 'Background' in scene.world.node_tree.nodes:
            scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.96, 0.95, 0.91, 1.0)
            scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
        else:
            scene.world.color = (0.96, 0.95, 0.91)

    # 3. Camera Setup (2D Orthographic)
    cam = bpy.data.objects.get("Camera")
    if not cam:
        cam_data = bpy.data.cameras.new("Camera")
        cam = bpy.data.objects.new("Camera", cam_data)
        scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = (0.0, -12.0, 0.0)
    cam.rotation_euler = (1.570796, 0.0, 0.0)
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 10.24

    # 4. Clean Default Meshes
    for obj_name in ["Cube", "Light"]:
        old_obj = bpy.data.objects.get(obj_name)
        if old_obj:
            bpy.data.objects.remove(old_obj, do_unlink=True)

    # 5. Grease Pencil Object Setup
    gp = bpy.data.objects.get("Stroke")
    if not gp:
        gp_data = bpy.data.grease_pencils.new("GreasePencil_Scene")
        gp = bpy.data.objects.new("Stroke", gp_data)
        scene.collection.objects.link(gp)

    # Pure black ink material
    gp.data.materials.clear()
    mat_ink = bpy.data.materials.get("GP_Black_Pencil_Ink") or bpy.data.materials.new("GP_Black_Pencil_Ink")
    if not mat_ink.grease_pencil:
        bpy.data.materials.create_gpencil_data(mat_ink)
    mat_ink.grease_pencil.show_stroke = True
    mat_ink.grease_pencil.show_fill = False
    mat_ink.grease_pencil.color = (0.04, 0.04, 0.04, 1.0)
    gp.data.materials.append(mat_ink)

    # 6. ENFORCE ZERO MANUAL DRAWING: Purge Manual_Drawing layer
    if gp.data.layers.get("Manual_Drawing"):
        gp.data.layers.remove(gp.data.layers.get("Manual_Drawing"))
        print("[BLENDER] Manual_Drawing layer purged successfully!")

    # Automated Vector Layers
    layer_names = ["Auto_Lines", "Character_1", "Character_2", "Composite_All"]
    for l_name in layer_names:
        if not gp.data.layers.get(l_name):
            gp.data.layers.new(l_name)

    # Set Composite_All as active layer
    gp.data.layers.active = gp.data.layers["Composite_All"]
    print(f"[LAYERS] Configured automated layers: {[l.name for l in gp.data.layers]}")

    # 7. Audio Sequence Synchronization
    audio_wav = os.path.join(base_dir, "audio.wav")
    if os.path.exists(audio_wav):
        ed = scene.sequence_editor or scene.sequence_editor_create()
        for s in list(ed.strips):
            if s.type == 'SOUND':
                ed.strips.remove(s)
        ed.strips.new_sound(
            name="Reference_Audio",
            filepath=audio_wav,
            channel=1,
            frame_start=1
        )
        scene.sync_mode = 'AUDIO_SYNC'
        print("[AUDIO] Synced audio strip at frame 1 with AUDIO_SYNC!")

    # 8. Viewport Setup: Camera View & Material Shading
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.region_3d.view_perspective = 'CAMERA'
                        space.shading.type = 'MATERIAL'

    # 9. Ensure Object Mode (Zero manual draw mode)
    bpy.context.view_layer.objects.active = gp
    gp.select_set(True)
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # 10. Save mainfile
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    try:
        shutil.copyfile(out_blend, out_blend_mirror)
        print(f"[SUCCESS] Saved project to {out_blend} and {out_blend_mirror}")
    except Exception:
        pass

    elapsed = time.time() - t0
    print(f"Project configured in {elapsed:.2f}s!")
    return elapsed

# Alias for backwards compatibility
configure_manual_draw_project = configure_automated_single_line_project

if __name__ == "__main__":
    configure_automated_single_line_project()
