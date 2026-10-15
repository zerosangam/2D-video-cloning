import bpy  # type: ignore # pyrefly: ignore[missing-import]
import json
import os
import mathutils  # type: ignore # pyrefly: ignore[missing-import]
import time

PALETTE_DEF = [
    ("GP_Skin_Terracotta",   (182/255, 117/255, 107/255, 1.0)), # 0: Creator skin / face
    ("GP_DarkDetail",        ( 45/255,  41/255,  38/255, 1.0)), # 1: Shoes / dark details
    ("GP_Char_Clothes",      (154/255, 157/255, 148/255, 1.0)), # 2: Creator clothing
    ("GP_Hair_DeepShadow",   ( 77/255,  78/255,  70/255, 1.0)), # 3: Creator hair / deep shadow
    ("GP_Skin_Rosy",         (172/255, 140/255, 141/255, 1.0)), # 4: Rosy flesh highlight
    ("GP_Whiteboard_Paper",  (216/255, 223/255, 208/255, 1.0)), # 5: Whiteboard / paper
    ("GP_Desk_Wood",         (104/255,  98/255,  91/255, 1.0)), # 6: Desk wood / prop
    ("GP_Cream_Canvas",      (244/255, 243/255, 217/255, 1.0)), # 7: Cream canvas BG
    ("GP_Wall_Sage",         (173/255, 179/255, 170/255, 1.0)), # 8: Sage wall BG
    ("GP_Clothes_Shading",   (128/255, 133/255, 127/255, 1.0)), # 9: Clothes fold shading
    ("GP_Prop_LightSage",    (199/255, 206/255, 194/255, 1.0)), # 10: Secondary light prop
    ("GP_InkOutline",        (  2/255,   1/255,   1/255, 1.0)), # 11: Dark ink line art
]

def load_v2_into_active_blender(strokes_json_path=None):
    t0 = time.time()
    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if strokes_json_path is None:
        strokes_json_path = os.path.join(workspace_dir, "cache", "strokes_v2.json")

    print("=" * 60)
    print("LOADING 2D MULTI-LAYER COLOR RECREATION INTO ACTIVE BLENDER")
    print("=" * 60)

    if not os.path.exists(strokes_json_path):
        raise FileNotFoundError(f"Strokes v2 file not found: {strokes_json_path}")

    with open(strokes_json_path, "r", encoding="utf-8") as f:
        strokes_data = json.load(f)

    scene = bpy.context.scene
    gp = bpy.data.objects.get("Stroke")
    if not gp:
        gp_data = bpy.data.grease_pencils.new("GreasePencil_Scene")
        gp = bpy.data.objects.new("Stroke", gp_data)
        scene.collection.objects.link(gp)

    # 1. Setup Master Materials
    gp.data.materials.clear()
    for name, rgba in PALETTE_DEF:
        mat = bpy.data.materials.get(name)
        if not mat:
            mat = bpy.data.materials.new(name)
        if not mat.grease_pencil:
            bpy.data.materials.create_gpencil_data(mat)
        
        if name == "GP_InkOutline":
            mat.grease_pencil.show_stroke = True
            mat.grease_pencil.show_fill = False
            mat.grease_pencil.color = rgba
        else:
            mat.grease_pencil.show_stroke = False
            mat.grease_pencil.show_fill = True
            mat.grease_pencil.fill_color = rgba
        
        gp.data.materials.append(mat)

    # 2. Setup 4 Separate Layers in order
    layer_names = ["BG_Canvas", "Fills_Props", "Fills_Character", "Lines"]
    for l in list(gp.data.layers):
        if l.name not in layer_names:
            gp.data.layers.remove(l)

    layers_dict = {}
    for name in layer_names:
        l = gp.data.layers.get(name)
        if not l:
            l = gp.data.layers.new(name)
        # Clear existing frames
        for f in list(l.frames):
            l.frames.remove(f.frame_number)
        layers_dict[name] = l

    # Ensure proper bottom-to-top rendering order
    gp.data.layers.move_bottom(layers_dict["BG_Canvas"])
    gp.data.layers.move_top(layers_dict["Lines"])

    # 3. Populate Frames across Layers
    bg_quad_pts = [[-3.5, -6.0], [3.5, -6.0], [3.5, 6.0], [-3.5, 6.0]]
    total_kf = len(strokes_data)
    print(f"Populating {total_kf} keyframes into Grease Pencil layers...")
    last_bg_idx = -1

    for f_str, frame_info in strokes_data.items():
        f_num = int(f_str)
        
        # --- A. BG Canvas Layer (keyframe only when BG color changes) ---
        bg_rgb = frame_info.get("bg_rgb", [0.96, 0.96, 0.85])
        bg_mat_idx = 7 if (bg_rgb[0] > 0.85 and bg_rgb[1] > 0.85) else (8 if bg_rgb[1] > bg_rgb[0] else 10)
        
        if last_bg_idx != bg_mat_idx or f_num == 1:
            kf_bg = layers_dict["BG_Canvas"].frames.new(f_num)
            d_bg = kf_bg.drawing
            d_bg.add_strokes([4])
            st_bg = d_bg.strokes[0]
            st_bg.material_index = bg_mat_idx
            st_bg.cyclic = True
            st_bg.fill_color = (bg_rgb[0], bg_rgb[1], bg_rgb[2], 1.0)
            for i, (bx, bz) in enumerate(bg_quad_pts):
                st_bg.points[i].position = mathutils.Vector((bx, 0.0, bz))
                st_bg.points[i].radius = 0.05
            d_bg.tag_positions_changed()
            last_bg_idx = bg_mat_idx

        # --- B. Props Fills Layer ---
        props_list = frame_info.get("props_fills", [])
        if props_list:
            kf_props = layers_dict["Fills_Props"].frames.new(f_num)
            d_props = kf_props.drawing
            d_props.add_strokes([len(item["pts"]) for item in props_list])
            for s_idx, item in enumerate(props_list):
                st = d_props.strokes[s_idx]
                st.material_index = item.get("mat_index", 5)
                st.cyclic = True
                for p_idx, (bx, bz) in enumerate(item["pts"]):
                    st.points[p_idx].position = mathutils.Vector((bx, 0.0, bz))
                    st.points[p_idx].radius = 0.03
            d_props.tag_positions_changed()

        # --- C. Character Fills Layer ---
        char_list = frame_info.get("char_fills", [])
        if char_list:
            kf_char = layers_dict["Fills_Character"].frames.new(f_num)
            d_char = kf_char.drawing
            d_char.add_strokes([len(item["pts"]) for item in char_list])
            for s_idx, item in enumerate(char_list):
                st = d_char.strokes[s_idx]
                st.material_index = item.get("mat_index", 2)
                st.cyclic = True
                for p_idx, (bx, bz) in enumerate(item["pts"]):
                    st.points[p_idx].position = mathutils.Vector((bx, 0.0, bz))
                    st.points[p_idx].radius = 0.03
            d_char.tag_positions_changed()

        # --- D. Lines Layer (Ink Outlines) ---
        lines_list = frame_info.get("lines", [])
        if lines_list:
            kf_lines = layers_dict["Lines"].frames.new(f_num)
            d_lines = kf_lines.drawing
            d_lines.add_strokes([len(pts) for pts in lines_list])
            for s_idx, pts in enumerate(lines_list):
                st = d_lines.strokes[s_idx]
                st.material_index = 11 # GP_InkOutline
                st.cyclic = True
                for p_idx, (bx, bz) in enumerate(pts):
                    st.points[p_idx].position = mathutils.Vector((bx, 0.0, bz))
                    st.points[p_idx].radius = 0.035
            d_lines.tag_positions_changed()

    # 4. Final Scene Updates & Save
    scene.frame_set(35)
    output_blend = os.path.join(workspace_dir, "output", "blender", "project.blend")
    os.makedirs(os.path.dirname(output_blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output_blend)
    print(f"Saved project cleanly to: {output_blend}")
    
    elapsed = time.time() - t0
    print(f"[SUCCESS] Multi-layer color recreation loaded into active Blender in {elapsed:.2f} seconds!")
    print(f"Active Frame: {scene.frame_current}")
    print(f"Layers: {[l.name for l in gp.data.layers]}")
    return elapsed

if __name__ == "__main__":
    load_v2_into_active_blender()
