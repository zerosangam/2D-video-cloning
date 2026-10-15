import cv2
import os
import json
import numpy as np

# Master 12-color palette for character, props, and ink
PALETTE_RGB = [
    [182, 117, 107], # 0: GP_Skin_Terracotta (Creator skin / face)
    [ 45,  41,  38], # 1: GP_DarkDetail (Shoes, accents, dark detail)
    [154, 157, 148], # 2: GP_Char_Clothes (Creator shirt / main clothing)
    [ 77,  78,  70], # 3: GP_Hair_DeepShadow (Creator hair / dark shadows)
    [172, 140, 141], # 4: GP_Skin_Rosy (Face highlight / secondary skin)
    [216, 223, 208], # 5: GP_Whiteboard_Paper (Whiteboard surface / paper)
    [104,  98,  91], # 6: GP_Desk_Wood (Desk furniture / wooden props)
    [244, 243, 217], # 7: GP_Cream_Canvas (Light cream canvas)
    [173, 179, 170], # 8: GP_Wall_Sage (Sage wall / environment)
    [128, 133, 127], # 9: GP_Clothes_Shading (Clothes fold / shading)
    [199, 206, 194], # 10: GP_Prop_LightSage (Secondary light prop surface)
    [  2,   1,   1], # 11: GP_InkOutline (Dark ink line art)
]

def pixel_to_blender_coords(px, py, width=1080, height=1920, ortho_scale=10.24):
    scale = ortho_scale / float(height)
    half_w = float(width) / 2.0
    half_h = float(height) / 2.0
    bx = round((float(px) - half_w) * scale, 3)
    bz = round((half_h - float(py)) * scale, 3)
    return [bx, bz]

def find_best_mat_index(rgb):
    dists = [np.linalg.norm(np.array(rgb) - np.array(p)) for p in PALETTE_RGB[:11]]
    return int(np.argmin(dists))

def vectorize_frame_v2(img_path, width=1080, height=1920, ortho_scale=10.24):
    img = cv2.imread(img_path)
    if img is None:
        return None

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. Background Color Detection from border margins
    border = np.vstack([
        img[:25, :].reshape(-1, 3),
        img[-25:, :].reshape(-1, 3),
        img[:, :25].reshape(-1, 3),
        img[:, -25:].reshape(-1, 3)
    ])
    bg_bgr = np.median(border, axis=0).astype(int)
    bg_rgb = [round(bg_bgr[2]/255.0, 3), round(bg_bgr[1]/255.0, 3), round(bg_bgr[0]/255.0, 3)]

    # 2. Ink Outline Detection (dark strokes)
    ink_mask = (gray < 72).astype(np.uint8) * 255
    raw_cnts, _ = cv2.findContours(ink_mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_KCOS)
    lines_strokes = []
    for c in raw_cnts:
        if cv2.arcLength(c, False) > 10:
            approx = cv2.approxPolyDP(c, 0.9, True)
            if len(approx) >= 3:
                pts = [pixel_to_blender_coords(px, py, width, height, ortho_scale) for px, py in approx.reshape(-1, 2)]
                lines_strokes.append(pts)

    # 3. Non-Background & Non-Ink Colored Regions
    dist_bg = np.linalg.norm(img.astype(float) - bg_bgr.astype(float), axis=2)
    fg_mask = (dist_bg >= 24) & (gray >= 72)
    fg_u8 = fg_mask.astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fg_closed = cv2.morphologyEx(fg_u8, cv2.MORPH_CLOSE, kernel)

    cnts, _ = cv2.findContours(fg_closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    char_fills = []
    props_fills = []

    for c in cnts:
        area = cv2.contourArea(c)
        if area > 280:
            mask = np.zeros(gray.shape, dtype=np.uint8)
            cv2.drawContours(mask, [c], -1, 255, -1)
            mean_bgr = cv2.mean(img, mask=mask)[:3]
            r, g, b = int(mean_bgr[2]), int(mean_bgr[1]), int(mean_bgr[0])
            mat_idx = find_best_mat_index([r, g, b])

            approx = cv2.approxPolyDP(c, 1.4, True)
            if len(approx) >= 3:
                b_pts = [pixel_to_blender_coords(px, py, width, height, ortho_scale) for px, py in approx.reshape(-1, 2)]
                stroke_entry = {
                    "mat_index": mat_idx,
                    "pts": b_pts
                }
                # Classify into Character vs Props
                if mat_idx in [0, 1, 2, 3, 4, 9]:
                    char_fills.append(stroke_entry)
                else:
                    props_fills.append(stroke_entry)

    return {
        "bg_rgb": bg_rgb,
        "char_fills": char_fills,
        "props_fills": props_fills,
        "lines": lines_strokes
    }

def process_all_keyframes_v2(frames_dir, keyframes, meta, output_json_path):
    all_data = {}
    print(f"Vectorizing {len(keyframes)} high-fidelity keyframes with color fills...")
    for idx, f in enumerate(keyframes):
        fp = os.path.join(frames_dir, f"frame_{f:04d}.png")
        if not os.path.exists(fp):
            fp = os.path.join(frames_dir, f"frame_{f:04d}.jpg")
        if os.path.exists(fp):
            res = vectorize_frame_v2(fp, meta["width"], meta["height"])
            if res:
                all_data[str(f)] = res
        if (idx + 1) % 50 == 0 or idx == len(keyframes) - 1:
            print(f"  Processed {idx + 1}/{len(keyframes)} keyframes...")

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f)
    print(f"Saved v2 vector data to {output_json_path}")
    return all_data
