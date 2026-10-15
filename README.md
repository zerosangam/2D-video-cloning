# 🎬 2D-video-cloning (Blender 2D Animation Master Workspace)

> This workspace is fully automated for cloning and recreating **ANY** reference video into **2D gapless single-line ink art** and **flat color animation** using **Mr. Perfect AI Engine (v9.0)** and **Blender 5.2**.

---

## 🗂️ Workspace Directory Map

| Folder | Purpose | Contents |
| :--- | :--- | :--- |
| **`input/`** | Input reference videos | Drop any `.mp4` video here to process. |
| **`output/`** | Final categorized deliverables | Clean subfolders: `videos/`, `blender/`, `previews/`, `character_sheets/`, `metadata/`, `reports/`. |
| **`master_system/`** | Mr. Perfect AI Master Engine | Universal engine script, full documentation, and batch runner. |
| **`engine/`** | Active Python backend modules | Clean helper modules (ingest, vectorizer, watermark cleaner, blender builder). |
| **`cache/`** | Archived projects & intermediate frames | `thailand_project/`, `toilet_bully_project/`, `legacy_scripts/`. |
| **`.agents/`** | Persistent AI Skills | `universal-video-2d-recreation` skill definition. |

---

## 📦 Deliverables in `output/`

* **`output/videos/`**:
  * `mr_perfect_lines.mp4`: Final 2D recreation with synced audio (1080x1920, 24 FPS, gapless 2px single-line art).

* **`output/blender/`**:
  * `project.blend`: Blender 5.2 project featuring separated character Grease Pencil layers (`Character_Girl`, `Character_MemeGuy`, `Composite_All`) and audio sync.

* **`output/previews/`**:
  * `mr_perfect_grid.jpg`: 4-milestone side-by-side comparison grid (Frames 1, 9, 60, 160).

* **`output/character_sheets/`**:
  * Character model sheets and locked color palettes.

* **`output/metadata/`**:
  * `master_palette.json`, `frame_prompts.json`, `timeline.json`.

* **`output/reports/`**:
  * `report.md`: Detailed technical analysis report.

---

## 🚀 How to Clone a New Video (1-Click)

1. Put your new video in `input/`.
2. Double-click `run.bat` (or tell the AI assistant: *"Naya video clone karo"*).
3. Check `output/` for your finished video, Blender file, and preview grid!

---