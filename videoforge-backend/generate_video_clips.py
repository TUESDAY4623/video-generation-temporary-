"""VideoForge Clip Engine v2 — cinematic visualizations for educational videos.

KEY DIFFERENCES FROM v1:
  - 6 unique scene-specific visual templates (one per scene) with rich animations
  - Animated SVG icons, kinetic typography, data flow visualizations
  - 3D-style card transforms, parallax layers, animated code blocks
  - Particle systems, gradient flows, animated counters
  - Each scene gets 8-12 clips focused on its specific topic
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Ensure videoforge-backend root is in sys.path regardless of CWD
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.adapters.chat_tts_adapter import ChatTTSAdapter
from app.adapters.whisper_aligner import WhisperAligner
from app.utils.hardware import SystemProfiler, QualityProfile
from renderers.diagram_renderer import DiagramRenderer, VisualSceneSpec

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("videoforge.v2")

PROJECTS_DIR = Path(__file__).resolve().parent.parent / "projects"

# Initial dynamic hardware benchmark
_INITIAL_PROFILE = SystemProfiler.get_profile()
WIDTH = _INITIAL_PROFILE.width
HEIGHT = _INITIAL_PROFILE.height
FPS = _INITIAL_PROFILE.fps
WPM = 150  # Strictly fixed at 150 WPM
NUM_WORKERS = _INITIAL_PROFILE.max_workers
VIDEO_ENCODER = _INITIAL_PROFILE.video_encoder
VIDEO_BITRATE = _INITIAL_PROFILE.video_bitrate
PLAYWRIGHT_ARGS = list(_INITIAL_PROFILE.playwright_gpu_args)

CLIP_DURATION_SEC = 12.0
CLIP_MIN_SEC = 10.0
CLIP_MAX_SEC = 15.0
CLIPS_PER_SCENE_MIN = 6
CLIPS_PER_SCENE_MAX = 12

TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge")
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-JennyNeural")


def apply_quality_profile(profile: QualityProfile):
    """Dynamically applies quality settings to all pipeline components."""
    global WIDTH, HEIGHT, FPS, WPM, NUM_WORKERS, VIDEO_ENCODER, VIDEO_BITRATE, PLAYWRIGHT_ARGS, _RENDER_HELPER
    WIDTH = profile.width
    HEIGHT = profile.height
    FPS = profile.fps
    WPM = 150  # Fixed at 150 WPM
    NUM_WORKERS = profile.max_workers
    VIDEO_ENCODER = profile.video_encoder
    VIDEO_BITRATE = profile.video_bitrate
    PLAYWRIGHT_ARGS = list(profile.playwright_gpu_args)
    _RENDER_HELPER = None  # Force re-generation of helper with new parameters

# ── Shared theme ──────────────────────────────────────────────────────────────
THEME = {
    "bg": "#050514",
    "bg_grad": "radial-gradient(ellipse at 50% 0%, #1a1a4e 0%, #0a0a1a 60%, #050514 100%)",
    "primary": "#7c83ff",
    "secondary": "#00d4aa",
    "accent": "#ff6b9d",
    "warning": "#ffb86c",
    "text": "#e4e4f0",
    "text_dim": "#8888aa",
    "code_bg": "#0a0a20",
    "card_bg": "rgba(15, 15, 40, 0.85)",
    "font": "'Inter', 'Segoe UI', system-ui, sans-serif",
    "mono": "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
}

# ── Cinematic CSS with rich animations ───────────────────────────────────────
CSS = """\
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&family=JetBrains+Mono:wght@400;700;900&display=swap');

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: 'Inter', {font};
    background: {bg};
    background-image: {bg_grad};
    color: {text};
    width: {w}px; height: {h}px;
    overflow: hidden;
    position: relative;
    perspective: 1500px;
}}

/* Animated grid background */
.grid-bg {{
    position: absolute; inset: 0;
    background-image:
        linear-gradient(rgba(124,131,255,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(124,131,255,0.04) 1px, transparent 1px);
    background-size: 80px 80px;
    animation: gridShift 20s linear infinite;
    opacity: 0.5;
}}
@keyframes gridShift {{
    0% {{ background-position: 0 0; }}
    100% {{ background-position: 80px 80px; }}
}}

/* Floating particles */
.particles {{ position: absolute; inset: 0; pointer-events: none; overflow: hidden; }}
.particle {{
    position: absolute; border-radius: 50%;
    opacity: 0;
    animation: floatUp linear infinite;
    filter: blur(1px);
}}
@keyframes floatUp {{
    0% {{ transform: translateY(110vh) scale(0); opacity: 0; }}
    10% {{ opacity: 0.6; }}
    90% {{ opacity: 0.2; }}
    100% {{ transform: translateY(-10vh) scale(1.5); opacity: 0; }}
}}

/* Glow blobs */
.blob {{
    position: absolute; border-radius: 50%;
    filter: blur(80px); opacity: 0.4;
    animation: blobFloat 15s ease-in-out infinite;
}}
@keyframes blobFloat {{
    0%, 100% {{ transform: translate(0, 0) scale(1); }}
    50% {{ transform: translate(50px, -30px) scale(1.2); }}
}}

/* Typography */
h1 {{
    font-size: 96px; font-weight: 900; line-height: 1.0;
    background: linear-gradient(135deg, {primary} 0%, {secondary} 50%, {accent} 100%);
    background-size: 200% 200%;
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    animation: gradientShift 8s ease-in-out infinite;
    letter-spacing: -2px;
}}
@keyframes gradientShift {{
    0%, 100% {{ background-position: 0% 50%; }}
    50% {{ background-position: 100% 50%; }}
}}
h2 {{
    font-size: 64px; font-weight: 800; text-align: center;
    background: linear-gradient(135deg, {text} 0%, {primary} 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    margin-bottom: 30px;
    letter-spacing: -1px;
}}
h3 {{ font-size: 36px; font-weight: 700; }}
.subtitle {{
    font-size: 32px; color: {secondary}; font-weight: 300;
    text-align: center; margin-top: 16px; letter-spacing: 3px;
    text-transform: uppercase;
}}
.badge {{
    display: inline-block;
    background: linear-gradient(135deg, {primary}, {accent});
    color: white; padding: 12px 32px; border-radius: 50px;
    font-size: 20px; font-weight: 700; letter-spacing: 2px;
    box-shadow: 0 0 40px {primary}66, 0 8px 32px rgba(0,0,0,0.4);
    text-transform: uppercase;
}}

/* Glass cards with 3D transform */
.card {{
    background: {card_bg};
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 24px; padding: 36px;
    backdrop-filter: blur(20px);
    box-shadow: 0 12px 48px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
    transform: perspective(1000px) rotateX(0deg);
    transition: transform 0.6s ease;
    animation: cardEnter 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}}
@keyframes cardEnter {{
    0% {{ opacity: 0; transform: translateY(60px) scale(0.9); }}
    100% {{ opacity: 1; transform: translateY(0) scale(1); }}
}}

.card-glow {{
    border: 2px solid {primary};
    box-shadow: 0 0 60px {primary}55, 0 12px 48px rgba(0,0,0,0.5),
                inset 0 1px 0 rgba(255,255,255,0.1);
}}
.card-tilt {{
    animation: cardTilt 6s ease-in-out infinite;
}}
@keyframes cardTilt {{
    0%, 100% {{ transform: perspective(1000px) rotateY(0deg) rotateX(0deg); }}
    50% {{ transform: perspective(1000px) rotateY(2deg) rotateX(-1deg); }}
}}

/* Code blocks */
.code-block {{
    background: {code_bg};
    border: 1px solid {primary};
    border-radius: 16px;
    padding: 32px 40px;
    font-family: {mono};
    font-size: 28px;
    color: #a6e3a1;
    line-height: 1.8;
    text-align: left;
    box-shadow: 0 0 40px {primary}44, inset 0 1px 0 rgba(255,255,255,0.05);
    position: relative;
    overflow: hidden;
}}
.code-block::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
    background: linear-gradient(90deg, {primary}, {secondary}, {accent}, {primary});
    background-size: 200% 100%;
    animation: borderShift 4s linear infinite;
}}
@keyframes borderShift {{
    0% {{ background-position: 0% 0; }}
    100% {{ background-position: 200% 0; }}
}}
.code-block .kw {{ color: #c678dd; font-weight: 700; }}
.code-block .str {{ color: #98c379; }}
.code-block .num {{ color: #d19a66; }}
.code-block .cmt {{ color: #5c6370; font-style: italic; }}
.code-block .fn {{ color: #61afef; }}

/* Highlight */
.highlight {{ color: {accent}; font-weight: 800; text-shadow: 0 0 30px {accent}88; }}
.glow {{ text-shadow: 0 0 30px {primary}aa, 0 0 60px {primary}44; }}

/* Binary bits */
.binary-bit {{
    display: inline-block; padding: 14px 22px; margin: 6px;
    background: linear-gradient(135deg, {primary}55, {secondary}55);
    border-radius: 12px; border: 1px solid {primary};
    font-family: {mono}; font-size: 36px; font-weight: 900;
    color: #fab1a0;
    animation: bitPulse 2s ease-in-out infinite;
    box-shadow: 0 0 20px {primary}44;
}}
@keyframes bitPulse {{
    0%, 100% {{ transform: scale(1); box-shadow: 0 0 20px {primary}44; }}
    50% {{ transform: scale(1.08); box-shadow: 0 0 40px {primary}88; }}
}}
.binary-display {{
    font-family: {mono}; font-size: 56px; letter-spacing: 12px;
    color: #fab1a0; text-align: center; padding: 36px;
    background: {code_bg}; border-radius: 20px;
    border: 1px solid rgba(250,177,160,0.3);
    box-shadow: 0 0 60px rgba(250,177,160,0.15);
}}

/* Grids */
.grid {{ display: grid; gap: 32px; }}
.grid-2 {{ grid-template-columns: 1fr 1fr; }}
.grid-3 {{ grid-template-columns: repeat(3, 1fr); }}
.grid-4 {{ grid-template-columns: repeat(4, 1fr); }}
.center {{ text-align: center; }}
.split {{ display: flex; gap: 60px; align-items: center; }}
.split > div {{ flex: 1; }}

/* Caption bar */
.caption-bar {{
    position: absolute; bottom: 32px; left: 50%; transform: translateX(-50%);
    max-width: 1400px; padding: 18px 36px;
    background: rgba(5, 5, 20, 0.92);
    border: 1px solid rgba(124,131,255,0.3);
    border-radius: 16px;
    font-size: 22px; line-height: 1.5;
    color: #e4e4f0; text-align: center;
    backdrop-filter: blur(20px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    animation: fadeInUp 0.6s ease-out both;
}}
@keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateX(-50%) translateY(30px); }}
    to {{ opacity: 1; transform: translateX(-50%) translateY(0); }}
}}

/* Clip badge */
.clip-badge {{
    position: absolute; top: 28px; right: 32px;
    background: rgba(5, 5, 20, 0.85);
    border: 1px solid rgba(124,131,255,0.3);
    border-radius: 10px; padding: 8px 18px;
    font-size: 14px; color: {text_dim}; font-family: {mono};
    backdrop-filter: blur(10px);
}}

/* Scene badge */
.scene-badge {{
    position: absolute; top: 28px; left: 32px;
    background: rgba(5, 5, 20, 0.85);
    border: 1px solid rgba(124,131,255,0.3);
    border-radius: 10px; padding: 8px 18px;
    font-size: 14px; color: {primary}; font-family: {mono};
    backdrop-filter: blur(10px);
}}

/* Binary counter */
.bit-counter {{
    display: inline-block;
    font-family: {mono}; font-size: 72px; font-weight: 900;
    color: #fab1a0;
    text-shadow: 0 0 40px rgba(250,177,160,0.8);
    animation: countPulse 1s ease-in-out infinite;
}}
@keyframes countPulse {{
    0%, 100% {{ transform: scale(1); }}
    50% {{ transform: scale(1.05); }}
}}

/* Venn diagram circles */
.venn-circle {{
    position: absolute;
    border-radius: 50%;
    border: 3px solid;
    display: flex; align-items: center; justify-content: center;
    font-size: 28px; font-weight: 700;
    text-align: center;
    animation: vennFloat 8s ease-in-out infinite;
    backdrop-filter: blur(10px);
}}
@keyframes vennFloat {{
    0%, 100% {{ transform: translate(0, 0); }}
    50% {{ transform: translate(10px, -10px); }}
}}

/* Pipeline boxes */
.pipeline-box {{
    display: flex; align-items: center; justify-content: center;
    width: 200px; height: 200px;
    border-radius: 24px;
    font-size: 80px;
    animation: pulse 3s ease-in-out infinite;
    box-shadow: 0 12px 48px rgba(0,0,0,0.4);
}}
@keyframes pulse {{
    0%, 100% {{ transform: scale(1); }}
    50% {{ transform: scale(1.04); }}
}}
.arrow-flow {{
    font-size: 80px; font-weight: 900;
    color: {primary};
    animation: arrowRight 1.5s ease-in-out infinite;
}}
@keyframes arrowRight {{
    0%, 100% {{ transform: translateX(0); opacity: 0.6; }}
    50% {{ transform: translateX(15px); opacity: 1; }}
}}

/* Hamster wheel */
.wheel {{
    width: 300px; height: 300px; border-radius: 50%;
    border: 12px solid {primary};
    position: relative;
    animation: spin 3s linear infinite;
    box-shadow: 0 0 60px {primary}88;
}}
@keyframes spin {{ to {{ transform: rotate(360deg); }} }}
.wheel::before {{
    content: '🐹'; position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    font-size: 80px;
    animation: spin 3s linear infinite reverse;
}}

/* Light switch */
.switch-container {{
    display: inline-block;
    width: 200px; height: 320px;
    background: linear-gradient(135deg, #2a2a4a, #1a1a3a);
    border-radius: 100px;
    border: 4px solid #4a4a6a;
    position: relative;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5), inset 0 4px 0 rgba(255,255,255,0.1);
}}
.switch-flip {{
    position: absolute; top: 30px; left: 50%;
    transform: translateX(-50%);
    width: 80px; height: 80px; border-radius: 50%;
    background: linear-gradient(135deg, {primary}, {secondary});
    box-shadow: 0 0 40px {primary}aa;
    animation: switchMove 3s ease-in-out infinite;
}}
@keyframes switchMove {{
    0%, 40% {{ top: 30px; }}
    50%, 90% {{ top: 200px; }}
    100% {{ top: 30px; }}
}}
.lightbulb {{
    font-size: 120px;
    animation: bulbGlow 3s ease-in-out infinite;
    filter: drop-shadow(0 0 30px currentColor);
}}
@keyframes bulbGlow {{
    0%, 40% {{ color: #fab1a0; opacity: 1; }}
    50%, 90% {{ color: #2a2a4a; opacity: 0.4; }}
    100% {{ color: #fab1a0; opacity: 1; }}
}}

/* Data flow particles */
.data-particle {{
    position: absolute;
    width: 20px; height: 20px;
    border-radius: 50%;
    background: {accent};
    box-shadow: 0 0 30px {accent};
    animation: dataFlow 3s linear infinite;
}}
@keyframes dataFlow {{
    0% {{ left: 5%; top: 50%; opacity: 0; }}
    20% {{ opacity: 1; }}
    80% {{ opacity: 1; }}
    100% {{ left: 95%; top: 50%; opacity: 0; }}
}}

/* Code typing animation */
.typed-cursor {{
    display: inline-block;
    width: 3px; height: 1em;
    background: {primary};
    margin-left: 4px;
    animation: blink 1s step-end infinite;
    vertical-align: text-bottom;
}}
@keyframes blink {{
    50% {{ opacity: 0; }}
}}

/* Flowchart nodes */
.flow-node {{
    padding: 28px 48px;
    border-radius: 16px;
    font-size: 30px; font-weight: 700;
    text-align: center; min-width: 280px;
    backdrop-filter: blur(10px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    animation: nodeEnter 0.6s ease-out both;
}}
@keyframes nodeEnter {{
    0% {{ opacity: 0; transform: scale(0.7); }}
    100% {{ opacity: 1; transform: scale(1); }}
}}
.flow-arrow {{
    font-size: 60px; color: {primary};
    animation: arrowDown 1.5s ease-in-out infinite;
    margin: 8px 0;
}}
@keyframes arrowDown {{
    0%, 100% {{ transform: translateY(0); opacity: 0.6; }}
    50% {{ transform: translateY(10px); opacity: 1; }}
}}

/* Scratch blocks */
.scratch-block {{
    padding: 18px 36px;
    border-radius: 8px;
    font-size: 26px; font-weight: 700;
    color: white;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4);
    position: relative;
    transform: translateX(0);
    animation: blockSlide 0.5s ease-out both;
}}
@keyframes blockSlide {{
    0% {{ transform: translateX(-50px); opacity: 0; }}
    100% {{ transform: translateX(0); opacity: 1; }}
}}

/* Fade-in delays */
.fade-in {{ animation: fadeIn 1s ease-out both; }}
.fade-in-d1 {{ animation: fadeIn 1s ease-out 0.3s both; }}
.fade-in-d2 {{ animation: fadeIn 1s ease-out 0.6s both; }}
.fade-in-d3 {{ animation: fadeIn 1s ease-out 0.9s both; }}
@keyframes fadeIn {{
    0% {{ opacity: 0; transform: translateY(20px); }}
    100% {{ opacity: 1; transform: translateY(0); }}
}}
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Script parsing, clip splitting — same as before
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_structured_topic_script(topic: str, subtopic: str, explanation: str, wpm: int = 150) -> list[dict]:
    """Generates an educational 5-scene, 16-clip script synchronized with visual templates at 150 WPM."""
    topic_clean = topic.strip() or "Data Algorithms"
    sub_clean = subtopic.strip() or "Architectural Patterns & Complexity"
    expl_clean = explanation.strip() or f"Comprehensive guide to understanding {topic_clean} and optimization."

    return [
        {
            "index": 0,
            "title": f"Introduction to {topic_clean}",
            "visual": "Three foundational pillars of modern algorithmic design.",
            "visual_spec": {
                "visual_type": "concept_card",
                "title": f"{topic_clean} Foundations",
                "subtitle": sub_clean,
                "accent_color": "#7c83ff",
                "key_points": [
                    f"Core definition and essential principles of {topic_clean}.",
                    "Deterministic transformation of inputs into predictable outputs.",
                    "Efficiency metrics measured in Time and Space complexity."
                ]
            },
            "clips": [
                {
                    "clip_index": 0,
                    "narration": f"Welcome to our deep dive into {topic_clean}, the foundational building blocks that power modern software systems.",
                    "duration_seconds": 6.8
                },
                {
                    "clip_index": 1,
                    "narration": "Every algorithm is an unambiguous sequence of instructions designed to transform raw input into structured results.",
                    "duration_seconds": 6.8
                },
                {
                    "clip_index": 2,
                    "narration": "By optimizing execution paths, we dramatically reduce memory consumption and achieve near instantaneous throughput.",
                    "duration_seconds": 6.8
                }
            ],
            "duration_seconds": 20.4
        },
        {
            "index": 1,
            "title": "Architectural Pipeline & Data Flow",
            "visual": "Three-stage data pipeline showing flow from Raw Input through Engine to Output.",
            "visual_spec": {
                "visual_type": "diagram",
                "title": f"{topic_clean} Architecture",
                "subtitle": "Modular Processing Pipeline",
                "accent_color": "#00d4aa",
                "diagram_code": "graph LR\n    A[Raw Input Data] -->|Parse & Validate| B[Transformation Engine]\n    B -->|Persist & Cache| C[Structured Output]"
            },
            "clips": [
                {
                    "clip_index": 0,
                    "narration": "Our architecture starts at the ingestion layer, receiving diverse streams of unsorted data.",
                    "duration_seconds": 6.5
                },
                {
                    "clip_index": 1,
                    "narration": "The core transformation engine applies recursive partitioning to isolate bottlenecks and accelerate computation.",
                    "duration_seconds": 6.8
                },
                {
                    "clip_index": 2,
                    "narration": "Finally, the structured output is validated and delivered with zero latency overhead.",
                    "duration_seconds": 6.2
                }
            ],
            "duration_seconds": 19.5
        },
        {
            "index": 2,
            "title": "Implementation & Core Logic",
            "visual": "Modern syntax-highlighted IDE code walkthrough showcasing algorithm logic.",
            "visual_spec": {
                "visual_type": "code_walkthrough",
                "title": f"{topic_clean} Implementation",
                "subtitle": "High-Performance Execution Logic",
                "accent_color": "#ff6b9d",
                "code_language": "python",
                "code_snippet": f"def execute_{topic_clean.lower().replace(' ', '_')}(stream, threshold=0.95):\n    # Initialize optimized state tracking\n    buffer = []\n    for item in stream:\n        if item.quality >= threshold:\n            buffer.append(item.process())\n    return compile_results(buffer)",
                "highlight_lines": [1, 2, 3]
            },
            "clips": [
                {
                    "clip_index": 0,
                    "narration": "Let's examine the production implementation, starting with our optimized memory buffer.",
                    "duration_seconds": 6.5
                },
                {
                    "clip_index": 1,
                    "narration": "Inside the processing loop, conditional branch evaluation filters noise before committing to heap storage.",
                    "duration_seconds": 7.0
                },
                {
                    "clip_index": 2,
                    "narration": "The compiled results are packaged cleanly, guaranteeing thread safety across concurrent workers.",
                    "duration_seconds": 6.8
                }
            ],
            "duration_seconds": 20.3
        },
        {
            "index": 3,
            "title": "Lifecycle Execution & Pipeline Stages",
            "visual": "Sequential 3-step pipeline flow highlighting stages from Ingestion to Validation.",
            "visual_spec": {
                "visual_type": "process_flow",
                "title": f"{topic_clean} Lifecycle",
                "subtitle": "Step-by-Step Production Process",
                "accent_color": "#ffb86c",
                "steps": [
                    {"title": "Ingestion", "desc": "Buffering and deduplicating continuous payload streams"},
                    {"title": "Computation", "desc": "Executing vectorized transforms and index lookups"},
                    {"title": "Verification", "desc": "Enforcing schema invariants and latency guarantees"}
                ]
            },
            "clips": [
                {
                    "clip_index": 0,
                    "narration": "Stage one handles streaming ingestion, sanitizing inputs before memory commitment.",
                    "duration_seconds": 6.5
                },
                {
                    "clip_index": 1,
                    "narration": "Stage two drives parallel vectorized computation, utilizing all available execution cores.",
                    "duration_seconds": 6.8
                },
                {
                    "clip_index": 2,
                    "narration": "Stage three performs real-time verification to guarantee sub-millisecond response times.",
                    "duration_seconds": 6.5
                }
            ],
            "duration_seconds": 19.8
        },
        {
            "index": 4,
            "title": "Complexity Analysis & Performance Benchmarks",
            "visual": "Four-way complexity tradeoff comparison matrix from constant to quadratic time.",
            "visual_spec": {
                "visual_type": "comparison",
                "title": "Algorithmic Complexity Matrix",
                "subtitle": "Time vs Space Optimization Metrics",
                "accent_color": "#7c83ff",
                "comparison_items": [
                    {"title": "Direct Hash Access", "val": "O(1)", "desc": "Instant constant-time lookup"},
                    {"title": "Binary Search", "val": "O(log n)", "desc": "Logarithmic divide and conquer"},
                    {"title": "Linear Traversal", "val": "O(n)", "desc": "Proportional streaming scan"},
                    {"title": "Divide & Conquer", "val": "O(n log n)", "desc": "Optimal sorting benchmark"}
                ]
            },
            "clips": [
                {
                    "clip_index": 0,
                    "narration": "Constant time lookup delivers instant access regardless of how large the underlying dataset grows.",
                    "duration_seconds": 6.8
                },
                {
                    "clip_index": 1,
                    "narration": "Binary search halves the search space at each iteration, making it ideal for sorted indices.",
                    "duration_seconds": 6.5
                },
                {
                    "clip_index": 2,
                    "narration": "Linear traversal guarantees complete coverage when inspecting unordered data sequences.",
                    "duration_seconds": 6.5
                },
                {
                    "clip_index": 3,
                    "narration": "Optimal divide-and-conquer strategies scale predictably even under extreme enterprise workloads.",
                    "duration_seconds": 6.8
                }
            ],
            "duration_seconds": 26.6
        }
    ]


def load_or_create_script(project_dir, topic, subtopic, explanation, profile: QualityProfile | None = None) -> str:
    json_path = Path(project_dir) / "script.json"
    if json_path.exists():
        return json_path.read_text(encoding="utf-8")
    script_path = Path(project_dir) / "script.txt"
    if script_path.exists():
        return script_path.read_text(encoding="utf-8")

    Path(project_dir).mkdir(parents=True, exist_ok=True)
    structured_script = _generate_structured_topic_script(topic, subtopic, explanation, 150)
    json_content = json.dumps(structured_script, indent=2)
    json_path.write_text(json_content, encoding="utf-8")
    script_path.write_text(json_content, encoding="utf-8")
    return json_content


def parse_scenes(script_text: str) -> list[dict]:
    scenes = []
    try:
        data = json.loads(script_text)
        if isinstance(data, list):
            for i, s in enumerate(data):
                scenes.append({
                    "index": i,
                    "title": s.get("title", f"Scene {i + 1}"),
                    "visual": s.get("visual", ""),
                    "visual_spec": s.get("visual_spec"),
                    "narration": s.get("narration", s.get("audio", "")),
                    "clips": s.get("clips"),
                    "duration_seconds": float(s.get("duration_seconds", s.get("duration", 480))),
                })
            return scenes
    except (json.JSONDecodeError, TypeError):
        pass

    blocks = re.split(r'(?=##\s*SCENE\s*\d+)', script_text, flags=re.IGNORECASE)
    for i, block in enumerate(blocks):
        block = block.strip()
        if not block:
            continue
        title = f"Scene {i + 1}"
        visual = ""
        narration = ""
        duration = 480.0
        lines = block.splitlines()
        current_section = None
        section_content = []
        for line in lines:
            m = re.match(r'^##+\s*(.*)', line)
            if m:
                if current_section and section_content:
                    content = "\n".join(section_content).strip()
                    if "title" in current_section.lower():
                        title = content.splitlines()[0].strip()
                    elif "visual" in current_section.lower():
                        visual = content
                    elif "narrator" in current_section.lower() or "audio" in current_section.lower():
                        narration = content
                current_section = m.group(1).strip()
                section_content = []
                continue
            if current_section is not None:
                section_content.append(line)
        if current_section and section_content:
            content = "\n".join(section_content).strip()
            if "title" in current_section.lower():
                title = content.splitlines()[0].strip()
            elif "visual" in current_section.lower():
                visual = content
            elif "narrator" in current_section.lower() or "audio" in current_section.lower():
                narration = content
        if narration:
            duration = len(narration.split()) / WPM * 60
        scenes.append({
            "index": i,
            "title": title,
            "visual": visual,
            "narration": narration,
            "duration_seconds": duration if duration > 0 else 480.0,
        })
    return scenes


def split_scene_into_clips(scene: dict, min_clips: int | None = None, max_clips: int | None = None) -> list[dict]:
    min_c = min_clips if min_clips is not None else CLIPS_PER_SCENE_MIN
    max_c = max_clips if max_clips is not None else CLIPS_PER_SCENE_MAX
    narration = scene.get("narration", "").strip()
    base_visual = scene.get("visual", "")
    total_dur = float(scene.get("duration_seconds", 480))

    if scene.get("clips") and isinstance(scene["clips"], list):
        explicit_clips = []
        num_c = len(scene["clips"])
        for i, c in enumerate(scene["clips"]):
            text = c.get("narration", "").strip() if isinstance(c, dict) else str(c).strip()
            wc = len(text.split())
            sec = max(3.0, wc / WPM * 60)
            explicit_clips.append({
                "narration": text,
                "visual_hint": base_visual,
                "duration_seconds": round(sec, 1),
                "clip_index": i,
                "total_clips": num_c,
                "scene_title": scene.get("title", ""),
                "variant": ["concept", "detail", "analogy", "demo"][i % 4],
                "word_count": wc,
            })
        return explicit_clips

    if not narration:
        num_clips = max(min_c, min(max_c, int(total_dur / CLIP_DURATION_SEC)))
        return [{
            "narration": "", "visual_hint": base_visual,
            "duration_seconds": CLIP_DURATION_SEC, "clip_index": i,
            "total_clips": num_clips, "scene_title": scene.get("title", ""),
            "variant": "concept",
        } for i in range(num_clips)]

    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', narration) if s.strip()]
    if not sentences:
        return []

    # If min_clips is None or equals sentence count, 1 sentence = 1 clip for tight synchronization!
    if min_clips is None and len(sentences) >= 1:
        s_clips = []
        num_c = len(sentences)
        for i, sent in enumerate(sentences):
            wc = len(sent.split())
            sec = max(3.0, wc / WPM * 60)
            s_clips.append({
                "narration": sent,
                "visual_hint": base_visual,
                "duration_seconds": round(sec, 1),
                "clip_index": i,
                "total_clips": num_c,
                "scene_title": scene.get("title", ""),
                "variant": ["concept", "detail", "analogy", "demo"][i % 4],
                "word_count": wc,
            })
        return s_clips

    total_words = len(narration.split())
    num_clips = max(min_c, min(max_c, int(total_words / (WPM * CLIP_DURATION_SEC / 60)) + 1))
    words_per_clip = total_words / max(1, num_clips)

    clips = []
    cur_sents = []
    cur_count = 0
    clip_idx = 0

    def flush():
        nonlocal clip_idx
        if not cur_sents:
            return
        chunk_text = " ".join(cur_sents).strip()
        wc = cur_count
        sec = max(CLIP_MIN_SEC, min(CLIP_MAX_SEC, wc / WPM * 60))
        kw = _extract_visual_keywords(chunk_text)
        hint = base_visual + ((" | " + ", ".join(kw)) if kw else "")
        variant = ["concept", "detail", "analogy", "demo"][clip_idx % 4]
        clips.append({
            "narration": chunk_text, "visual_hint": hint,
            "duration_seconds": round(sec, 1), "clip_index": clip_idx,
            "total_clips": num_clips, "scene_title": scene.get("title", ""),
            "variant": variant, "word_count": wc,
        })
        clip_idx += 1

    for sent in sentences:
        wc = len(sent.split())
        if cur_count + wc > words_per_clip * 1.5 and cur_sents:
            flush(); cur_sents = []; cur_count = 0
        cur_sents.append(sent)
        cur_count += wc
        if cur_count >= words_per_clip and len(clips) < num_clips - 1:
            flush(); cur_sents = []; cur_count = 0
    flush()
    if clips:
        total = sum(c["duration_seconds"] for c in clips)
        if total > 0:
            scale = total_dur / total
            for c in clips:
                c["duration_seconds"] = round(c["duration_seconds"] * scale, 1)
    return clips


def _extract_visual_keywords(text: str) -> list[str]:
    lower = text.lower()
    hints = []
    keyword_map = [
        (["welcome", "introduction", "computer science"], "intro"),
        (["venn", "problem-solving", "problem solving", "studying", "study"], "venn"),
        (["smartphone", "drone", "code", "movies", "screen"], "tech_montage"),
        (["electric", "electricity", "chip", "pathways"], "electricity"),
        (["light switch", "switch", "on", "off", "bulb"], "lightswitch"),
        (["base 10", "fingers", "decimal"], "base10"),
        (["base 2", "binary", "count", "10", "11", "100"], "binary_count"),
        (["ascii", "65", "66", "letter"], "ascii"),
        (["rgb", "red", "green", "blue", "pixel", "color", "orange"], "rgb"),
        (["image", "video", "photo", "youtube", "game"], "img_story"),
        (["recipe", "chef", "bake", "cake"], "recipe"),
        (["pseudocode", "plain english", "logical"], "pseudocode"),
        (["password", "login", "if", "condition"], "condition"),
        (["input", "output", "factory", "boxes", "truck"], "io_factory"),
        (["function", "reusable", "block"], "function"),
        (["loop", "hamster", "wheel", "repeat", "100"], "loop"),
        (["scratch", "block", "purple"], "scratch"),
        (["dna", "smartphone", "rocket"], "summary"),
        (["assignment", "conclusion", "peanut butter", "jelly"], "outro"),
    ]
    for keys, hint in keyword_map:
        if any(k in lower for k in keys):
            if hint not in hints:
                hints.append(hint)
    return hints


# ═══════════════════════════════════════════════════════════════════════════════
# Scene-specific visual templates
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_particles(n=20, color="#7c83ff", height=1080):
    return f'<div class="particles">' + "".join(
        f'<div class="particle" style="left:{5+i*4.5}%;width:{3+i%5}px;height:{3+i%5}px;background:{color};'
        f'animation-duration:{8+i*1.5}s;animation-delay:{i*0.3}s"></div>'
        for i in range(n)
    ) + "</div>"


def _generate_blobs():
    return """<div class="blob" style="width:500px;height:500px;background:#7c83ff;top:10%;left:5%;animation-delay:0s"></div>
<div class="blob" style="width:400px;height:400px;background:#00d4aa;top:60%;right:5%;animation-delay:5s"></div>
<div class="blob" style="width:350px;height:350px;background:#ff6b9d;bottom:5%;left:30%;animation-delay:10s"></div>"""


def _base_html(title, body, clip_id, scene_id, css):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width={WIDTH}">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<div class="grid-bg"></div>
{_generate_blobs()}
{_generate_particles(18, '#7c83ff')}
<div class="scene-badge">{scene_id}</div>
<div class="clip-badge">{clip_id}</div>
{body}
</body>
</html>"""


def build_intro_visual(scene: dict, clip: dict, clip_id: str, scene_id: str) -> str:
    """Scene 1: Introduction to Computer Science.

    Clips:
      0: Tech montage grid
      1: CS ≠ Programming tagline
      2: Venn diagram (CS core)
      3: Problem-solving highlight
      4: Programming = tool
      5: Algorithms + hardware
    """
    idx = clip["clip_index"]
    total = clip["total_clips"]
    css = CSS.format(font=THEME["font"], mono=THEME["mono"], w=WIDTH, h=HEIGHT,
                     bg=THEME["bg"], bg_grad=THEME["bg_grad"],
                     primary=THEME["primary"], secondary=THEME["secondary"],
                     accent=THEME["accent"], text=THEME["text"], text_dim=THEME["text_dim"],
                     code_bg=THEME["code_bg"], card_bg=THEME["card_bg"])

    if idx == 0:
        # Tech montage - simulated with icons
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <div class="badge fade-in">MODULE 1</div>
    <h1 class="fade-in-d1" style="margin-top:40px;font-size:84px">Computer Science<br><span class="highlight">Fundamentals</span></h1>
    <p class="subtitle fade-in-d2">The Computational Mindset & Binary</p>
    <div class="card card-glow fade-in-d3" style="max-width:900px;margin-top:50px;padding:40px">
        <div class="grid grid-4" style="text-align:center">
            <div class="fade-in" style="animation-delay:0.2s">
                <div style="font-size:80px;margin-bottom:8px">📱</div>
                <p style="color:{THEME['primary']};font-size:20px;font-weight:600">Smartphone</p>
            </div>
            <div class="fade-in" style="animation-delay:0.4s">
                <div style="font-size:80px;margin-bottom:8px">🚁</div>
                <p style="color:{THEME['secondary']};font-size:20px;font-weight:600">Drone</p>
            </div>
            <div class="fade-in" style="animation-delay:0.6s">
                <div style="font-size:80px;margin-bottom:8px">🌆</div>
                <p style="color:{THEME['accent']};font-size:20px;font-weight:600">CGI Cities</p>
            </div>
            <div class="fade-in" style="animation-delay:0.8s">
                <div style="font-size:80px;margin-bottom:8px">💻</div>
                <p style="color:{THEME['warning']};font-size:20px;font-weight:600">Code</p>
            </div>
        </div>
    </div>
</div>"""
    elif idx == 1:
        # CS is NOT just programming
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:80px">
    <h1 class="fade-in" style="font-size:84px"><span class="highlight">Computer Science</span><br>is NOT just programming</h1>
    <div class="card card-glow fade-in-d2" style="max-width:850px;margin-top:60px;padding:50px">
        <h3 style="color:{THEME['primary']};text-align:center;margin-bottom:30px">In the movies it looks like:</h3>
        <div class="code-block" style="font-size:32px;text-align:center">
            <span style="color:#5c6370">&gt;_ </span>
            <span class="str" style="font-family:{THEME['mono']}">h4ck_th3_pl4n3t_</span><span class="typed-cursor"></span>
        </div>
        <p style="color:{THEME['text_dim']};text-align:center;margin-top:30px;font-size:26px">
            Green text on a black screen. But that's <span class="highlight">just one tiny tool</span>.
        </p>
    </div>
</div>"""
    elif idx == 2:
        # Venn diagram
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:40px">
    <h2 class="fade-in">Computer Science = Way More</h2>
    <div style="position:relative;width:1100px;height:500px;margin:50px auto 0">
        <div class="venn-circle fade-in" style="width:360px;height:360px;border-color:{THEME['primary']};background:{THEME['primary']}22;top:70px;left:50px;animation-delay:0.2s">
            <div style="text-align:center">
                <div style="font-size:60px">⌨️</div>
                <div style="color:{THEME['primary']};margin-top:12px">Programming</div>
                <div style="color:{THEME['text_dim']};font-size:18px;margin-top:6px">The tool</div>
            </div>
        </div>
        <div class="venn-circle fade-in" style="width:360px;height:360px;border-color:{THEME['secondary']};background:{THEME['secondary']}22;top:70px;left:380px;animation-delay:0.4s">
            <div style="text-align:center">
                <div style="font-size:60px">🧠</div>
                <div style="color:{THEME['secondary']};margin-top:12px">Algorithms</div>
                <div style="color:{THEME['text_dim']};font-size:18px;margin-top:6px">Logic</div>
            </div>
        </div>
        <div class="venn-circle fade-in" style="width:360px;height:360px;border-color:{THEME['accent']};background:{THEME['accent']}22;top:70px;left:710px;animation-delay:0.6s">
            <div style="text-align:center">
                <div style="font-size:60px">💾</div>
                <div style="color:{THEME['accent']};margin-top:12px">Hardware</div>
                <div style="color:{THEME['text_dim']};font-size:18px;margin-top:6px">The machine</div>
            </div>
        </div>
        <div class="card card-glow fade-in-d3" style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);padding:24px 60px;text-align:center">
            <div style="font-size:60px">🎯</div>
            <h3 class="highlight" style="margin-top:8px;font-size:42px">Problem Solving</h3>
            <p style="color:{THEME['text_dim']};font-size:22px;margin-top:6px">The CORE of CS</p>
        </div>
    </div>
</div>"""
    elif idx == 3:
        # Problem solving deep dive
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">🎯 Problem Solving is the Heart</h2>
    <div class="fade-in-d1" style="max-width:950px;margin:50px auto 0">
        <div class="card card-glow" style="padding:40px">
            <h3 style="color:{THEME['primary']};text-align:center;margin-bottom:30px">The Computer Science Loop</h3>
            <div style="display:flex;align-items:center;justify-content:space-between;gap:24px">
                <div class="flow-node flow-process" style="background:linear-gradient(135deg,{THEME['primary']}55,{THEME['primary']}22);border:2px solid {THEME['primary']};color:{THEME['primary']}">🧩<br>Problem</div>
                <div class="flow-arrow">→</div>
                <div class="flow-node flow-decision" style="background:linear-gradient(135deg,{THEME['secondary']}55,{THEME['secondary']}22);border:2px solid {THEME['secondary']};color:{THEME['secondary']}">💡<br>Think</div>
                <div class="flow-arrow">→</div>
                <div class="flow-node flow-process" style="background:linear-gradient(135deg,{THEME['accent']}55,{THEME['accent']}22);border:2px solid {THEME['accent']};color:{THEME['accent']}">⚙️<br>Algorithm</div>
                <div class="flow-arrow">→</div>
                <div class="flow-node flow-decision" style="background:linear-gradient(135deg,{THEME['warning']}55,{THEME['warning']}22);border:2px solid {THEME['warning']};color:{THEME['warning']}">💻<br>Code</div>
            </div>
        </div>
    </div>
    <div class="card fade-in-d2" style="max-width:800px;margin:40px auto 0;padding:30px;text-align:center">
        <p style="font-size:26px;line-height:1.6;color:{THEME['text']}">
            Programming is just <span class="highlight">the tool</span> we use to give the computer our solution.
        </p>
    </div>
</div>"""
    elif idx == 4:
        # Today's journey
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">Today's Journey</h2>
    <div class="fade-in-d1" style="max-width:900px;margin:50px auto">
        <div class="grid grid-2" style="gap:24px">
            <div class="card card-tilt" style="padding:32px;text-align:center">
                <div style="font-size:60px">💡</div>
                <h3 style="color:{THEME['primary']};font-size:26px;margin-top:12px">Binary</h3>
                <p style="color:{THEME['text_dim']};font-size:18px;margin-top:8px">1s and 0s</p>
            </div>
            <div class="card card-tilt" style="padding:32px;text-align:center;animation-delay:0.2s">
                <div style="font-size:60px">🔤</div>
                <h3 style="color:{THEME['secondary']};font-size:26px;margin-top:12px">ASCII & RGB</h3>
                <p style="color:{THEME['text_dim']};font-size:18px;margin-top:8px">Text & Color</p>
            </div>
            <div class="card card-tilt" style="padding:32px;text-align:center;animation-delay:0.4s">
                <div style="font-size:60px">🧠</div>
                <h3 style="color:{THEME['accent']};font-size:26px;margin-top:12px">Algorithms</h3>
                <p style="color:{THEME['text_dim']};font-size:18px;margin-top:8px">Step-by-step</p>
            </div>
            <div class="card card-tilt" style="padding:32px;text-align:center;animation-delay:0.6s">
                <div style="font-size:60px">⚙️</div>
                <h3 style="color:{THEME['warning']};font-size:26px;margin-top:12px">Functions & Loops</h3>
                <p style="color:{THEME['text_dim']};font-size:18px;margin-top:8px">The building blocks</p>
            </div>
        </div>
    </div>
</div>"""
    else:
        # Wrap-up for intro
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:100px">
    <h1 class="fade-in" style="font-size:72px">By the end, you'll understand<br>how <span class="highlight">metal and electricity</span><br>create the apps you use daily</h1>
    <div class="card card-glow fade-in-d2" style="max-width:700px;margin:60px auto 0;padding:50px;text-align:center">
        <div style="font-size:100px">📱🚁🎮🌐</div>
        <p style="color:{THEME['text_dim']};font-size:24px;margin-top:20px">
            All of it? <span class="highlight">1s and 0s</span>. Let's go.
        </p>
    </div>
</div>"""

    return _base_html(scene["title"], body, clip_id, scene_id, css)


def build_binary_visual(scene: dict, clip: dict, clip_id: str, scene_id: str) -> str:
    """Scene 2: The Light Switch Analogy — Binary.

    Clips:
      0: Electricity in chips
      1: Light switch ON (1)
      2: Light switch OFF (0)
      3: Light switch comparison
      4: Base 10 (fingers)
      5: Base 2 counting 0, 1, 10, 11
      6: Why binary is logical
    """
    idx = clip["clip_index"]
    total = clip["total_clips"]
    css = CSS.format(font=THEME["font"], mono=THEME["mono"], w=WIDTH, h=HEIGHT,
                     bg=THEME["bg"], bg_grad=THEME["bg_grad"],
                     primary=THEME["primary"], secondary=THEME["secondary"],
                     accent=THEME["accent"], text=THEME["text"], text_dim=THEME["text_dim"],
                     code_bg=THEME["code_bg"], card_bg=THEME["card_bg"])

    if idx == 0:
        # Electricity in chips
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">⚡ Electricity Flows Inside the Chip</h2>
    <div class="fade-in-d1" style="max-width:1000px;margin:50px auto 0">
        <div class="card card-glow" style="padding:50px">
            <div style="position:relative;width:100%;height:300px;background:linear-gradient(135deg,#1a1a3a,#0a0a20);border-radius:16px;overflow:hidden">
                <div style="position:absolute;top:50%;left:10%;transform:translateY(-50%);font-size:80px">🔌</div>
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:200px;height:200px;background:linear-gradient(135deg,#1a1a3a,#0a0a20);border:3px solid {THEME['primary']};border-radius:20px;display:flex;align-items:center;justify-content:center">
                    <div style="font-size:80px">💾</div>
                </div>
                <div style="position:absolute;top:50%;right:10%;transform:translateY(-50%);font-size:80px">⚡</div>
                <div class="data-particle" style="animation-delay:0s"></div>
                <div class="data-particle" style="background:{THEME['secondary']};box-shadow:0 0 30px {THEME['secondary']};animation-delay:0.5s"></div>
                <div class="data-particle" style="background:{THEME['accent']};box-shadow:0 0 30px {THEME['accent']};animation-delay:1s"></div>
                <div class="data-particle" style="background:{THEME['primary']};animation-delay:1.5s"></div>
                <div class="data-particle" style="background:{THEME['secondary']};box-shadow:0 0 30px {THEME['secondary']};animation-delay:2s"></div>
            </div>
            <p style="color:{THEME['text_dim']};font-size:24px;margin-top:30px;text-align:center">
                Billions of tiny microscopic pathways carrying electricity
            </p>
        </div>
    </div>
</div>"""
    elif idx == 1:
        # Switch ON = 1
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:80px">
    <h2 class="fade-in">Switch UP = <span class="highlight">ON</span></h2>
    <div class="fade-in-d1" style="display:flex;align-items:center;justify-content:center;gap:80px;margin-top:60px">
        <div class="switch-container">
            <div class="switch-flip" style="top:30px"></div>
        </div>
        <div style="font-size:120px;color:{THEME['primary']};text-shadow:0 0 60px {THEME['primary']}">→</div>
        <div class="text-center">
            <div class="lightbulb">🔆</div>
            <div class="bit-counter" style="margin-top:20px;color:{THEME['secondary']};text-shadow:0 0 50px {THEME['secondary']}">1</div>
            <p style="color:{THEME['secondary']};font-size:32px;margin-top:12px;font-weight:700">ON</p>
        </div>
    </div>
    <div class="card fade-in-d2" style="max-width:600px;margin:60px auto 0;padding:30px;text-align:center">
        <p style="font-size:24px;line-height:1.5">Electricity flows → bulb lights up → <span class="highlight">state = 1</span></p>
    </div>
</div>"""
    elif idx == 2:
        # Switch OFF = 0
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:80px">
    <h2 class="fade-in">Switch DOWN = <span class="highlight">OFF</span></h2>
    <div class="fade-in-d1" style="display:flex;align-items:center;justify-content:center;gap:80px;margin-top:60px">
        <div class="switch-container">
            <div class="switch-flip" style="top:200px"></div>
        </div>
        <div style="font-size:120px;color:{THEME['text_dim']}">→</div>
        <div class="text-center">
            <div class="lightbulb" style="color:#2a2a4a">⚫</div>
            <div class="bit-counter" style="margin-top:20px;color:{THEME['text_dim']};text-shadow:0 0 50px #8888aa">0</div>
            <p style="color:{THEME['text_dim']};font-size:32px;margin-top:12px;font-weight:700">OFF</p>
        </div>
    </div>
    <div class="card fade-in-d2" style="max-width:600px;margin:60px auto 0;padding:30px;text-align:center">
        <p style="font-size:24px;line-height:1.5">No electricity → bulb dark → <span class="highlight">state = 0</span></p>
    </div>
</div>"""
    elif idx == 3:
        # Two states only
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">That's it. Only <span class="highlight">Two States</span></h2>
    <div class="fade-in-d1" style="max-width:900px;margin:60px auto 0">
        <div class="grid grid-2" style="gap:40px">
            <div class="card card-glow" style="text-align:center;padding:60px;border-color:{THEME['secondary']}">
                <div class="lightbulb">🔆</div>
                <div class="bit-counter" style="color:{THEME['secondary']};margin-top:20px">1</div>
                <h3 style="color:{THEME['secondary']};margin-top:15px">ON</h3>
            </div>
            <div class="card" style="text-align:center;padding:60px;border-color:{THEME['text_dim']}">
                <div style="font-size:140px;opacity:0.4">⚫</div>
                <div class="bit-counter" style="color:{THEME['text_dim']};margin-top:20px">0</div>
                <h3 style="color:{THEME['text_dim']};margin-top:15px">OFF</h3>
            </div>
        </div>
        <div class="card fade-in-d2" style="margin-top:40px;padding:30px;text-align:center">
            <p style="font-size:26px">
                A computer is a massive collection of <span class="highlight">billions</span> of these microscopic light switches.
            </p>
        </div>
    </div>
</div>"""
    elif idx == 4:
        # Base 10 = 10 fingers
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">Humans: <span class="highlight">Base 10</span> (10 Fingers)</h2>
    <div class="fade-in-d1" style="max-width:900px;margin:50px auto 0">
        <div class="card card-glow" style="padding:50px">
            <div style="display:flex;justify-content:center;gap:20px;margin-bottom:40px">
                {"".join(f'<div class="fade-in" style="font-size:80px;animation-delay:{i*0.1}s">☝️</div>' for i in range(10))}
            </div>
            <div class="binary-display" style="font-size:54px">1 → 2 → 3 → ... → 9 → 10</div>
            <p style="color:{THEME['text_dim']};font-size:24px;margin-top:30px;text-align:center">
                Count to 9, then add a new digit → <span class="highlight">10</span>
            </p>
        </div>
    </div>
</div>"""
    elif idx == 5:
        # Base 2 counting
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">Computers: <span class="highlight">Base 2</span> (Binary)</h2>
    <div class="fade-in-d1" style="max-width:1000px;margin:50px auto 0">
        <div class="card card-glow" style="padding:50px">
            <div style="display:flex;justify-content:center;gap:20px;margin-bottom:40px">
                <div class="binary-bit fade-in" style="animation-delay:0s">0</div>
                <div class="binary-bit fade-in" style="animation-delay:0.2s">1</div>
                <div class="binary-bit fade-in" style="animation-delay:0.4s">10</div>
                <div class="binary-bit fade-in" style="animation-delay:0.6s">11</div>
                <div class="binary-bit fade-in" style="animation-delay:0.8s">100</div>
            </div>
            <div style="text-align:center;margin-top:30px">
                <p style="color:{THEME['text_dim']};font-size:24px">
                    Run out of digits? Add a new digit to the <span class="highlight">left</span>!
                </p>
            </div>
            <div style="display:flex;justify-content:space-around;margin-top:40px;font-size:22px">
                <div class="fade-in" style="animation-delay:1s;text-align:center">
                    <div style="color:{THEME['secondary']};font-family:{THEME['mono']};font-size:36px">10</div>
                    <div style="color:{THEME['text_dim']};margin-top:8px">= 2</div>
                </div>
                <div class="fade-in" style="animation-delay:1.2s;text-align:center">
                    <div style="color:{THEME['secondary']};font-family:{THEME['mono']};font-size:36px">11</div>
                    <div style="color:{THEME['text_dim']};margin-top:8px">= 3</div>
                </div>
                <div class="fade-in" style="animation-delay:1.4s;text-align:center">
                    <div style="color:{THEME['secondary']};font-family:{THEME['mono']};font-size:36px">100</div>
                    <div style="color:{THEME['text_dim']};margin-top:8px">= 4</div>
                </div>
            </div>
        </div>
    </div>
</div>"""
    else:
        # Why binary is logical
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:80px">
    <div class="card card-glow fade-in" style="max-width:900px;padding:60px">
        <div style="font-size:100px;text-align:center">🧠</div>
        <h2 class="fade-in-d1" style="margin-top:30px">Strange to us.<br>Logical to computers.</h2>
        <p style="color:{THEME['text_dim']};font-size:26px;margin-top:40px;line-height:1.6">
            A chip is built from <span class="highlight">transistors</span> — tiny switches that can only be ON or OFF. Binary is the <span class="highlight">native language</span> of the machine.
        </p>
    </div>
</div>"""

    return _base_html(scene["title"], body, clip_id, scene_id, css)


def build_ascii_rgb_visual(scene: dict, clip: dict, clip_id: str, scene_id: str) -> str:
    """Scene 3: Representing Letters and Colors."""
    idx = clip["clip_index"]
    css = CSS.format(font=THEME["font"], mono=THEME["mono"], w=WIDTH, h=HEIGHT,
                     bg=THEME["bg"], bg_grad=THEME["bg_grad"],
                     primary=THEME["primary"], secondary=THEME["secondary"],
                     accent=THEME["accent"], text=THEME["text"], text_dim=THEME["text_dim"],
                     code_bg=THEME["code_bg"], card_bg=THEME["card_bg"])

    if idx == 0:
        # Typing on keyboard
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:80px">
    <h2 class="fade-in">⌨️ Type a Letter</h2>
    <div class="fade-in-d1" style="margin-top:80px">
        <div class="card card-glow" style="max-width:600px;margin:0 auto;padding:60px">
            <div style="font-size:200px;font-weight:900;color:{THEME['primary']};font-family:{THEME['mono']};text-shadow:0 0 60px {THEME['primary']}88;animation:bitPulse 1.5s ease-in-out infinite">
                A
            </div>
            <p style="color:{THEME['text_dim']};font-size:24px;margin-top:30px">
                Keyboard key 'A' pressed
            </p>
        </div>
    </div>
</div>"""
    elif idx == 1:
        # Letter → number
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">A → ASCII Code</h2>
    <div class="fade-in-d1" style="display:flex;align-items:center;justify-content:center;gap:80px;margin-top:80px">
        <div class="card card-glow" style="padding:60px;text-align:center">
            <div style="font-size:180px;font-weight:900;color:{THEME['primary']};font-family:{THEME['mono']}">A</div>
            <p style="color:{THEME['text_dim']};margin-top:20px;font-size:24px">Letter</p>
        </div>
        <div style="font-size:120px;color:{THEME['secondary']};animation:arrowRight 1.5s ease-in-out infinite">→</div>
        <div class="card card-glow" style="padding:60px;text-align:center;border-color:{THEME['secondary']}">
            <div style="font-size:180px;font-weight:900;color:{THEME['secondary']};font-family:{THEME['mono']};text-shadow:0 0 60px {THEME['secondary']}88">65</div>
            <p style="color:{THEME['text_dim']};margin-top:20px;font-size:24px">ASCII Number</p>
        </div>
    </div>
</div>"""
    elif idx == 2:
        # Number → binary
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">65 → Binary</h2>
    <div class="fade-in-d1" style="display:flex;align-items:center;justify-content:center;gap:80px;margin-top:80px">
        <div class="card card-glow" style="padding:60px;text-align:center;border-color:{THEME['secondary']}">
            <div style="font-size:180px;font-weight:900;color:{THEME['secondary']};font-family:{THEME['mono']};text-shadow:0 0 60px {THEME['secondary']}88">65</div>
        </div>
        <div style="font-size:120px;color:{THEME['accent']};animation:arrowRight 1.5s ease-in-out infinite">→</div>
        <div class="card card-glow" style="padding:50px;text-align:center;border-color:{THEME['accent']}">
            <div style="font-family:{THEME['mono']};font-size:80px;font-weight:900;color:#fab1a0;letter-spacing:8px;text-shadow:0 0 60px rgba(250,177,160,0.8)">
                01000001
            </div>
        </div>
    </div>
    <div class="card fade-in-d2" style="max-width:700px;margin:60px auto 0;padding:30px;text-align:center">
        <p style="font-size:24px">Every letter has a number → every number has a binary</p>
    </div>
</div>"""
    elif idx == 3:
        # ASCII table preview
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:40px">
    <h2 class="fade-in">🔤 The ASCII Code</h2>
    <div class="fade-in-d1" style="max-width:1000px;margin:40px auto 0">
        <div class="card card-glow" style="padding:40px">
            <div class="grid" style="grid-template-columns:repeat(6,1fr);gap:16px">
                {"".join(f'''<div class="fade-in" style="animation-delay:{i*0.05}s"><div class="card" style="padding:18px;text-align:center;animation:none">
                    <div style="font-family:{THEME['mono']};font-size:48px;font-weight:900;color:{THEME['primary']}">{chr(65+i)}</div>
                    <div style="font-family:{THEME['mono']};font-size:18px;color:{THEME['text_dim']};margin-top:6px">{65+i}</div>
                </div></div>''' for i in range(12))}
            </div>
            <p style="color:{THEME['text_dim']};font-size:22px;margin-top:30px;text-align:center">
                A=65, B=66, C=67... <span class="highlight">A secret code</span> for letters
            </p>
        </div>
    </div>
</div>"""
    elif idx == 4:
        # RGB intro
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">🎨 Every Pixel = 3 Tiny Lights</h2>
    <div class="fade-in-d1" style="margin-top:60px">
        <div style="display:flex;justify-content:center;gap:60px;align-items:center">
            <div class="fade-in" style="animation-delay:0.2s;text-align:center">
                <div style="width:180px;height:180px;border-radius:50%;background:radial-gradient(circle,#ff4444,#cc0000);box-shadow:0 0 80px rgba(255,68,68,0.8);animation:bitPulse 2s ease-in-out infinite"></div>
                <p style="font-size:48px;font-weight:900;color:#ff4444;margin-top:20px;font-family:{THEME['mono']};text-shadow:0 0 30px rgba(255,68,68,0.8)">RED</p>
            </div>
            <div class="fade-in" style="animation-delay:0.4s;text-align:center">
                <div style="width:180px;height:180px;border-radius:50%;background:radial-gradient(circle,#44ff44,#00cc00);box-shadow:0 0 80px rgba(68,255,68,0.8);animation:bitPulse 2s ease-in-out 0.3s infinite"></div>
                <p style="font-size:48px;font-weight:900;color:#44ff44;margin-top:20px;font-family:{THEME['mono']};text-shadow:0 0 30px rgba(68,255,68,0.8)">GREEN</p>
            </div>
            <div class="fade-in" style="animation-delay:0.6s;text-align:center">
                <div style="width:180px;height:180px;border-radius:50%;background:radial-gradient(circle,#4488ff,#0044cc);box-shadow:0 0 80px rgba(68,136,255,0.8);animation:bitPulse 2s ease-in-out 0.6s infinite"></div>
                <p style="font-size:48px;font-weight:900;color:#4488ff;margin-top:20px;font-family:{THEME['mono']};text-shadow:0 0 30px rgba(68,136,255,0.8)">BLUE</p>
            </div>
        </div>
    </div>
    <div class="card fade-in-d2" style="max-width:700px;margin:60px auto 0;padding:30px;text-align:center">
        <p style="font-size:26px">RGB = <span class="highlight">R</span>ed + <span class="highlight">G</span>reen + <span class="highlight">B</span>lue</p>
    </div>
</div>"""
    elif idx == 5:
        # RGB pixel values
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">Orange = R:255, G:100, B:0</h2>
    <div class="fade-in-d1" style="max-width:950px;margin:50px auto 0">
        <div class="card card-glow" style="padding:50px">
            <div style="display:flex;justify-content:center;gap:50px;margin-bottom:50px">
                <div class="fade-in" style="animation-delay:0.2s;text-align:center">
                    <div style="width:140px;height:140px;border-radius:50%;background:rgb(255,100,0);box-shadow:0 0 80px rgba(255,100,0,0.8);animation:bitPulse 2s ease-in-out infinite"></div>
                    <p style="font-family:{THEME['mono']};font-size:32px;color:#ff6b6b;margin-top:16px;font-weight:900">R: 255</p>
                </div>
                <div class="fade-in" style="animation-delay:0.4s;text-align:center">
                    <div style="width:140px;height:140px;border-radius:50%;background:rgb(0,200,100);box-shadow:0 0 80px rgba(0,200,100,0.8);animation:bitPulse 2s ease-in-out 0.3s infinite"></div>
                    <p style="font-family:{THEME['mono']};font-size:32px;color:#51cf66;margin-top:16px;font-weight:900">G: 100</p>
                </div>
                <div class="fade-in" style="animation-delay:0.6s;text-align:center">
                    <div style="width:140px;height:140px;border-radius:50%;background:rgb(0,50,255);box-shadow:0 0 80px rgba(0,50,255,0.8);animation:bitPulse 2s ease-in-out 0.6s infinite"></div>
                    <p style="font-family:{THEME['mono']};font-size:32px;color:#74c0fc;margin-top:16px;font-weight:900">B: 0</p>
                </div>
            </div>
            <div class="binary-display" style="font-size:22px;letter-spacing:6px">
                11111111 01100100 00000000
            </div>
            <p style="color:{THEME['text_dim']};font-size:22px;margin-top:30px;text-align:center">
                Each number → binary → pixel lights up
            </p>
        </div>
    </div>
</div>"""
    elif idx == 6:
        # Photos / videos = 1s and 0s
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">Every Photo & Video = 1s and 0s</h2>
    <div class="fade-in-d1" style="max-width:900px;margin:50px auto 0">
        <div class="grid grid-3" style="gap:24px">
            <div class="card card-tilt" style="padding:40px;text-align:center">
                <div style="font-size:80px">📸</div>
                <h3 style="color:{THEME['primary']};font-size:24px;margin-top:12px">Photos</h3>
                <p style="color:{THEME['text_dim']};font-size:18px;margin-top:8px">Millions of pixels × 3 numbers</p>
            </div>
            <div class="card card-tilt" style="padding:40px;text-align:center;animation-delay:0.2s">
                <div style="font-size:80px">🎬</div>
                <h3 style="color:{THEME['secondary']};font-size:24px;margin-top:12px">Videos</h3>
                <p style="color:{THEME['text_dim']};font-size:18px;margin-top:8px">30 images per second</p>
            </div>
            <div class="card card-tilt" style="padding:40px;text-align:center;animation-delay:0.4s">
                <div style="font-size:80px">🎮</div>
                <h3 style="color:{THEME['accent']};font-size:24px;margin-top:12px">Games</h3>
                <p style="color:{THEME['text_dim']};font-size:18px;margin-top:8px">60 images per second</p>
            </div>
        </div>
        <div class="card card-glow fade-in-d2" style="margin-top:40px;padding:30px;text-align:center">
            <p style="font-size:26px">
                <span class="highlight">Billions</span> of 1s and 0s flashing on and off
            </p>
        </div>
    </div>
</div>"""
    else:
        # Summary
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:80px">
    <div class="card card-glow fade-in" style="max-width:900px;padding:50px">
        <h2 class="fade-in-d1">📥 Everything Translates</h2>
        <div class="fade-in-d2" style="margin-top:40px;text-align:left">
            <div class="code-block" style="font-size:24px">
                <span class="cmt"># Type 'A' on keyboard</span><br>
                A<br>
                <span class="cmt"># → ASCII number</span><br>
                65<br>
                <span class="cmt"># → Binary</span><br>
                <span class="num">01000001</span><br>
                <span class="cmt"># → Computer stores it</span>
            </div>
        </div>
    </div>
</div>"""

    return _base_html(scene["title"], body, clip_id, scene_id, css)


def build_algorithm_visual(scene: dict, clip: dict, clip_id: str, scene_id: str) -> str:
    """Scene 4: Algorithmic Thinking & Pseudocode."""
    idx = clip["clip_index"]
    css = CSS.format(font=THEME["font"], mono=THEME["mono"], w=WIDTH, h=HEIGHT,
                     bg=THEME["bg"], bg_grad=THEME["bg_grad"],
                     primary=THEME["primary"], secondary=THEME["secondary"],
                     accent=THEME["accent"], text=THEME["text"], text_dim=THEME["text_dim"],
                     code_bg=THEME["code_bg"], card_bg=THEME["card_bg"])

    if idx == 0:
        # Confused person → recipe
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:80px">
    <h2 class="fade-in">😵 Confused? Meet Recipes</h2>
    <div class="fade-in-d1" style="display:flex;align-items:center;justify-content:center;gap:80px;margin-top:80px">
        <div class="card card-tilt" style="text-align:center;padding:50px">
            <div style="font-size:180px">😵‍💻</div>
            <p style="color:{THEME['text_dim']};font-size:22px;margin-top:20px">"How do I solve this?"</p>
        </div>
        <div style="font-size:120px;color:{THEME['primary']};animation:arrowRight 1.5s ease-in-out infinite">→</div>
        <div class="card card-glow" style="text-align:center;padding:50px">
            <div style="font-size:180px">👨‍🍳</div>
            <p style="color:{THEME['secondary']};font-size:22px;margin-top:20px">Chef with a recipe</p>
        </div>
    </div>
</div>"""
    elif idx == 1:
        # Recipe card
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">📋 A Recipe = Algorithm</h2>
    <div class="fade-in-d1" style="max-width:700px;margin:50px auto 0">
        <div class="card card-glow" style="padding:50px;text-align:left">
            <div style="display:flex;align-items:center;gap:20px;margin-bottom:24px">
                <div style="font-size:80px">🥚</div>
                <div class="code-block" style="font-size:24px;flex:1;padding:16px 24px">
                    <span class="cmt">Step 1:</span> Mix eggs and sugar
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:20px;margin-bottom:24px">
                <div style="font-size:80px">🥣</div>
                <div class="code-block" style="font-size:24px;flex:1;padding:16px 24px">
                    <span class="cmt">Step 2:</span> Add flour
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:20px">
                <div style="font-size:80px">🎂</div>
                <div class="code-block" style="font-size:24px;flex:1;padding:16px 24px">
                    <span class="cmt">Step 3:</span> Bake at 350°F
                </div>
            </div>
        </div>
    </div>
</div>"""
    elif idx == 2:
        # Algorithm definition
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:80px">
    <h2 class="fade-in">🧠 Algorithm = Step-by-Step</h2>
    <div class="fade-in-d1" style="max-width:850px;margin:50px auto 0">
        <div class="card card-glow" style="padding:50px">
            <h3 style="color:{THEME['primary']};text-align:center;margin-bottom:30px;font-size:36px">A set of instructions to solve a problem</h3>
            <div style="display:flex;justify-content:space-around;margin-top:40px">
                <div class="fade-in" style="animation-delay:0.2s;text-align:center">
                    <div style="font-size:80px">1️⃣</div>
                    <p style="color:{THEME['text_dim']};margin-top:12px;font-size:20px">Step 1</p>
                </div>
                <div class="fade-in" style="animation-delay:0.4s;text-align:center">
                    <div style="font-size:80px">2️⃣</div>
                    <p style="color:{THEME['text_dim']};margin-top:12px;font-size:20px">Step 2</p>
                </div>
                <div class="fade-in" style="animation-delay:0.6s;text-align:center">
                    <div style="font-size:80px">3️⃣</div>
                    <p style="color:{THEME['text_dim']};margin-top:12px;font-size:20px">Step 3</p>
                </div>
            </div>
            <p style="color:{THEME['warning']};font-size:24px;margin-top:40px;text-align:center;font-weight:600">
                ⚠️ Mix them up → you get a mess
            </p>
        </div>
    </div>
</div>"""
    elif idx == 3:
        # Pseudocode intro
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">📝 Pseudocode = Plain English Logic</h2>
    <div class="fade-in-d1" style="max-width:1000px;margin:50px auto 0">
        <div class="grid grid-2" style="gap:32px">
            <div class="card" style="padding:40px;text-align:center">
                <h3 style="color:{THEME['text_dim']};margin-bottom:20px">Plain English</h3>
                <p style="font-size:24px;line-height:1.6">"Ask the user for a password. If it's correct, log them in. If not, show an error."</p>
            </div>
            <div class="card card-glow" style="padding:40px">
                <h3 style="color:{THEME['primary']};margin-bottom:20px;text-align:center">Structured</h3>
                <div class="code-block" style="font-size:22px">
                    <span class="kw">ASK</span> user <span class="kw">FOR</span> password<br>
                    <span class="kw">IF</span> password == correct<br>
                    &nbsp;&nbsp;&nbsp;&nbsp;<span class="kw">THEN</span> log <span class="kw">IN</span><br>
                    <span class="kw">ELSE</span><br>
                    &nbsp;&nbsp;&nbsp;&nbsp;show <span class="str">"Error"</span>
                </div>
            </div>
        </div>
    </div>
</div>"""
    elif idx == 4:
        # Flowchart
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:40px">
    <h2 class="fade-in">🔀 Flowchart: Login Program</h2>
    <div class="fade-in-d1" style="max-width:700px;margin:50px auto 0">
        <div class="card card-glow" style="padding:50px">
            <div class="flow-node flow-process" style="margin:0 auto;background:linear-gradient(135deg,{THEME['primary']}55,{THEME['primary']}22);border:2px solid {THEME['primary']};color:{THEME['primary']}">📋 Ask for Password</div>
            <div class="flow-arrow">↓</div>
            <div class="flow-node flow-decision" style="margin:0 auto;background:linear-gradient(135deg,{THEME['accent']}55,{THEME['accent']}22);border:2px solid {THEME['accent']};color:{THEME['accent']};clip-path:polygon(50% 0%,100% 50%,50% 100%,0% 50%);padding:40px 60px">
                <div style="margin-top:30px">Is it correct?</div>
            </div>
            <div style="display:flex;gap:80px;justify-content:center;margin-top:30px">
                <div>
                    <div style="color:{THEME['secondary']};font-size:22px;font-weight:700">← Yes</div>
                    <div class="flow-node flow-process" style="background:linear-gradient(135deg,{THEME['secondary']}55,{THEME['secondary']}22);border:2px solid {THEME['secondary']};color:{THEME['secondary']}">✅ Log In</div>
                </div>
                <div>
                    <div style="color:{THEME['warning']};font-size:22px;font-weight:700">← No</div>
                    <div class="flow-node flow-decision" style="background:linear-gradient(135deg,{THEME['warning']}55,{THEME['warning']}22);border:2px solid {THEME['warning']};color:{THEME['warning']}">⚠️ Show Error</div>
                </div>
            </div>
        </div>
    </div>
</div>"""
    elif idx == 5:
        # Conditions
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">⚖️ Conditions = Decisions</h2>
    <div class="fade-in-d1" style="max-width:800px;margin:50px auto 0">
        <div class="card card-glow" style="padding:50px">
            <div class="code-block" style="font-size:32px;text-align:center">
                <span class="kw">IF</span> condition <span class="kw">IS</span> true<br>
                &nbsp;&nbsp;&nbsp;&nbsp;<span class="fn">do_this</span>()<br>
                <span class="kw">ELSE</span><br>
                    &nbsp;&nbsp;&nbsp;&nbsp;<span class="fn">do_that</span>()
            </div>
            <div style="margin-top:40px;display:flex;justify-content:space-around">
                <div class="fade-in" style="animation-delay:0.2s;text-align:center">
                    <div style="font-size:80px">✅</div>
                    <p style="color:{THEME['secondary']};font-size:24px;margin-top:12px;font-weight:600">This</p>
                </div>
                <div class="fade-in" style="animation-delay:0.4s;text-align:center">
                    <div style="font-size:80px">❌</div>
                    <p style="color:{THEME['accent']};font-size:24px;margin-top:12px;font-weight:600">That</p>
                </div>
            </div>
        </div>
    </div>
</div>"""
    else:
        # Wrap-up
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:80px">
    <div class="card card-glow fade-in" style="max-width:900px;padding:50px">
        <h2 class="fade-in-d1">🎯 The Algorithm Mindset</h2>
        <div class="fade-in-d2" style="margin-top:40px">
            <div class="code-block" style="font-size:26px;text-align:left">
                <span class="cmt"># Break any problem into steps</span><br>
                1. <span class="kw">Understand</span> what you want<br>
                2. <span class="kw">Plan</span> the steps<br>
                3. <span class="kw">Write</span> pseudocode<br>
                4. <span class="kw">Translate</span> to code<br>
                5. <span class="kw">Test</span> and fix
            </div>
        </div>
    </div>
</div>"""

    return _base_html(scene["title"], body, clip_id, scene_id, css)


def build_io_function_loop_visual(scene: dict, clip: dict, clip_id: str, scene_id: str) -> str:
    """Scene 5: Inputs, Outputs, Loops, Functions."""
    idx = clip["clip_index"]
    css = CSS.format(font=THEME["font"], mono=THEME["mono"], w=WIDTH, h=HEIGHT,
                     bg=THEME["bg"], bg_grad=THEME["bg_grad"],
                     primary=THEME["primary"], secondary=THEME["secondary"],
                     accent=THEME["accent"], text=THEME["text"], text_dim=THEME["text_dim"],
                     code_bg=THEME["code_bg"], card_bg=THEME["card_bg"])

    if idx == 0:
        # Input/Output factory
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:80px">
    <h2 class="fade-in">📦📦🏭📦📦 Input → Function → Output</h2>
    <div class="fade-in-d1" style="display:flex;align-items:center;justify-content:center;gap:40px;margin-top:80px">
        <div class="pipeline-box" style="background:linear-gradient(135deg,{THEME['primary']}55,{THEME['primary']}22);border:3px solid {THEME['primary']}">
            📦
        </div>
        <div class="flow-arrow">→</div>
        <div class="pipeline-box" style="background:linear-gradient(135deg,{THEME['secondary']}55,{THEME['secondary']}22);border:3px solid {THEME['secondary']};font-size:120px">
            ⚙️
        </div>
        <div class="flow-arrow">→</div>
        <div class="pipeline-box" style="background:linear-gradient(135deg,{THEME['accent']}55,{THEME['accent']}22);border:3px solid {THEME['accent']}">
            ✨
        </div>
    </div>
    <div style="display:flex;justify-content:center;gap:200px;margin-top:30px">
        <div class="fade-in" style="animation-delay:0.2s">
            <span style="color:{THEME['primary']};font-size:32px;font-weight:700">INPUT</span>
        </div>
        <div class="fade-in" style="animation-delay:0.4s">
            <span style="color:{THEME['secondary']};font-size:32px;font-weight:700">FUNCTION</span>
        </div>
        <div class="fade-in" style="animation-delay:0.6s">
            <span style="color:{THEME['accent']};font-size:32px;font-weight:700">OUTPUT</span>
        </div>
    </div>
</div>"""
    elif idx == 1:
        # Function code
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">⚙️ Function = Reusable Code Block</h2>
    <div class="fade-in-d1" style="max-width:900px;margin:50px auto 0">
        <div class="card card-glow" style="padding:40px">
            <div class="code-block" style="font-size:28px">
                <span class="kw">def</span> <span class="fn">make_coffee</span>(sugar, milk):<br>
                &nbsp;&nbsp;&nbsp;&nbsp;<span class="cmt"># takes input</span><br>
                &nbsp;&nbsp;&nbsp;&nbsp;cup = <span class="str">"coffee"</span><br>
                &nbsp;&nbsp;&nbsp;&nbsp;cup = cup + sugar + milk<br>
                &nbsp;&nbsp;&nbsp;&nbsp;<span class="kw">return</span> cup<br>
                <br>
                <span class="cmt"># Reuse it 1 million times</span><br>
                morning = <span class="fn">make_coffee</span>(<span class="str">"yes"</span>, <span class="str">"yes"</span>)
            </div>
        </div>
    </div>
</div>"""
    elif idx == 2:
        # Loop hamster
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">🔄 Loops = Do It Again & Again</h2>
    <div class="fade-in-d1" style="display:flex;align-items:center;justify-content:center;gap:80px;margin-top:80px">
        <div class="wheel"></div>
        <div class="text-center">
            <h3 style="color:{THEME['primary']};font-size:36px">Computers are</h3>
            <div style="font-size:48px;font-weight:900;color:{THEME['accent']};margin-top:20px;text-shadow:0 0 50px {THEME['accent']}">FAST</div>
            <div style="font-size:48px;font-weight:900;color:{THEME['warning']};margin-top:20px;text-shadow:0 0 50px {THEME['warning']}">DUMB</div>
        </div>
    </div>
</div>"""
    elif idx == 3:
        # Loop code
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">Infinite Energy for Repetitive Tasks</h2>
    <div class="fade-in-d1" style="max-width:900px;margin:50px auto 0">
        <div class="card card-glow" style="padding:40px">
            <div class="code-block" style="font-size:30px">
                <span class="kw">for</span> i <span class="kw">in</span> <span class="fn">range</span>(100):<br>
                &nbsp;&nbsp;&nbsp;&nbsp;<span class="cmt"># Do this 100 times</span><br>
                &nbsp;&nbsp;&nbsp;&nbsp;<span class="fn">do_task</span>()
            </div>
            <div style="margin-top:40px;text-align:center">
                <div class="binary-display" style="font-size:36px">
                    1 → 2 → 3 → ... → 100 → DONE
                </div>
            </div>
        </div>
    </div>
</div>"""
    elif idx == 4:
        # Scratch blocks
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">🧱 Visual Programming: Scratch</h2>
    <div class="fade-in-d1" style="max-width:700px;margin:50px auto 0">
        <div style="display:flex;flex-direction:column;gap:14px;align-items:flex-start">
            <div class="scratch-block" style="background:#4d97ff;width:600px;animation-delay:0.1s">📋 when [green flag] clicked</div>
            <div class="scratch-block" style="background:#4d97ff;width:540px;margin-left:60px;animation-delay:0.3s">🔁 repeat (10)</div>
            <div class="scratch-block" style="background:#af6eff;width:480px;margin-left:120px;animation-delay:0.5s">🐱 move (10) steps</div>
            <div class="scratch-block" style="background:#af6eff;width:480px;margin-left:120px;animation-delay:0.7s">🔊 play sound [Meow]</div>
            <div class="scratch-block" style="background:#ffab19;color:black;width:540px;margin-left:60px;animation-delay:0.9s">if ◇ <span style="color:white">touching edge?</span></div>
            <div class="scratch-block" style="background:#ffab19;color:black;width:480px;margin-left:120px;animation-delay:1.1s">turn ↺ (15) degrees</div>
        </div>
    </div>
</div>"""
    elif idx == 5:
        # All together
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:40px">
    <h2 class="fade-in">🧬 The DNA of Every Program</h2>
    <div class="fade-in-d1" style="max-width:1000px;margin:50px auto 0">
        <div class="grid grid-3" style="gap:24px">
            <div class="card card-tilt" style="padding:36px;text-align:center">
                <div style="font-size:70px">📥</div>
                <h3 style="color:{THEME['primary']};font-size:24px;margin-top:12px">Inputs</h3>
            </div>
            <div class="card card-tilt" style="padding:36px;text-align:center;animation-delay:0.1s">
                <div style="font-size:70px">📤</div>
                <h3 style="color:{THEME['secondary']};font-size:24px;margin-top:12px">Outputs</h3>
            </div>
            <div class="card card-tilt" style="padding:36px;text-align:center;animation-delay:0.2s">
                <div style="font-size:70px">⚙️</div>
                <h3 style="color:{THEME['accent']};font-size:24px;margin-top:12px">Functions</h3>
            </div>
            <div class="card card-tilt" style="padding:36px;text-align:center;animation-delay:0.3s">
                <div style="font-size:70px">⚖️</div>
                <h3 style="color:{THEME['warning']};font-size:24px;margin-top:12px">Conditions</h3>
            </div>
            <div class="card card-tilt" style="padding:36px;text-align:center;animation-delay:0.4s">
                <div style="font-size:70px">🔄</div>
                <h3 style="color:{THEME['primary']};font-size:24px;margin-top:12px">Loops</h3>
            </div>
            <div class="card card-tilt" style="padding:36px;text-align:center;animation-delay:0.5s">
                <div style="font-size:70px">📊</div>
                <h3 style="color:{THEME['secondary']};font-size:24px;margin-top:12px">Variables</h3>
            </div>
        </div>
    </div>
</div>"""
    else:
        # Wrap-up
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:80px">
    <div class="card card-glow fade-in" style="max-width:900px;padding:50px">
        <h2 class="fade-in-d1">🚀 From Phones to Rockets</h2>
        <div class="fade-in-d2" style="margin-top:40px;display:flex;justify-content:space-around;align-items:center">
            <div style="text-align:center">
                <div style="font-size:100px">📱</div>
                <p style="color:{THEME['text_dim']};margin-top:16px;font-size:20px">Phone OS</p>
            </div>
            <div style="font-size:60px;color:{THEME['primary']}">→</div>
            <div style="text-align:center">
                <div style="font-size:100px">🚀</div>
                <p style="color:{THEME['text_dim']};margin-top:16px;font-size:20px">Rocket Landing</p>
            </div>
            <div style="font-size:60px;color:{THEME['primary']}">→</div>
            <div style="text-align:center">
                <div style="font-size:100px">🤖</div>
                <p style="color:{THEME['text_dim']};margin-top:16px;font-size:20px">AI Models</p>
            </div>
        </div>
        <p style="color:{THEME['text']};font-size:26px;margin-top:40px;text-align:center">
            All of it: <span class="highlight">inputs, outputs, functions, conditions, loops</span>
        </p>
    </div>
</div>"""

    return _base_html(scene["title"], body, clip_id, scene_id, css)


def build_outro_visual(scene: dict, clip: dict, clip_id: str, scene_id: str) -> str:
    """Scene 6: Conclusion & Assignment."""
    idx = clip["clip_index"]
    css = CSS.format(font=THEME["font"], mono=THEME["mono"], w=WIDTH, h=HEIGHT,
                     bg=THEME["bg"], bg_grad=THEME["bg_grad"],
                     primary=THEME["primary"], secondary=THEME["secondary"],
                     accent=THEME["accent"], text=THEME["text"], text_dim=THEME["text_dim"],
                     code_bg=THEME["code_bg"], card_bg=THEME["card_bg"])

    if idx == 0:
        # Recap
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">🎉 What You Learned</h2>
    <div class="fade-in-d1" style="max-width:1000px;margin:50px auto 0">
        <div class="grid grid-2" style="gap:24px">
            <div class="card card-tilt" style="padding:36px;text-align:center;border-color:{THEME['primary']}">
                <div style="font-size:70px">💡</div>
                <h3 style="color:{THEME['primary']};font-size:26px;margin-top:12px">Binary</h3>
                <p style="color:{THEME['text_dim']};font-size:18px;margin-top:8px">1s and 0s = ON/OFF</p>
            </div>
            <div class="card card-tilt" style="padding:36px;text-align:center;border-color:{THEME['secondary']};animation-delay:0.1s">
                <div style="font-size:70px">🔤</div>
                <h3 style="color:{THEME['secondary']};font-size:26px;margin-top:12px">ASCII</h3>
                <p style="color:{THEME['text_dim']};font-size:18px;margin-top:8px">Letters → numbers → binary</p>
            </div>
            <div class="card card-tilt" style="padding:36px;text-align:center;border-color:{THEME['accent']};animation-delay:0.2s">
                <div style="font-size:70px">🎨</div>
                <h3 style="color:{THEME['accent']};font-size:26px;margin-top:12px">RGB</h3>
                <p style="color:{THEME['text_dim']};font-size:18px;margin-top:8px">Pixels = 3 lights</p>
            </div>
            <div class="card card-tilt" style="padding:36px;text-align:center;border-color:{THEME['warning']};animation-delay:0.3s">
                <div style="font-size:70px">🧠</div>
                <h3 style="color:{THEME['warning']};font-size:26px;margin-top:12px">Algorithms</h3>
                <p style="color:{THEME['text_dim']};font-size:18px;margin-top:8px">Steps + decisions</p>
            </div>
        </div>
    </div>
</div>"""
    elif idx == 1:
        # Assignment
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <h2 class="fade-in">📝 Your Assignment</h2>
    <div class="fade-in-d1" style="max-width:900px;margin:50px auto 0">
        <div class="card card-glow" style="padding:50px">
            <div style="font-size:100px;text-align:center">🥪</div>
            <h3 style="color:{THEME['primary']};text-align:center;margin-top:30px;font-size:42px">
                Write Pseudocode for a<br>Peanut Butter & Jelly Sandwich
            </h3>
            <div class="code-block fade-in-d2" style="margin-top:40px;font-size:24px">
                <span class="cmt"># Remember: computers are dumb!</span><br>
                <span class="kw">GET</span> bread, peanut_butter, jelly, knife<br>
                <span class="kw">PUT</span> bread on plate<br>
                <span class="kw">OPEN</span> peanut_butter jar<br>
                ...
            </div>
            <p style="color:{THEME['warning']};font-size:22px;margin-top:30px;text-align:center">
                ⚠️ Be EXPLICIT. If you don't say "open the jar", it won't.
            </p>
        </div>
    </div>
</div>"""
    else:
        # Next module preview
        body = f"""<div class="center" style="position:relative;z-index:2;padding-top:60px">
    <div class="badge fade-in">MODULE COMPLETE</div>
    <h1 class="fade-in-d1" style="margin-top:40px;font-size:80px">Ready for <span class="highlight">Code</span>?</h1>
    <div class="fade-in-d2" style="max-width:800px;margin:50px auto 0">
        <div class="card card-glow" style="padding:50px;text-align:center">
            <h2 style="margin-bottom:30px">Next Module</h2>
            <div style="font-size:120px">⚡</div>
            <h3 style="color:{THEME['primary']};font-size:48px;margin-top:20px">The C Programming Language</h3>
            <div class="code-block" style="margin-top:30px;font-size:28px;text-align:left">
                <span class="cmt">// Your first C program</span><br>
                <span class="kw">#include</span> <span class="str">&lt;stdio.h&gt;</span><br>
                <span class="kw">int</span> <span class="fn">main</span>() {{<br>
                &nbsp;&nbsp;&nbsp;&nbsp;<span class="fn">printf</span>(<span class="str">"Hello, World!"</span>);<br>
                &nbsp;&nbsp;&nbsp;&nbsp;<span class="kw">return</span> <span class="num">0</span>;<br>
                }}
            </div>
        </div>
    </div>
    <div class="fade-in-d3" style="margin-top:50px">
        <div class="badge" style="background:linear-gradient(135deg,{THEME['secondary']},{THEME['primary']})">See you in Module 2</div>
    </div>
</div>"""

    return _base_html(scene["title"], body, clip_id, scene_id, css)


def _infer_visual_spec_from_narration(scene: dict, clip: dict) -> dict:
    """Intelligently infers 1080p visual specs for ANY topic/script based on semantic narration cues."""
    narration = scene.get("narration", "") or clip.get("narration", "")
    title = scene.get("title", "Core Concept")
    lower = (title + " " + narration).lower()
    
    # 1. Code walkthrough detection
    if any(k in lower for k in ["code", "payload", "json", "syntax", "function", "def ", "class ", "jwt payload", "programming"]):
        snippet = "{\n  \"status\": \"authenticated\",\n  \"role\": \"admin\",\n  \"expires_in\": 900,\n  \"scope\": [\"read\", \"write\"]\n}"
        if "jwt" in lower:
            snippet = "{\n  \"sub\": \"usr_882910\",\n  \"jti\": \"e4a19b88-1c49-4320\",\n  \"iat\": 1727800000,\n  \"exp\": 1727800900,\n  \"role\": \"engineer\"\n}"
        return {
            "visual_type": "code_walkthrough",
            "title": title,
            "subtitle": "Syntax & Implementation Walkthrough",
            "code_snippet": snippet,
            "code_language": "json",
            "highlight_lines": [2, 3],
        }
        
    # 2. Comparison detection (A vs B, versus, difference)
    if any(k in lower for k in [" vs ", "versus", "comparison", "difference", "compare", "access token vs", "state vs stateless"]):
        parts = [p.strip() for p in re.split(r'\s+(?:vs|versus)\s+', title, flags=re.IGNORECASE)]
        item1 = parts[0] if len(parts) > 0 else "Approach A"
        item2 = parts[1] if len(parts) > 1 else "Approach B"
        return {
            "visual_type": "comparison",
            "title": title,
            "subtitle": "Comparative Architecture & Trade-offs",
            "accent_color": "#7c83ff",
            "comparison_items": [
                {"title": item1, "subtitle": "Primary Characteristics", "points": ["Lightweight & stateless", "Fast local verification", "Short-lived security barrier"]},
                {"title": item2, "subtitle": "Extended Lifecycle", "points": ["Monitored & stateful", "Used for session refresh", "Breach detection enabled"], "highlight": True}
            ]
        }
        
    # 3. Process flow detection (steps, phases, rotation, lifecycle)
    if any(k in lower for k in ["step", "phase", "process", "rotation", "lifecycle", "workflow", "how to"]):
        sentences = [s.strip() for s in re.split(r'[.!?]', narration) if len(s.strip()) > 10]
        steps = []
        for i, s in enumerate(sentences[:3]):
            steps.append({
                "title": f"Phase 0{i+1}",
                "desc": s[:90] + "..." if len(s) > 90 else s
            })
        if not steps:
            steps = [
                {"title": "1. Initialize Request", "desc": "Send parameters to server"},
                {"title": "2. Verify & Process", "desc": "Validate signature and execute rules"},
                {"title": "3. Output Result", "desc": "Return verified response payload"}
            ]
        return {
            "visual_type": "process_flow",
            "title": title,
            "subtitle": "Step-by-Step Execution Lifecycle",
            "accent_color": "#00d4aa",
            "steps": steps
        }
        
    # 4. Architecture / system diagram detection
    if any(k in lower for k in ["architecture", "flow", "request", "server", "gateway", "database", "client", "service"]):
        return {
            "visual_type": "diagram",
            "title": title,
            "subtitle": "Distributed System Architecture & Flow",
            "accent_color": "#00d4aa",
            "diagram_code": "graph LR\n  C[1. Client Application] -->|API Request| S[2. Auth / API Gateway]\n  S -->|Verify Logic| DB[(3. Protected Resources)]"
        }
        
    # 5. Default: Concept card with active bullet highlights
    sentences = [s.strip() for s in re.split(r'[.!?]', narration) if len(s.strip()) > 10]
    points = sentences[:4] if sentences else ["Core foundational principles.", "Production architecture and best practices.", "Implementation considerations."]
    return {
        "visual_type": "concept_card",
        "title": title,
        "subtitle": "Key Concepts & Strategic Takeaways",
        "accent_color": "#7c83ff",
        "key_points": points
    }


def build_clip_html(scene: dict, clip: dict, clip_id: str, scene_id: str) -> str:
    """Build HTML for a clip using dynamic semantic specs (Mermaid, code, process flow) or intelligent inference."""
    vspec_dict = scene.get("visual_spec")
    if not vspec_dict or not isinstance(vspec_dict, dict):
        vspec_dict = _infer_visual_spec_from_narration(scene, clip)

    try:
        renderer = DiagramRenderer(width=WIDTH, height=HEIGHT, fps=FPS)
        spec = VisualSceneSpec(
            scene_id=clip_id,
            visual_type=vspec_dict.get("visual_type", "concept_card"),
            title=vspec_dict.get("title") or scene.get("title", "Overview"),
            subtitle=vspec_dict.get("subtitle") or clip.get("title") or scene.get("title"),
            diagram_code=vspec_dict.get("diagram_code"),
            steps=vspec_dict.get("steps", []),
            comparison_items=vspec_dict.get("comparison_items", []),
            code_snippet=vspec_dict.get("code_snippet"),
            code_language=vspec_dict.get("code_language", "json"),
            highlight_lines=vspec_dict.get("highlight_lines", []),
            key_points=vspec_dict.get("key_points") or [clip.get("narration", "")[:100]],
            accent_color=vspec_dict.get("accent_color", "#7c83ff"),
            clip_index=clip.get("clip_index", 0),
            total_clips=clip.get("total_clips", 1),
            narration_text=clip.get("narration", ""),
        )
        return renderer.render_scene_html(spec)
    except Exception as e:
        log.warning("Dynamic diagram render error (%s), using fallback concept card", e)
        renderer = DiagramRenderer(width=WIDTH, height=HEIGHT, fps=FPS)
        spec = VisualSceneSpec(
            scene_id=clip_id,
            visual_type="concept_card",
            title=scene.get("title", "Key Concept"),
            subtitle="Overview & Execution Details",
            key_points=[clip.get("narration", "")[:120]],
            accent_color="#7c83ff",
            clip_index=clip.get("clip_index", 0),
            total_clips=clip.get("total_clips", 1),
            narration_text=clip.get("narration", ""),
        )
        return renderer.render_scene_html(spec)


def generate_all_clip_html(scenes, clips_dir, min_clips=None, max_clips=None):
    clips_dir.mkdir(parents=True, exist_ok=True)
    all_clips = []
    for scene in scenes:
        scene_clips = split_scene_into_clips(scene, min_clips=min_clips, max_clips=max_clips)
        scene_id = f"S{scene['index'] + 1}"
        for clip in scene_clips:
            clip_id = f"{scene_id}_C{clip['clip_index'] + 1:02d}"
            html_path = clips_dir / f"{clip_id}.html"
            html = build_clip_html(scene, clip, clip_id, scene_id)
            html_path.write_text(html, encoding="utf-8")
            clip = dict(clip)
            clip["html_path"] = str(html_path)
            clip["clip_id"] = clip_id
            clip["scene_title"] = scene.get("title", "")
            all_clips.append(clip)
        log.info("  Scene %d '%s': %d clips", scene['index'] + 1, scene.get("title", "")[:40], len(scene_clips))
    log.info("✓ Generated %d clip HTML files", len(all_clips))
    return all_clips


# ═══════════════════════════════════════════════════════════════════════════════
# Audio, render, merge — same as v1
# ═══════════════════════════════════════════════════════════════════════════════

def get_audio_duration(path: Path) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        return float(json.loads(r.stdout)["format"].get("duration", 0))
    except Exception:
        return 0.0


def make_silent_audio(output_path: Path, duration: float = 1.0) -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i",
             "anullsrc=r=44100:cl=mono", "-t", str(duration), str(output_path)],
            capture_output=True, timeout=15, check=True,
        )
        return True
    except Exception:
        return False


async def _generate_clip_audio(clip, semaphore, audio_dir):
    async with semaphore:
        text = clip.get("narration", "").strip()
        clip_id = clip["clip_id"]
        output_path = audio_dir / f"{clip_id}.mp3"
        tts_adapter = ChatTTSAdapter()
        aligner = WhisperAligner()

        if output_path.exists() and output_path.stat().st_size > 1000:
            dur = get_audio_duration(output_path)
            alignments = aligner.align_audio(output_path, script_text=text, duration=dur)
            tight_dur = round(max(2.0, dur + 0.6), 2)
            return {
                **clip,
                "duration_seconds": tight_dur,
                "audio_path": str(output_path),
                "audio_duration": dur,
                "alignments": [a.to_dict() for a in alignments],
                "cached": True
            }

        if not text:
            make_silent_audio(output_path, clip["duration_seconds"])
            return {
                **clip,
                "audio_path": str(output_path),
                "audio_duration": clip["duration_seconds"],
                "alignments": [],
                "cached": False
            }

        try:
            await tts_adapter.generate_speech(text, output_path)
            dur = get_audio_duration(output_path)
            alignments = aligner.align_audio(output_path, script_text=text, duration=dur)
            tight_dur = round(max(2.0, dur + 0.6), 2)
            return {
                **clip,
                "duration_seconds": tight_dur,
                "audio_path": str(output_path),
                "audio_duration": dur,
                "alignments": [a.to_dict() for a in alignments],
                "cached": False
            }
        except Exception as e:
            log.warning("  Clip %s: TTS generation error (%s), using fallback", clip_id, e)
            dur = max(1.0, len(text.split()) / WPM * 60)
            make_silent_audio(output_path, dur)
            tight_dur = round(max(2.0, dur + 0.6), 2)
            return {
                **clip,
                "duration_seconds": tight_dur,
                "audio_path": str(output_path),
                "audio_duration": dur,
                "alignments": [],
                "cached": False
            }


async def generate_all_clip_audio(clips, audio_dir):
    audio_dir.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(min(8, len(clips) or 1))
    log.info("Generating audio for %d clips...", len(clips))
    tasks = [_generate_clip_audio(c, semaphore, audio_dir) for c in clips]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    updated = [r for r in results if not isinstance(r, BaseException)]
    log.info("✓ Audio generated for %d clips", len(updated))
    return updated


_RENDER_HELPER: Path | None = None


def _build_encoder_args(encoder: str, bitrate: str = "12M") -> list[str]:
    """Returns FFmpeg video encoding arguments tailored to the specific encoder."""
    if encoder == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "20", "-b:v", bitrate]
    elif encoder == "h264_qsv":
        return ["-c:v", "h264_qsv", "-b:v", bitrate]
    elif encoder == "h264_mf":
        return ["-c:v", "h264_mf", "-b:v", bitrate]
    elif encoder == "h264_amf":
        return ["-c:v", "h264_amf", "-b:v", bitrate]
    elif encoder == "h264_videotoolbox":
        return ["-c:v", "h264_videotoolbox", "-b:v", bitrate]
    else:
        return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "20"]


def _is_clip_visual_valid(video_path: Path, check_time: float = 1.0) -> bool:
    """Verifies that a rendered clip contains valid visual content (not a pure white or pure black blank screen)."""
    try:
        chk_img = video_path.parent / f"_chk_{video_path.stem}.jpg"
        res = subprocess.run([
            "ffmpeg", "-y", "-ss", str(max(0.2, check_time)), "-i", str(video_path),
            "-vframes", "1", str(chk_img)
        ], capture_output=True, timeout=10)
        if res.returncode == 0 and chk_img.exists():
            from PIL import Image
            im = Image.open(chk_img)
            stat = im.resize((10, 10)).convert('L')
            avg = sum(stat.getdata()) / 100.0
            chk_img.unlink(missing_ok=True)
            # Pure white screen is ~255. Valid dark scenes are typically 10-60 luminance.
            if avg > 240.0:
                log.warning("Visual check failed for %s (Avg luminance = %.1f, looks blank/white)", video_path.name, avg)
                return False
            return True
    except Exception as e:
        log.debug("Visual validation check error: %s", e)
    return True


def _get_render_helper():
    global _RENDER_HELPER
    helper = Path(__file__).parent / "_render_clip.py"
    pw_args_json = json.dumps(PLAYWRIGHT_ARGS)
    code = f'''import sys, time, shutil, os, json
from pathlib import Path

html_path = Path(sys.argv[1])
duration = float(sys.argv[2])
width = int(sys.argv[3])
height = int(sys.argv[4])
record_dir = Path(sys.argv[5])

try:
    from playwright.sync_api import sync_playwright
    pw_args = {pw_args_json}
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(args=pw_args)
        except Exception:
            browser = p.chromium.launch(args=["--disable-web-security", "--no-sandbox", "--disable-dev-shm-usage", "--autoplay-policy=no-user-gesture-required"])
        context = browser.new_context(
            viewport={{"width": width, "height": height}},
            device_scale_factor=1,
            record_video_dir=str(record_dir),
            record_video_size={{"width": width, "height": height}},
            color_scheme="dark",
        )
        t_start = time.time()
        page = context.new_page()
        page.goto(f"file:///{{html_path.resolve().as_posix()}}", wait_until="load", timeout=15000)
        try:
            page.wait_for_selector(".screen-canvas", state="visible", timeout=10000)
        except Exception:
            pass
        page.wait_for_timeout(250)
        
        t_ready = time.time()
        ready_offset = max(0.0, t_ready - t_start)
        
        while time.time() - t_ready < duration:
            page.wait_for_timeout(50)
            
        video = page.video
        page.close()
        final_path = record_dir / "output.webm"
        video.save_as(str(final_path))
        context.close()
        browser.close()
        
        meta_file = record_dir / "meta.json"
        meta_file.write_text(json.dumps({{"ready_offset": ready_offset}}), encoding="utf-8")
        print(f"OK:{{ready_offset:.3f}}")
except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    print(f"ERROR: {{e}}", file=sys.stderr)
    sys.exit(1)
'''
    try:
        helper.write_text(code, encoding="utf-8")
    except Exception:
        pass
    _RENDER_HELPER = helper
    return helper


def _transcode_webm_to_mp4(webm_path: Path, output_path: Path, duration: float, ready_offset: float = 0.0) -> bool:
    """Transcodes recorded WebM to MP4 starting after ready_offset to eliminate initial white frames."""
    primary_enc_args = _build_encoder_args(VIDEO_ENCODER, VIDEO_BITRATE)
    ss_args = ["-ss", f"{ready_offset:.3f}"] if ready_offset > 0.05 else []

    # 1. Primary Hardware/Selected Encoder
    cmd = [
        "ffmpeg", "-y",
        *ss_args,
        "-i", str(webm_path),
        *primary_enc_args,
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-vf", f"fps={FPS},scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:-1:-1:color=#050514,format=yuv420p",
        "-an", "-t", str(duration), str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 1000:
        if _is_clip_visual_valid(output_path, check_time=min(1.0, duration / 2)):
            return True
        log.warning("Primary encoder %s produced blank/white clip on %s, trying CPU fallback", VIDEO_ENCODER, output_path.name)

    # 2. Resilient CPU Fallback (never fails!)
    log.warning("Falling back to libx264 CPU encoder for %s", output_path.name)
    fallback_cmd = [
        "ffmpeg", "-y",
        *ss_args,
        "-i", str(webm_path),
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-vf", f"fps={FPS},scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:-1:-1:color=#050514,format=yuv420p",
        "-an", "-t", str(duration), str(output_path),
    ]
    fb_result = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=90)
    if fb_result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 1000:
        return True

    return False


def _render_one_clip(html_path, output_path, duration, retries=2):
    record_dir = output_path.parent / f"_rec_{output_path.stem}"
    helper = _get_render_helper()
    
    for attempt in range(retries):
        record_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                [sys.executable, str(helper), str(html_path), str(duration),
                 str(WIDTH), str(HEIGHT), str(record_dir)],
                capture_output=True, text=True, timeout=int(duration + 90),
            )
            if result.returncode != 0:
                log.warning("  Playwright attempt %d failed for %s: %s", attempt + 1, output_path.name, result.stderr.strip()[-200:])
                continue
            
            ready_offset = 0.0
            meta_file = record_dir / "meta.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    ready_offset = float(meta.get("ready_offset", 0.0))
                except Exception:
                    pass
            
            webm_path = record_dir / "output.webm"
            if not webm_path.exists() or webm_path.stat().st_size < 1000:
                continue
            if _transcode_webm_to_mp4(webm_path, output_path, duration, ready_offset=ready_offset):
                return True
        finally:
            if record_dir.exists():
                shutil.rmtree(record_dir, ignore_errors=True)
        time.sleep(0.5)
    return False


def render_all_clips_parallel(clips, videos_dir, max_workers=None):
    if max_workers is None:
        max_workers = min(4, NUM_WORKERS)
    videos_dir.mkdir(parents=True, exist_ok=True)
    results = []
    total = len(clips)
    completed = 0
    log.info("Rendering %d clips with %d workers...", total, max_workers)
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for clip in clips:
            clip_id = clip["clip_id"]
            video_path = videos_dir / f"{clip_id}.mp4"
            future = executor.submit(_render_one_clip, Path(clip["html_path"]), video_path, clip["duration_seconds"])
            future_map[future] = (clip, video_path)
        for future in as_completed(future_map):
            clip, video_path = future_map[future]
            try:
                ok = future.result()
            except Exception as e:
                log.error("  Clip %s crashed: %s", clip["clip_id"], e)
                ok = False
            clip_result = dict(clip)
            clip_result["video_path"] = str(video_path)
            clip_result["video_ok"] = ok
            results.append(clip_result)
            completed += 1
            elapsed = time.time() - start_time
            rate = completed / elapsed if elapsed > 0 else 0
            eta = (total - completed) / rate if rate > 0 else 0
            log.info("  [%d/%d] %s — %.1fs, ETA=%.0fs", completed, total, clip["clip_id"], clip["duration_seconds"], eta)
    elapsed = time.time() - start_time
    ok_count = sum(1 for r in results if r.get("video_ok"))
    log.info("✓ Rendered %d/%d clips in %.1fs", ok_count, total, elapsed)
    return sorted(results, key=lambda r: r["clip_id"])


def concat_clips_with_audio(clips, videos_dir, audio_dir, output_path):
    log.info("Compositing final video from %d clips...", len(clips))
    work_dir = output_path.parent / "_merge_work"
    work_dir.mkdir(parents=True, exist_ok=True)
    scene_groups = {}
    for clip in clips:
        scene_idx = int(clip["clip_id"].split("_")[0].replace("S", "")) - 1
        scene_groups.setdefault(scene_idx, []).append(clip)
    scene_outputs = []
    for scene_idx in sorted(scene_groups.keys()):
        scene_clips = sorted(scene_groups[scene_idx], key=lambda c: c["clip_index"])
        scene_mp4s = []
        for clip in scene_clips:
            clip_id = clip["clip_id"]
            video_path = videos_dir / f"{clip_id}.mp4"
            audio_path = Path(clip.get("audio_path", ""))
            clip_duration = clip["duration_seconds"]
            if not video_path.exists() or not video_path.stat().st_size > 1000:
                continue
            clip_output = work_dir / f"sc_{scene_idx:02d}_{clip['clip_index']:02d}.mp4"
            enc_args = _build_encoder_args(VIDEO_ENCODER, VIDEO_BITRATE)
            if audio_path.exists() and audio_path.stat().st_size > 1000:
                cmd = [
                    "ffmpeg", "-y", "-i", str(video_path), "-i", str(audio_path),
                    "-map", "0:v:0", "-map", "1:a:0",
                    *enc_args,
                    "-c:a", "aac", "-b:a", "192k",
                    "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-af", "apad=pad_dur=999", "-t", str(clip_duration),
                    str(clip_output),
                ]
            else:
                cmd = [
                    "ffmpeg", "-y", "-i", str(video_path),
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-map", "0:v:0", "-map", "1:a:0",
                    *enc_args,
                    "-c:a", "aac", "-b:a", "192k",
                    "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-t", str(clip_duration), str(clip_output),
                ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                fb_args = _build_encoder_args("libx264")
                if audio_path.exists() and audio_path.stat().st_size > 1000:
                    fb_cmd = [
                        "ffmpeg", "-y", "-i", str(video_path), "-i", str(audio_path),
                        "-map", "0:v:0", "-map", "1:a:0",
                        *fb_args,
                        "-c:a", "aac", "-b:a", "192k",
                        "-pix_fmt", "yuv420p", "-r", str(FPS),
                        "-af", "apad=pad_dur=999", "-t", str(clip_duration),
                        str(clip_output),
                    ]
                else:
                    fb_cmd = [
                        "ffmpeg", "-y", "-i", str(video_path),
                        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                        "-map", "0:v:0", "-map", "1:a:0",
                        *fb_args,
                        "-c:a", "aac", "-b:a", "192k",
                        "-pix_fmt", "yuv420p", "-r", str(FPS),
                        "-t", str(clip_duration), str(clip_output),
                    ]
                result = subprocess.run(fb_cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                scene_mp4s.append(clip_output)
            else:
                scene_mp4s.append(video_path)
        scene_list = work_dir / f"scene_{scene_idx:02d}_list.txt"
        scene_list.write_text("".join(f"file '{Path(v).resolve().as_posix()}'\n" for v in scene_mp4s), encoding="utf-8")
        scene_output = work_dir / f"scene_{scene_idx:02d}.mp4"
        result = subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(scene_list),
            "-c", "copy", "-movflags", "+faststart", str(scene_output),
        ], capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            scene_outputs.append(scene_output)
            log.info("  Scene %d: %d clips merged", scene_idx + 1, len(scene_mp4s))
    if not scene_outputs:
        return False
    concat_file = output_path.parent / "concat.txt"
    concat_file.write_text("".join(f"file '{Path(v).resolve().as_posix()}'\n" for v in scene_outputs), encoding="utf-8")
    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", "-movflags", "+faststart", str(output_path),
    ], capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        return False
    size_mb = output_path.stat().st_size / (1024 * 1024)
    log.info("✓ Final video: %s (%.1f MB)", output_path, size_mb)
    return True


def generate_thumbnail(final_path, thumb_path, timestamp=5.0):
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(timestamp), "-i", str(final_path),
        "-vframes", "1", "-vf", f"scale={WIDTH}:{HEIGHT}", str(thumb_path),
    ], capture_output=True, text=True, timeout=30)
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# Main pipeline
# ═══════════════════════════════════════════════════════════════════════════════

async def run_pipeline(
    project_dir,
    topic,
    subtopic,
    explanation,
    skip_audio=False,
    max_workers=None,
    clips_per_scene=None,
    quality_tier: str | None = None,
    fps_override: int | None = None,
    resolution_override: str | None = None,
):
    pipeline_start = time.time()
    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)

    log.info("=" * 60)
    log.info("STEP 0: DYNAMIC HARDWARE BENCHMARK & SYSTEM CHECK")
    log.info("=" * 60)

    # 1. Probe host hardware and compute adaptive profile
    profile = SystemProfiler.get_profile(force_refresh=True)

    # Apply user overrides if requested
    if quality_tier in ("ultra", "medium", "low"):
        if quality_tier == "ultra":
            profile.tier = "ultra"
            profile.width, profile.height = 2560, 1440
            profile.fps = 60
            profile.video_bitrate = "14M"
        elif quality_tier == "medium":
            profile.tier = "medium"
            profile.width, profile.height = 1920, 1080
            profile.fps = 60 if profile.is_gpu_accelerated else 30
            profile.video_bitrate = "7M"
        elif quality_tier == "low":
            profile.tier = "low"
            profile.width, profile.height = 1280, 720
            profile.fps = 30
            profile.video_bitrate = "3M"

    if fps_override:
        profile.fps = fps_override
    if resolution_override:
        parts = resolution_override.lower().split("x")
        if len(parts) == 2:
            try:
                profile.width, profile.height = int(parts[0]), int(parts[1])
            except ValueError:
                pass
    if max_workers:
        profile.max_workers = max_workers

    # Ensure strictly 150 WPM
    profile.wpm = 150

    # Apply globally to renderers and FFmpeg
    apply_quality_profile(profile)

    # Print clean diagnostics banner
    SystemProfiler.print_system_banner(profile)

    # Save system_profile.json
    profile_path = SystemProfiler.save_profile_to_project(project_dir, profile)
    log.info("  ✓ System profile written to: %s", profile_path)

    log.info("")
    log.info("=" * 60)
    log.info("STEP 1: Loading / Generating Script (Pacing: %d WPM)", WPM)
    log.info("=" * 60)
    script_text = load_or_create_script(project_dir, topic, subtopic, explanation, profile)

    log.info("")
    log.info("=" * 60)
    log.info("STEP 2: Parsing Scenes & Validating 1-to-1 Clip Timing")
    log.info("=" * 60)
    scenes = parse_scenes(script_text)
    log.info("✓ Parsed %d scenes", len(scenes))
    for s in scenes:
        log.info("  Scene %d: '%s' (%.1fs)", s["index"] + 1, s["title"][:50], s["duration_seconds"])

    log.info("")
    log.info("=" * 60)
    log.info("STEP 3: Generating Clip HTML at Native %dx%d", WIDTH, HEIGHT)
    log.info("=" * 60)
    clips_dir = project_dir / "clips" / "html"
    all_clips = generate_all_clip_html(scenes, clips_dir, min_clips=clips_per_scene, max_clips=clips_per_scene)
    log.info("✓ %d total clips generated", len(all_clips))

    log.info("")
    log.info("=" * 60)
    log.info("STEP 4: Generating Narration Audio & Locking Exact Timing")
    log.info("=" * 60)
    audio_dir = project_dir / "audio" / "narration"
    if skip_audio:
        for clip in all_clips:
            clip["audio_path"] = ""
            clip["audio_duration"] = 0
    else:
        all_clips = await generate_all_clip_audio(all_clips, audio_dir)

    log.info("")
    log.info("=" * 60)
    log.info("STEP 5: Parallel GPU Rendering (%d workers, %s @ %d fps)", NUM_WORKERS, VIDEO_ENCODER, FPS)
    log.info("=" * 60)
    videos_dir = project_dir / "clips" / "videos"
    rendered = render_all_clips_parallel(all_clips, videos_dir, max_workers=NUM_WORKERS)
    ok_clips = [c for c in rendered if c.get("video_ok")]
    if not ok_clips:
        log.error("No clips rendered successfully")
        return project_dir

    log.info("")
    log.info("=" * 60)
    log.info("STEP 6: Hardware-Accelerated Video Composition")
    log.info("=" * 60)
    renders_dir = project_dir / "renders"
    renders_dir.mkdir(parents=True, exist_ok=True)
    final_path = renders_dir / "final.mp4"
    if not concat_clips_with_audio(ok_clips, videos_dir, audio_dir, final_path):
        log.error("Composition failed")
        return project_dir

    log.info("")
    log.info("=" * 60)
    log.info("STEP 7: Post-Processing & Output Finalization")
    log.info("=" * 60)
    output_path = renders_dir / "video.mp4"
    import shutil
    shutil.copy2(final_path, output_path)
    generate_thumbnail(output_path, renders_dir / "thumbnail.jpg")

    total_dur = sum(c["duration_seconds"] for c in ok_clips)
    elapsed = time.time() - pipeline_start
    log.info("")
    log.info("=" * 60)
    log.info("🎬 VIDEO GENERATION COMPLETE!")
    log.info("=" * 60)
    log.info("  Output:      %s", output_path)
    log.info("  Resolution:  %dx%d (%s)", WIDTH, HEIGHT, profile.tier.upper())
    log.info("  Frame Rate:  %d FPS", FPS)
    log.info("  Encoder:     %s (%s)", VIDEO_ENCODER, "GPU Accelerated" if profile.is_gpu_accelerated else "CPU")
    log.info("  Clips:       %d/%d rendered", len(ok_clips), len(rendered))
    log.info("  Scenes:      %d", len(scenes))
    log.info("  Duration:    %.1f min (%.1fs)", total_dur / 60, total_dur)
    log.info("  Pipeline:    %.1fs", elapsed)
    log.info("=" * 60)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="VideoForge Clip Engine v2 with Adaptive Hardware Profiling")
    parser.add_argument("--project-dir", type=str, default=None)
    parser.add_argument("--topic", type=str, default="")
    parser.add_argument("--subtopic", type=str, default="")
    parser.add_argument("--explanation", type=str, default="")
    parser.add_argument("--skip-audio", action="store_true")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--clips-per-scene", type=int, default=None)
    parser.add_argument("--quality", type=str, choices=["auto", "ultra", "medium", "low"], default="auto",
                        help="Adaptive quality tier: auto (hardware-detected), ultra (2K 60fps), medium (1080p), low (720p)")
    parser.add_argument("--fps", type=int, default=None, help="Override frame rate (e.g. 60 or 30)")
    parser.add_argument("--res", type=str, default=None, help="Override resolution (e.g. 2560x1440, 1920x1080, 1280x720)")
    args = parser.parse_args()

    topic = args.topic or "Data Algorithm"
    subtopic = args.subtopic or "Architectural Patterns & Complexity"
    explanation = args.explanation or (
        "Comprehensive educational guide on data algorithm design, processing pipelines, "
        "code implementation, lifecycle stages, and complexity tradeoffs."
    )
    project_dir = Path(args.project_dir) if args.project_dir else PROJECTS_DIR / "data-algorithms"
    
    tier_override = None if args.quality == "auto" else args.quality

    asyncio.run(run_pipeline(
        project_dir=project_dir,
        topic=topic,
        subtopic=subtopic,
        explanation=explanation,
        skip_audio=args.skip_audio,
        max_workers=args.workers,
        clips_per_scene=args.clips_per_scene,
        quality_tier=tier_override,
        fps_override=args.fps,
        resolution_override=args.res,
    ))


if __name__ == "__main__":
    main()
