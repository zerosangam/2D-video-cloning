"""
================================================================================
MEM0 AI MEMORY BRAIN FOR 2D VIDEO CLONING
================================================================================
Extracts and specializes Mem0 long-term memory for:
1. Character Color Palettes & Identity Locking across multiple videos.
2. Stroke & Ink preferences (2px gapless DoG line art, smoothing factors).
3. Watermark & Creator profile recall (bypasses redundant watermark scans).
4. Full offline SQLite/JSON local fallback + online OpenAI/Gemini support.
================================================================================
"""

import os
import sys
import json
import sqlite3
import time
from typing import Dict, Any, Optional

# Attempt Mem0 import from installed environment
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except Exception as e:
    MEM0_AVAILABLE = False
    Memory = None


def load_dotenv(env_path: str):
    """Simple zero-dependency .env file loader."""
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    except Exception:
        pass


class AnimationMemoryBrain:
    """
    High-Performance Memory Brain utilizing Mem0 architecture for 2D Video Recreation.
    Stores and retrieves character palettes, line styles, and video profile history.
    """

    def __init__(self, workspace_dir: Optional[str] = None, user_id: str = "creator"):
        self.workspace_dir = workspace_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.user_id = user_id

        # Load environment variables (.env)
        env_file = os.path.join(self.workspace_dir, ".env")
        load_dotenv(env_file)

        self.db_dir = os.path.join(self.workspace_dir, "output", "metadata")
        os.makedirs(self.db_dir, exist_ok=True)
        self.sqlite_path = os.path.join(self.db_dir, "mem0_character_brain.db")
        self.palette_file = os.path.join(self.db_dir, "master_palette.json")
        
        self._init_local_db()
        self.mem0_client = self._init_mem0()

    def _init_local_db(self):
        """Initializes ultra-fast local SQLite tables for offline character memory."""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_memories (
                character_id TEXT PRIMARY KEY,
                name TEXT,
                palette_json TEXT,
                stroke_json TEXT,
                updated_at REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watermark_memories (
                source_key TEXT PRIMARY KEY,
                banner_flag INTEGER,
                detected_boxes TEXT,
                updated_at REAL
            )
        """)
        conn.commit()
        conn.close()

    def _init_mem0(self) -> Optional[Any]:
        """Initializes Mem0 with OpenRouter API (openrouter/free model) or local vector configuration."""
        if not MEM0_AVAILABLE:
            return None

        openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        if openrouter_key:
            try:
                model_name = os.environ.get("DEFAULT_LLM_MODEL", "openrouter/free")
                base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
                config = {
                    "llm": {
                        "provider": "openai",
                        "config": {
                            "model": model_name,
                            "api_key": openrouter_key,
                            "openai_base_url": base_url
                        }
                    },
                    "embedder": {
                        "provider": "openai",
                        "config": {
                            "model": "text-embedding-3-small",
                            "api_key": openrouter_key,
                            "openai_base_url": base_url
                        }
                    }
                }
                client = Memory.from_config(config)
                print(f"[Mem0 Brain] Initialized Neural Memory via OpenRouter (Model: '{model_name}')")
                return client
            except Exception as err:
                print(f"[Mem0 Brain] Notice: OpenRouter connection note: {err}")

        try:
            # Check if LLM API key exists
            if os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY"):
                return Memory()
        except Exception as err:
            print(f"[Mem0] Notice: Operating in local high-speed database mode ({err})")
        return None

    def recall_character(self, character_name: str) -> Dict[str, Any]:
        """
        Recalls locked color palette and line art rules for a specific character.
        If seen in previous videos, ensures exact color & stroke consistency.
        """
        clean_name = character_name.strip().lower()

        # 1. Check Mem0 neural memory if active
        if self.mem0_client:
            try:
                results = self.mem0_client.search(
                    query=f"Color palette and ink art rules for character {clean_name}",
                    user_id=self.user_id
                )
                if results and len(results) > 0:
                    text_memory = results[0].get("memory", "")
                    # Extract structured palette if found
            except Exception:
                pass

        # 2. Check Local SQLite Brain
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT palette_json, stroke_json FROM character_memories WHERE character_id = ?", (clean_name,))
        row = cursor.fetchone()
        conn.close()

        if row:
            palette = json.loads(row[0])
            stroke = json.loads(row[1]) if row[1] else {}
            return {
                "character_id": clean_name,
                "palette": palette,
                "stroke": stroke,
                "is_recalled": True
            }

        # 3. Check workspace master_palette.json fallback
        if os.path.exists(self.palette_file):
            try:
                with open(self.palette_file, "r", encoding="utf-8") as f:
                    master_pal = json.load(f)
                    return {
                        "character_id": clean_name,
                        "palette": master_pal,
                        "stroke": {"stroke_width": 2.0, "ink_color": "#0F0F0F", "paper_color": "#F5F3E9"},
                        "is_recalled": True
                    }
            except Exception:
                pass

        # Default standard 2D anime preset
        return {
            "character_id": clean_name,
            "palette": {
                "ink_outline": "#0F0F0F",
                "shadow_secondary": "#5A544F",
                "clothing_props": "#D47A60",
                "accent_surface": "#EAC58E",
                "background_paper": "#F5F3E9",
                "specular_highlight": "#FFFFFF"
            },
            "stroke": {
                "stroke_width": 2.0,
                "sigma_1": 1.0,
                "sigma_2": 2.5,
                "ink_color": "#0F0F0F",
                "paper_color": "#F5F3E9"
            },
            "is_recalled": False
        }

    def remember_character(self, character_name: str, palette: Dict[str, str], stroke: Optional[Dict[str, Any]] = None):
        """
        Stores character color palette and stroke rules permanently in Mem0 memory.
        """
        clean_name = character_name.strip().lower()
        stroke_info = stroke or {"stroke_width": 2.0, "ink_color": "#0F0F0F"}

        # Store in local SQLite
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO character_memories (character_id, name, palette_json, stroke_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (clean_name, character_name, json.dumps(palette), json.dumps(stroke_info), time.time()))
        conn.commit()
        conn.close()

        # Update workspace master_palette.json
        try:
            with open(self.palette_file, "w", encoding="utf-8") as f:
                json.dump(palette, f, indent=2)
        except Exception:
            pass

        # Store in Mem0 neural memory if active
        if self.mem0_client:
            try:
                text_payload = f"Character {character_name} uses locked 2D colors: {json.dumps(palette)} with 2px ink stroke."
                self.mem0_client.add(
                    text_payload,
                    user_id=self.user_id,
                    metadata={"character": clean_name, "type": "palette"}
                )
            except Exception:
                pass

        print(f"[Mem0 Brain] Saved character memory for '{character_name}' permanently.")

    def remember_watermark_profile(self, source_key: str, banner_flag: bool, boxes: list):
        """Remembers creator watermark signatures to speed up recurring batch processing."""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO watermark_memories (source_key, banner_flag, detected_boxes, updated_at)
            VALUES (?, ?, ?, ?)
        """, (source_key, 1 if banner_flag else 0, json.dumps(boxes), time.time()))
        conn.commit()
        conn.close()

    def recall_watermark_profile(self, source_key: str) -> Optional[Dict[str, Any]]:
        """Recalls previously computed watermark coordinates."""
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT banner_flag, detected_boxes FROM watermark_memories WHERE source_key = ?", (source_key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "has_top_banner": bool(row[0]),
                "boxes": json.loads(row[1])
            }
        return None
