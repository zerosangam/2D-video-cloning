---
name: universal-video-2d-recreation
description: Universal video to 2D animation recreation skill. Recreates ANY reference video into 2D gapless single-line ink art and flat color animation with zero manual drawing, separated character layers in Blender 5.2, exact audio sync, and preview grids.
---

# Universal Video to 2D Animation Recreation Skill

## When to Use This Skill
Activate this skill whenever the user asks to clone, recreate, or convert ANY video into 2D animation, line art, or cartoon style, or mentions:
- "video clone karna hai", "video create karna hai"
- "mr perfect tool", "single line", "bina gap chora"
- "character layers alag alag rakhna hai"
- "manual drawing delete karo"
- "blender 2d grease pencil"
- "watermark remove karo bina box ke"
- "intermediate files delete karke skill me update karo"

---

## 1. Core Principles & User Constraints

1. **ZERO MANUAL DRAWING**:
   - Never prompt the user to manually draw or trace frames in Blender. The entire pipeline is 100% automated via the Mr. Perfect AI Master Engine.
   - Blender project auto-populates separated Grease Pencil layers from vector splines.

2. **GAPLESS SINGLE-LINE ART (2px Charcoal Ink)**:
   - Difference of Gaussians (DoG) filter ($\sigma_1 = 1.0, \sigma_2 = 2.5$) captures both faint pencil sketches and bold contours.
   - Solid ink extraction prevents hollow double-strokes on thick fills.
   - Morphological $3 \times 3$ ellipse closing + medial-axis skeletonization + $2 \times 2$ dilation produces uniform 2px anti-aliased single-line ink art.
   - Canvas: Authentic warm paper (`#F5F3E9`, RGB `245, 243, 233`).
   - Ink: Pure dark charcoal (`#0F0F0F`, RGB `15, 15, 15`).

3. **ZERO-BOX SEAMLESS WATERMARK ELIMINATION (v9.0 LaMA Studio AI)**:
   - Never crop and paste rectangular bounding boxes!
   - Autonomous Video Profiler scans multi-frame background percentiles ($p_{90}$) and high-contrast difference ($\Delta \ge 8$).
   - False-Positive Shield ensures character hair, clothes, and chairs ($w < 110$) are never mistaken for watermarks.
   - **LaMA Deep Learning Inpainting** (`engine/lama_inpaint` with `big-lama.pt`) seamlessly reconstructs complex paper/background textures at sub-pixel text locations with zero blur and zero smudges.
   - Pure black restoration ($gray < 70 \to [15, 15, 15]$) eliminates faint ghost text inside open mouths and solid black fills.

4. **SEPARATED CHARACTER & PROP LAYERS**:
   - Connected Component analysis groups strokes into distinct Grease Pencil layers without bisecting strokes across coordinate boundaries.
   - Layers: `Character_1_Left`, `Character_2_Center`, `Character_3_Right`, `Layer_Props_Background`, `Composite_All`.

5. **AUDIO SYNCHRONIZATION**:
   - 44.1 kHz PCM audio extracted with anti-copyright +0.8 semitone pitch shift and 1.00x zero-speed frame-lock.
   - Sequencer strip locked to `AUDIO_SYNC`.

6. **AUTO-CONDENSE KNOWLEDGE & AUTO-PURGE PROTOCOL**:
   - Heavy intermediate frames (`raw_frames/`, `mr_perfect_frames/`, `color_frames/`) are temporary scratchpads.
   - Once final deliverables are compiled, all learned metrics (watermarks, palette, specs) are condensed into text in this Skill.
   - All intermediate frames are automatically purged (deleted) to preserve disk space (0 MB waste).

---

## 2. Quick Execution Commands

To clone ANY video in the `input/` folder in 1-click:
```powershell
python start_cloning.py
```

Or pass a specific video file path:
```powershell
python start_cloning.py "d:/Blender/input/my_video.mp4"
```

---

## 3. Deliverables Checklist

Every run produces clean deliverables in `d:/Blender/output/`:
- `videos/mr_perfect_color.mp4`: 1:1 authentic flat cel-shaded 2D cartoon video.
- `videos/mr_perfect_lines.mp4`: Gapless 2px single-line ink art video.
- `blender/project.blend`: Multi-layer Blender 5.2 Grease Pencil file with audio sync.
- `previews/mr_perfect_grid.jpg`: 4-quadrant narrative milestone preview.
- `metadata/master_palette.json`: K-Means 6-color palette.
- `reports/report.md`: Technical execution report.

---

## Learned Video Profiles & Knowledge Log
### Run Profile: zero (1).mp4
- **Timestamp**: 2026-10-15 07:54:34
- **Specs**: 2160x3840 -> 1080x1920 @ 60.0 FPS (1681 frames, 127.6s)
- **Watermark Detected**: True | Zones: [[427, 161, 661, 225], [364, 1331, 751, 1397], [330, 910, 730, 990], [280, 1100, 700, 1230]] | Pixels: 33828
- **Banner Detected**: True
- **Dominant Colors**: ink_outline: #030302, shadow_secondary: #646356, clothing_props: #249E86, accent_surface: #7E8273, background_paper: #A7A995, specular_highlight: #D1D4C2

### Run Profile: Big Boss mujhe hurt ho raha hai!!!.mp4
- **Timestamp**: 2026-10-14 21:00:05
- **Specs**: 1080x1920 -> 1080x1920 @ 29.97 FPS (1073 frames, 2969.3s)
- **Watermark Detected**: True | Zones: [[202, 345, 732, 529], [438, 1177, 759, 1285], [416, 1412, 754, 1491], [523, 1549, 1048, 1890], [0, 1804, 62, 1885]] | Pixels: 102249
- **Banner Detected**: False
- **Dominant Colors**: ink_outline: #030303, shadow_secondary: #585858, clothing_props: #8E8E8E, accent_surface: #C8C8C8, background_paper: #E8E8E8, specular_highlight: #FAFE4B

### Run Profile: Another helicopter helicopter 🤣😂🤣 please sub on my YouTube channel for more.mp4
- **Timestamp**: 2026-10-13 23:52:47
- **Specs**: 1072x1920 -> 1080x1920 @ 60.0 FPS (788 frames, 506.3s)
- **Watermark Detected**: True | Zones: [[330, 910, 730, 990], [280, 1100, 700, 1230]] | Pixels: 62105
- **Banner Detected**: False
- **Dominant Colors**: ink_outline: #020301, shadow_secondary: #55564A, clothing_props: #DB2A1D, accent_surface: #A5A894, background_paper: #CBCBC4, specular_highlight: #E6E7E2

### Run Profile: Trying not to laugh! 🤣🤣 (4k memes) #shorts.  click the blue Join button to support my animations.mp4
- **Timestamp**: 2026-10-13 22:35:00
- **Specs**: 2160x3840 -> 1080x1920 @ 30.0 FPS (270 frames, 132.9s)
- **Watermark Detected**: True | Zones: [[316, 905, 709, 1023]] | Pixels: 24,851
- **Banner Detected**: False
- **Dominant Colors**: ink_outline: #1A1A17, shadow_secondary: #484841, clothing_props: #6B6858, accent_surface: #988B77, background_paper: #CCCBBF, specular_highlight: #E6E7E2
