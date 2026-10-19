"""VideoForge — Standalone Educational Video Generator

Usage:
    python generate_video.py [--project-dir ./projects/cs-module1] [--topic "Topic"] [--subtopic "Sub"]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# ── paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = SCRIPT_DIR / "videoforge-backend"
ELEVENLABS_DIR = SCRIPT_DIR / "ElevenLabs"
STY_TTS2_DIR = ELEVENLABS_DIR / "StyleTTS2"
PROJECTS_DIR = SCRIPT_DIR / "projects"
sys.path.insert(0, str(BACKEND_DIR))

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("videoforge")

# ── config ────────────────────────────────────────────────────────────────────
from dotenv import load_dotenv  # noqa: E402
load_dotenv(SCRIPT_DIR / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge")  # edge | elevenlabs | none
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-GuyNeural")
WIDTH = int(os.getenv("DEFAULT_WIDTH", "1920"))
HEIGHT = int(os.getenv("DEFAULT_HEIGHT", "1080"))
FPS = int(os.getenv("DEFAULT_FPS", "30"))
WPM = int(os.getenv("DEFAULT_WORDS_PER_MINUTE", "150"))
SUBSLIDE_DURATION_SEC = float(os.getenv("SUBSLIDE_DURATION_SEC", "20"))  # target length per sub-slide
WORDS_PER_SUBSLIDE = int(WPM * SUBSLIDE_DURATION_SEC / 60)  # ~50 words at 150 wpm for 20s


# ═══════════════════════════════════════════════════════════════════════════════
# 1.  LOAD / CREATE SCRIPT
# ═══════════════════════════════════════════════════════════════════════════════

CS_MODULE1_SCRIPT = r"""Computer Science Fundamentals — Module 1: The Computational Mindset & Binary

[SCENE 1: Introduction to Computer Science — 0:00 - 8:00]

VISUAL: Fast-paced montage — smartphone unlock, drone flying, CGI cityscape, scientist typing code. Transition to virtual classroom host. Venn diagram: Computer Science encompasses Programming, Algorithms, Hardware, and Problem Solving. Highlight "Problem Solving" with a glowing ring.

NARRATION:
"Welcome to Computer Science Fundamentals. I'm your professor, and today we begin a journey into how computers think, work, and solve problems. Many people think computer science is just typing green text on a black screen like in the movies. But in reality, computer science is the study of problem-solving. Programming is just the tool we use to give the computer our solution. Today, we are going to peel back the layers of the screen and understand the fundamental rules of the digital universe. By the end of this video, you will understand how a machine built from nothing but metal and electricity can create the apps, games, and websites you use every day."

[SCENE 2: How Computers Think — The Light Switch Analogy — 8:00 - 18:00]

VISUAL: Close-up of wall light switch. Animation: switch flips UP → lightbulb ON → glowing number "1" appears. Switch flips DOWN → lightbulb OFF → glowing number "0". Split screen: left side shows human hand writing "9", right side shows microchip. Morphing graphic: 10-finger hand → 2-state chip. Binary counting table: 0, 1, 10, 11, 100 — highlight left-shift pattern.

NARRATION:
"To understand computers, we have to talk about electricity. Inside a computer chip, there are billions of tiny microscopic pathways. Electricity is flowing through them constantly. But a computer can't understand English, Spanish, or Python. It can only understand one thing: is the electricity on, or is it off? Think of a light switch. When the switch is up, electricity flows, the bulb is on. We call this state '1'. When the switch is down, the bulb is off. We call this state '0'. That's it. A computer is essentially a massive collection of billions of microscopic light switches.

But how do we count to 10 using only 0s and 1s? Humans use Base 10, because we have 10 fingers. We count 1, 2, 3, all the way to 9, and then we add a new digit to make '10'. Computers use Base 2, also known as Binary. They count 0, 1... and then they run out of digits! So what do they do? They add a new digit to the left. So '2' in binary is '10'. '3' is '11'. '4' is '100'. It looks strange to us, but to a computer, it's the only logical way to exist."

[SCENE 3: Representing Letters and Colors — 18:00 - 28:00]

VISUAL: Computer keyboard. Letter 'A' key pressed in slow motion. 'A' transforms to 65, then to binary "01000001". Binary floats to monitor, transforms back to 'A'. Label: "ASCII". Color wheel with RGB spotlights. Pixel magnification showing 3 tiny lights (R, G, B) with numbers: R: 255, G: 100, B: 0. Binary equivalents flash rapidly.

NARRATION:
"So, we can represent numbers with 1s and 0s. But what about text? How do you send a text message to a friend if the phone only knows 1s and 0s? Decades ago, computer scientists created a secret code called ASCII. In ASCII, every letter of the alphabet is assigned a specific number. The letter 'A' is the number 65. The letter 'B' is 66. And since we know how to convert numbers to binary, the letter 'A' becomes '01000001'. When you type 'A' on your keyboard, it sends that binary code to the computer's brain, which translates it back to 'A' on your screen.

But what about images and videos? An image on a screen is made up of millions of tiny dots called pixels. Every pixel is actually a combination of three tiny lights: Red, Green, and Blue — known as RGB. The computer assigns a number to each color. If Red is fully on, it's 255. If it's off, it's 0. So, the color orange might be Red: 255, Green: 100, Blue: 0. The computer translates those three numbers into binary, stores them, and lights up the pixel on your screen. Every photo, every YouTube video, every video game is ultimately just billions of 1s and 0s flashing on and off."

[SCENE 4: Algorithmic Thinking & Pseudocode — 28:00 - 38:00]

VISUAL: Person confused at computer. Chef in kitchen holds recipe card. Recipe text morphs into logical steps. "Pseudocode" concept appears — plain English sentences transform into structured logic. Flowchart: diamond "Is password correct?" → Yes → "Log in", No → "Try again".

NARRATION:
"Now that we know how computers store data, how do we get them to actually do work? We use Algorithms. An algorithm is just a step-by-step set of instructions to solve a problem. It's exactly like a recipe. If you want to bake a cake, you follow specific steps in a specific order. If you mix them up, you get a mess.

Before we write actual code, we write 'Pseudocode'. Pseudocode is plain English that outlines the logic of our program. Let's say we want to write a program to log a user into a website. The pseudocode would be: 'Ask user for password. If the password is correct, let them in. If the password is wrong, show an error message.'

Notice we used the word 'If'. This is a fundamental concept in computer science called a 'Condition'. Computers make decisions by evaluating conditions: If this happens, do that. Otherwise, do something else."

[SCENE 5: Inputs, Outputs, Loops, and Functions — 38:00 - 48:00]

VISUAL: Factory graphic. Truck drops boxes (Inputs) on left. Boxes enter machine (Function). Machine outputs finished product (Outputs) on right. "Function" label with button-press animation. Hamster on wheel → "Loop". Circular flowchart: Start → Do Task → Check condition → If true, go back. Counter: 1, 2, 3, 4, 5. Scratch block-coding: purple blocks snap together to form loop and condition.

NARRATION:
"Let's define the core building blocks of every algorithm. First, we have Inputs and Outputs. A program takes information in, processes it, and gives information back.

Next, we have Functions. A function is a reusable block of code. Think of it like a mini-factory inside your program. You give it an input, it does some work, and it gives you an output. You can use it over and over again without rewriting the code.

Finally, we have Loops. Computers are incredibly fast and incredibly dumb. If you want a computer to do something 100 times, you shouldn't have to write the instruction 100 times. You use a loop. A loop tells the computer, 'Do this task, and keep doing it until I tell you to stop, or until a condition is met.'

Together, Inputs, Outputs, Functions, Conditions, and Loops are the DNA of every piece of software ever created. From the operating system on your phone to the algorithms that land rockets on drone ships, it all boils down to these simple concepts."

[SCENE 6: Conclusion & Assignment — 48:00 - 50:00]

VISUAL: Host returns to center. Montage: light switch (1s and 0s), 'A' → binary, flowchart, loop symbol. On-screen text: "Assignment: Write Pseudocode for making a peanut butter and jelly sandwich." Fade to course logo. "Next Module: The C Programming Language."

NARRATION:
"Today, we've taken our first step into the computational mindset. You've learned that computers only speak in binary — 1s and 0s representing on and off. You've learned how we use codes like ASCII and RGB to translate those 1s and 0s into text and images. And you've learned the basic building blocks of algorithms: inputs, outputs, functions, conditions, and loops.

Before we move on to Module 2, where we will start writing our first real code in the C programming language, I have a challenge for you. Your assignment is to write pseudocode for making a peanut butter and jelly sandwich. Remember, computers are dumb. If you don't explicitly tell the computer to open the jar of peanut butter, it will try to spread the bread right over the closed jar. Think logically, step by step."""


def load_or_create_script(project_dir: Path, topic: str, _subtopic: str, _explanation: str) -> str:
    """Load existing script or use the built-in CS Module 1 content."""
    script_file = project_dir / "script.txt"
    if script_file.exists():
        log.info("Loading existing script from %s", script_file)
        return script_file.read_text(encoding="utf-8")

    # Use the built-in script if no custom content provided
    if topic and ("computer science" in topic.lower() or "cs" in topic.lower()):
        log.info("Using built-in CS Module 1 script")
        script_file.write_text(CS_MODULE1_SCRIPT, encoding="utf-8")
        return CS_MODULE1_SCRIPT

    # For custom topics, we'll need Claude to generate the script
    raise ValueError(
        f"No script found for topic '{topic}'. "
        "For custom topics, Claude API generation is required (not yet implemented for offline use)."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 2.  PARSE SCRIPT INTO SCENES
# ═══════════════════════════════════════════════════════════════════════════════

def parse_scenes(script_text: str) -> list[dict[str, Any]]:
    """Parse the formatted script into structured scenes."""
    scenes = []
    # Split by scene headers like [SCENE N: ... — DURATION]
    blocks = re.split(r'\[SCENE\s+\d+:', script_text)
    for block in blocks[1:]:  # skip preamble
        lines = block.strip().split('\n', 1)
        header = lines[0]
        body = lines[1] if len(lines) > 1 else ""

        # Extract scene title and timing
        title_match = re.match(r'(.+?)[—–-]\s*(\d+:\d+)\s*-\s*(\d+:\d+)', header)
        if not title_match:
            continue

        title = title_match.group(1).strip()
        start_str = title_match.group(2)
        end_str = title_match.group(3)

        def to_seconds(t: str) -> int:
            parts = t.split(':')
            return int(parts[0]) * 60 + int(parts[1])

        duration = to_seconds(end_str) - to_seconds(start_str)

        # Extract VISUAL and NARRATION sections
        visual_match = re.search(r'VISUAL:\s*(.*?)(?=NARRATION:|$)', body, re.DOTALL | re.IGNORECASE)
        narration_match = re.search(r'NARRATION:\s*(.*?)$', body, re.DOTALL | re.IGNORECASE)

        visual = visual_match.group(1).strip() if visual_match else ""
        narration = narration_match.group(1).strip() if narration_match else body.strip()

        scenes.append({
            "title": title,
            "start": start_str,
            "end": end_str,
            "duration_seconds": duration,
            "visual": visual,
            "narration": narration,
        })

    log.info("Parsed %d scenes", len(scenes))
    for s in scenes:
        log.info("  [%s-%s] %s (%ds)", s['start'], s['end'], s['title'], s['duration_seconds'])

    return scenes


def split_narration_for_subslides(scene: dict) -> list[dict]:
    """Split one scene's narration into ~20s chunks with sub-visual prompts.

    Strategy:
    - Split narration text at sentence boundaries (. ? !)
    - Greedily accumulate sentences until ~WORDS_PER_SUBSLIDE words reached
    - Each chunk becomes one sub-slide with target_seconds = words / WPM * 60
    - Visual hints are derived from the scene's overall visual description
      and tagged with the chunk's content keywords (binary, ascii, loop, etc.)

    Returns list of {text_chunk, visual_hint, target_seconds, variant}.
    """
    text = scene.get("narration", "").strip()
    base_visual = scene.get("visual", "")
    dur_val = scene.get("duration_seconds") or scene.get("estimated_duration") or 0
    _dur = float(dur_val) if dur_val is not None else 0.0
    # _dur kept for reference; actual chunk durations come from word count

    # Split into sentences (keep punctuation)
    raw_sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in raw_sentences if s.strip()]

    chunks: list[dict] = []
    cur_words: list[str] = []
    cur_text: list[str] = []
    cur_word_count = 0
    variant_idx = 0

    def flush_chunk():
        nonlocal cur_words, cur_text, cur_word_count, variant_idx
        if not cur_text:
            return
        chunk_text = " ".join(cur_text).strip()
        word_count = cur_word_count
        target_sec = max(5.0, word_count / WPM * 60)  # min 5s per slide
        # Cycle through 4 visual variants: concept → detail → analogy → summary
        variants = ["concept", "detail", "analogy", "summary"]
        variant = variants[variant_idx % len(variants)]
        # Visual hint: base visual + content keywords
        keyword_hints = []
        lower = chunk_text.lower()
        if any(k in lower for k in ["binary", "0", "1", "switch"]):
            keyword_hints.append("binary visualization")
        if any(k in lower for k in ["ascii", "letter", "65"]):
            keyword_hints.append("ASCII encoding")
        if any(k in lower for k in ["pixel", "rgb", "color", "255"]):
            keyword_hints.append("RGB color encoding")
        if any(k in lower for k in ["algorithm", "recipe", "pseudocode", "if"]):
            keyword_hints.append("algorithm flowchart")
        if any(k in lower for k in ["function", "loop", "input", "output"]):
            keyword_hints.append("function pipeline")
        hint = base_visual
        if keyword_hints:
            hint = base_visual + " | Focus: " + ", ".join(keyword_hints)
        chunks.append({
            "text_chunk": chunk_text,
            "visual_hint": hint,
            "target_seconds": target_sec,
            "variant": variant,
            "word_count": word_count,
        })
        variant_idx += 1
        cur_words = []
        cur_text = []
        cur_word_count = 0

    for sent in sentences:
        sent_words = sent.split()
        sent_count = len(sent_words)
        # If adding this sentence would overshoot significantly, flush first
        if cur_word_count + sent_count > WORDS_PER_SUBSLIDE * 1.4 and cur_text:
            flush_chunk()
        # If a single sentence is longer than the target, still add it whole
        cur_text.append(sent)
        cur_word_count += sent_count
        cur_words.extend(sent_words)
        # Flush when we hit target
        if cur_word_count >= WORDS_PER_SUBSLIDE:
            flush_chunk()

    # Flush any remaining sentences
    flush_chunk()

    return chunks





# ═══════════════════════════════════════════════════════════════════════════════
# 3.  GENERATE HTML SLIDES (Presenton-style)
# ═══════════════════════════════════════════════════════════════════════════════

THEME = {
    "bg": "#0a0a1a",
    "bg_grad": "radial-gradient(ellipse at 50% 0%, #1a1a3e 0%, #0a0a1a 70%)",
    "primary": "#7c83ff",
    "secondary": "#00d4aa",
    "accent": "#ff6b9d",
    "text": "#e4e4f0",
    "text_dim": "#8888aa",
    "code_bg": "#12122a",
    "card_bg": "rgba(20, 20, 50, 0.8)",
    "font": "'Segoe UI', system-ui, -apple-system, sans-serif",
    "mono": "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
}

CSS_TEMPLATE = """\
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap');

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: 'Inter', {font};
    background: {bg};
    background-image: {bg_grad};
    color: {text};
    width: {w}px; height: {h}px;
    overflow: hidden;
    position: relative;
}}

.particles {{ position: absolute; inset: 0; pointer-events: none; overflow: hidden; }}
.particle {{ position: absolute; border-radius: 50%; opacity: 0.3; animation: floatUp linear infinite; }}
@keyframes floatUp {{
    0% {{ transform: translateY(100vh) scale(0); opacity: 0; }}
    10% {{ opacity: 0.4; }} 90% {{ opacity: 0.1; }}
    100% {{ transform: translateY(-10vh) scale(1.2); opacity: 0; }}
}}

h1 {{
    font-size: 72px; font-weight: 900; line-height: 1.1;
    background: linear-gradient(135deg, {primary}, {secondary});
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}}
h2 {{
    font-size: 56px; font-weight: 800; text-align: center;
    background: linear-gradient(135deg, {text}, {primary});
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    margin-bottom: 30px;
}}
h3 {{ font-size: 32px; font-weight: 700; }}
.subtitle {{
    font-size: 32px; color: {secondary}; font-weight: 300;
    text-align: center; margin-top: 16px; letter-spacing: 2px;
}}
.badge {{
    display: inline-block; background: linear-gradient(135deg, {primary}, {accent});
    color: white; padding: 8px 24px; border-radius: 50px;
    font-size: 18px; font-weight: 600; letter-spacing: 1px;
}}

.card {{
    background: {card_bg}; border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px; padding: 36px; backdrop-filter: blur(20px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05);
    animation: slideUp 0.8s ease-out both;
}}
@keyframes slideUp {{ from {{ opacity: 0; transform: translateY(40px); }} to {{ opacity: 1; transform: translateY(0); }} }}

.card-glow {{
    border: 2px solid {primary};
    box-shadow: 0 0 40px {primary}33, 0 8px 32px rgba(0,0,0,0.3);
}}

.code-block {{
    background: {code_bg}; border: 1px solid {primary}; border-radius: 12px;
    padding: 28px 36px; font-family: {mono}; font-size: 26px;
    color: #a6e3a1; line-height: 1.8; text-align: left;
    box-shadow: 0 0 30px {primary}15; position: relative; overflow: hidden;
}}
.code-block::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, {primary}, {secondary}, {accent});
}}

.highlight {{ color: {accent}; font-weight: 800; text-shadow: 0 0 20px {accent}50; }}
.glow {{ text-shadow: 0 0 30px {primary}80, 0 0 60px {primary}30; }}
.binary-bit {{
    display: inline-block; padding: 12px 20px; margin: 4px;
    background: linear-gradient(135deg, {primary}44, {secondary}44);
    border-radius: 10px; border: 1px solid {primary};
    animation: bitPulse 2s ease-in-out infinite;
}}
@keyframes bitPulse {{ 0%, 100% {{ transform: scale(1); }} 50% {{ transform: scale(1.08); }} }}
.binary-display {{
    font-family: {mono}; font-size: 48px; letter-spacing: 8px;
    color: #fab1a0; text-align: center; padding: 30px;
    background: {code_bg}; border-radius: 16px; border: 1px solid rgba(250,177,160,0.2);
}}

.grid {{ display: grid; gap: 32px; }}
.grid-2 {{ grid-template-columns: 1fr 1fr; }}
.grid-3 {{ grid-template-columns: repeat(3, 1fr); }}
.grid-4 {{ grid-template-columns: repeat(4, 1fr); }}
.center {{ text-align: center; }}
.split {{ display: flex; gap: 60px; align-items: center; }}
.split > div {{ flex: 1; }}
.factory-visual {{ display: flex; align-items: center; justify-content: center; gap: 30px; padding: 40px; }}
.factory-box {{
    width: 140px; height: 140px; border-radius: 20px;
    display: flex; align-items: center; justify-content: center;
    font-size: 64px; box-shadow: 0 8px 30px rgba(0,0,0,0.3);
}}
.factory-machine {{
    background: linear-gradient(135deg, {primary}, {secondary});
    width: 200px; height: 180px; border-radius: 24px;
    display: flex; align-items: center; justify-content: center;
    font-size: 72px; position: relative;
    box-shadow: 0 0 60px {primary}40;
    animation: machinePulse 2s ease-in-out infinite;
}}
@keyframes machinePulse {{
    0%, 100% {{ box-shadow: 0 0 60px {primary}40; }}
    50% {{ box-shadow: 0 0 100px {secondary}50; }}
}}

.flow-box {{
    padding: 24px 40px; border-radius: 14px;
    font-size: 28px; font-weight: 700; text-align: center; min-width: 280px;
}}
.flow-process {{
    background: linear-gradient(135deg, {primary}33, {primary}11);
    border: 2px solid {primary}; color: {primary};
}}
.flow-decision {{
    background: linear-gradient(135deg, {accent}33, {accent}11);
    border: 2px solid {accent}; color: {accent};
}}
.flow-arrow {{ font-size: 48px; color: {secondary}; text-align: center; }}
.flow-line {{ width: 4px; height: 60px; background: {secondary}; margin: 0 auto; border-radius: 2px; }}

.assignment-box {{
    background: linear-gradient(135deg, {primary}22, {accent}22);
    border: 3px dashed {accent}; border-radius: 24px;
    padding: 50px; text-align: center;
    animation: assignmentGlow 2s ease-in-out infinite alternate;
}}
@keyframes assignmentGlow {{
    from {{ box-shadow: 0 0 30px {accent}20; }}
    to {{ box-shadow: 0 0 60px {accent}40; }}
}}

.ascii-chain {{ display: flex; align-items: center; justify-content: center; gap: 20px; font-size: 48px; font-family: {mono}; }}
.ascii-arrow {{
    font-size: 48px; color: {accent};
    animation: arrowSlide 1.5s ease-in-out infinite;
}}
@keyframes arrowSlide {{ 0%, 100% {{ transform: translateX(0); opacity: 0.5; }} 50% {{ transform: translateX(10px); opacity: 1; }} }}

.emoji-row {{ display: flex; gap: 30px; justify-content: center; font-size: 72px; }}

.fade-in {{ animation: fadeIn 1s ease-out both; }}
.fade-in-d1 {{ animation: fadeIn 1s ease-out 0.2s both; }}
.fade-in-d2 {{ animation: fadeIn 1s ease-out 0.4s both; }}
.fade-in-d3 {{ animation: fadeIn 1s ease-out 0.6s both; }}
.fade-in-d4 {{ animation: fadeIn 1s ease-out 0.8s both; }}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(30px); }} to {{ opacity: 1; transform: translateY(0); }} }}

.mt-20 {{ margin-top: 20px; }} .mt-40 {{ margin-top: 40px; }} .mt-60 {{ margin-top: 60px; }}

/* ── Sub-Slide Carousel Engine ─────────────────────────── */
.sub-slide-wrap {{ position: relative; width: 100%; height: 100%; overflow: hidden; }}
.sub-slide {{
    position: absolute; inset: 0;
    opacity: 0; z-index: 0;
    transition: opacity 0.9s cubic-bezier(0.4, 0, 0.2, 1),
                transform 0.9s cubic-bezier(0.4, 0, 0.2, 1);
    transform: translateX(60px) scale(0.97);
    display: flex; align-items: center; justify-content: center;
    padding: 60px 80px;
    pointer-events: none; visibility: hidden;
}}
.sub-slide.active {{
    opacity: 1; z-index: 2;
    transform: translateX(0) scale(1);
    pointer-events: auto; visibility: visible;
}}
.sub-slide.exit-left {{
    opacity: 0; z-index: 1;
    transform: translateX(-80px) scale(0.95);
}}
.sub-slide.exit-right {{
    opacity: 0; z-index: 1;
    transform: translateX(80px) scale(0.95);
}}
/* Staggered child animations within each active sub-slide */
.sub-slide.active .stagger-1 {{ animation: fadeIn 0.6s ease-out 0.1s both; }}
.sub-slide.active .stagger-2 {{ animation: fadeIn 0.6s ease-out 0.25s both; }}
.sub-slide.active .stagger-3 {{ animation: fadeIn 0.6s ease-out 0.4s both; }}
.sub-slide.active .stagger-4 {{ animation: fadeIn 0.6s ease-out 0.55s both; }}

/* Sub-slide header */
.sub-slide-header {{
    position: absolute; top: 28px; left: 50%; transform: translateX(-50%);
    font-size: 16px; color: #8888aa; letter-spacing: 3px; text-transform: uppercase;
    z-index: 5; font-weight: 300;
}}
.sub-slide-counter {{
    position: absolute; top: 28px; right: 40px;
    font-size: 15px; color: #555577; z-index: 5;
    font-variant-numeric: tabular-nums;
}}

/* Transition overlay for crossfade */
.transition-overlay {{
    position: absolute; inset: 0; z-index: 3;
    background: #0a0a1a; opacity: 0;
    pointer-events: none;
    transition: opacity 0.45s ease-in-out;
}}
.transition-overlay.flash {{ opacity: 0.6; }}
"""


def create_slide_html(scene: dict, index: int) -> str:
    """Generate a multi-sub-slide HTML file with JS carousel + transitions."""
    t = THEME
    title = scene["title"]
    visual = scene["visual"]
    idx = index + 1

    # Get sub-slides (chunks) for this scene
    subslides = scene.get("subslides", [])
    if not subslides:
        # Fallback: single sub-slide for the whole scene
        dur_val = scene.get("duration_seconds") or scene.get("estimated_duration") or 0
        dur_sec = float(dur_val) if dur_val is not None else 0.0
        subslides = [{
            "text_chunk": scene.get("narration", ""),
            "visual_hint": visual,
            "target_seconds": dur_sec,
            "variant": "concept",
        }]

    num_slides = len(subslides)

    # Build sub-slide sections
    sections_html = ""
    for si, sub in enumerate(subslides):
        body = _build_slide_body(
            sub.get("visual_hint", visual),
            t, title,
        )
        chunk_text = sub.get("text_chunk", "")
        # Escape for HTML data attribute
        chunk_escaped = chunk_text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") if chunk_text else ""
        sections_html += f'\n<section class="sub-slide" data-index="{si}" data-duration="{sub.get("target_seconds", SUBSLIDE_DURATION_SEC):.1f}" data-chunk="{chunk_escaped}">\n{body}\n</section>'

    css = CSS_TEMPLATE.format(
        font=t["font"], mono=t["mono"],
        bg=t["bg"], bg_grad=t["bg_grad"],
        primary=t["primary"], secondary=t["secondary"],
        accent=t["accent"], text=t["text"], text_dim=t["text_dim"],
        code_bg=t["code_bg"], card_bg=t["card_bg"],
        w=WIDTH, h=HEIGHT,
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width={WIDTH}">
<title>Scene {idx}: {title}</title>
<style>{css}</style>
</head>
<body>
<div class="sub-slide-wrap">
    <div class="sub-slide-header">Module 1 — Computer Science Fundamentals</div>
    <div class="sub-slide-counter"><span id="slideNum">1</span> / {num_slides}</div>
    <div class="transition-overlay" id="transOverlay"></div>
    {sections_html}
</div>
<div id="subCaption" style="position:absolute;bottom:24px;left:50%;transform:translateX(-50%);max-width:1200px;padding:10px 22px;background:rgba(10,10,26,0.8);border:1px solid rgba(124,131,255,0.25);border-radius:10px;font-size:16px;line-height:1.4;color:#e4e4f0;z-index:4;text-align:center;opacity:0;transition:opacity 0.5s ease;pointer-events:none;backdrop-filter:blur(6px)"></div>
<script>
(function() {{
    const slides = document.querySelectorAll('.sub-slide');
    const total = slides.length;
    const slideNumEl = document.getElementById('slideNum');
    const overlay = document.getElementById('transOverlay');
    const captionEl = document.getElementById('subCaption');
    let current = 0;
    let startTime = Date.now();

    function updateCaption(el) {{
        if (!captionEl) return;
        const txt = el.getAttribute('data-chunk') || '';
        if (txt) {{
            captionEl.textContent = txt.length > 200 ? txt.slice(0, 197) + '...' : txt;
            captionEl.style.opacity = '1';
        }} else {{
            captionEl.style.opacity = '0';
        }}
    }}

    function showSlide(index) {{
        if (index === current) return;
        const oldSlide = slides[current];
        const newSlide = slides[index];
        const direction = index > current ? 1 : -1;

        // Flash overlay for smooth crossfade
        overlay.classList.add('flash');
        setTimeout(() => overlay.classList.remove('flash'), 450);

        // Exit old slide
        oldSlide.classList.remove('active');
        oldSlide.classList.add(direction > 0 ? 'exit-left' : 'exit-right');

        // Enter new slide
        newSlide.classList.remove('exit-left', 'exit-right');
        void newSlide.offsetWidth;
        newSlide.classList.add('active');
        updateCaption(newSlide);

        // Update counter
        if (slideNumEl) slideNumEl.textContent = index + 1;

        // Reset staggered animations on new slide
        const staggers = newSlide.querySelectorAll('.stagger-1,.stagger-2,.stagger-3,.stagger-4');
        staggers.forEach(el => {{
            el.style.animation = 'none';
            void el.offsetWidth;
            el.style.animation = '';
        }});

        current = index;
        startTime = Date.now();
    }}

    function nextSlide() {{
        const next = (current + 1) % total;
        showSlide(next);
    }}

    // Initialize first slide
    slides[0].classList.add('active');
    updateCaption(slides[0]);

    // Cycle through slides based on their target durations
    (function autoAdvance() {{
        const dur = parseFloat(slides[current].getAttribute('data-duration')) || {SUBSLIDE_DURATION_SEC};
        const elapsed = (Date.now() - startTime) / 1000;
        if (elapsed >= dur) {{
            nextSlide();
        }}
        setTimeout(autoAdvance, 200);
    }})();
}})();
</script>
</body>
</html>"""


def _build_slide_body(
    visual: str, t: dict, title: str = "") -> str:
    """Build visually rich, scene-specific slide HTML with cinematic animations."""
    v = visual.lower()

    # ── Scene 1: Epic Introduction ─────────────────────────
    if "venn" in v or "introduction" in v or "welcome" in v:
        return f"""
    <div class="particles">
        {''.join(f'<div class="particle" style="left:{15+i*18}%;width:{4+i%4}px;height:{4+i%4}px;background:{t["primary"]};animation-duration:{6+i*2}s;animation-delay:{i*0.5}s"></div>' for i in range(12))}
    </div>

    <div class="center" style="position:relative;z-index:2">
        <div class="fade-in">
            <span class="badge">MODULE 1</span>
        </div>
        <h1 class="fade-in-d1" style="margin-top:30px">Computer Science<br>Fundamentals</h1>
        <p class="subtitle fade-in-d2">The Computational Mindset & Binary</p>

        <div class="card card-glow fade-in-d3" style="max-width:1000px;margin:60px auto 0">
            <h3 style="text-align:center;margin-bottom:30px;color:{t['text_dim']};font-weight:300">
                Computer Science is NOT just programming
            </h3>
            <div class="grid grid-4" style="gap:24px">
                <div class="card" style="border-color:{t['primary']};animation:none;text-align:center;padding:28px">
                    <div style="font-size:52px;margin-bottom:12px">⌨️</div>
                    <h3 style="color:{t['primary']};font-size:24px">Programming</h3>
                    <p style="color:{t['text_dim']};font-size:18px;margin-top:8px">The tool we use</p>
                </div>
                <div class="card" style="border-color:{t['secondary']};animation:none;text-align:center;padding:28px">
                    <div style="font-size:52px;margin-bottom:12px">🧠</div>
                    <h3 style="color:{t['secondary']};font-size:24px">Algorithms</h3>
                    <p style="color:{t['text_dim']};font-size:18px;margin-top:8px">Step-by-step logic</p>
                </div>
                <div class="card" style="border-color:{t['accent']};animation:none;text-align:center;padding:28px">
                    <div style="font-size:52px;margin-bottom:12px">💾</div>
                    <h3 style="color:{t['accent']};font-size:24px">Hardware</h3>
                    <p style="color:{t['text_dim']};font-size:18px;margin-top:8px">The physical machine</p>
                </div>
                <div class="card-glow" style="animation:none;text-align:center;padding:28px;box-shadow:0 0 40px {t['primary']}44">
                    <div style="font-size:52px;margin-bottom:12px">🎯</div>
                    <h3 class="highlight" style="font-size:24px">Problem Solving</h3>
                    <p style="color:{t['text_dim']};font-size:18px;margin-top:8px">The CORE of CS</p>
                </div>
            </div>
        </div>
    </div>"""

    # ── Scene 2: Binary & Light Switch ─────────────────────
    if "light switch" in v or "binary" in v or "base 2" in v:
        return f"""
    <div class="particles">
        {''.join(f'<div class="particle" style="left:{10+i*15}%;width:{3+i%5}px;height:{3+i%5}px;background:{t["accent"]};animation-duration:{5+i*1.5}s;animation-delay:{i*0.7}s"></div>' for i in range(10))}
    </div>

    <div class="center" style="position:relative;z-index:2">
        <h2 class="fade-in">💡 The Language of Computers</h2>

        <div class="split fade-in-d1" style="max-width:1100px;margin:0 auto">
            <div class="card" style="text-align:center">
                <div class="switch-anim">🔆</div>
                <div style="display:flex;gap:20px;justify-content:center;margin-top:20px">
                    <div class="card" style="padding:20px 40px;border-color:{t['accent']};animation:none">
                        <div style="font-size:72px;font-weight:900;color:{t['accent']};font-family:{t['mono']}">ON</div>
                        <div style="font-size:48px;color:#fab1a0;font-weight:800;font-family:{t['mono']};margin-top:8px">1</div>
                    </div>
                    <div class="card" style="padding:20px 40px;border-color:{t['text_dim']};animation:none">
                        <div style="font-size:72px;font-weight:900;color:{t['text_dim']};font-family:{t['mono']}">OFF</div>
                        <div style="font-size:48px;color:#6c7086;font-weight:800;font-family:{t['mono']};margin-top:8px">0</div>
                    </div>
                </div>
                <p style="color:{t['text_dim']};margin-top:16px;font-size:22px">Only two states: ON or OFF</p>
            </div>

            <div class="card">
                <h3 style="color:{t['secondary']};text-align:center;margin-bottom:20px">Binary Counting</h3>
                <div class="binary-display">
                    <span class="binary-bit">0</span>
                    <span class="binary-bit">1</span>
                    <span class="binary-bit" style="animation-delay:0.3s">10</span>
                    <span class="binary-bit" style="animation-delay:0.6s">11</span>
                    <span class="binary-bit" style="animation-delay:0.9s">100</span>
                </div>
                <div class="code-block mt-20" style="text-align:center;font-size:22px">
                    <span style="color:{t['text_dim']}">Human (Base 10):</span> 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, <span style="color:{t['accent']}">10</span><br>
                    <span style="color:{t['text_dim']}">Computer (Base 2):</span> 0, 1, <span style="color:{t['accent']}">10</span>, 11, 100, 101, 110, 111, <span style="color:{t['accent']}">1000</span>
                </div>
            </div>
        </div>

        <div class="card fade-in-d2" style="max-width:900px;margin:40px auto 0;text-align:center">
            <p style="font-size:30px;line-height:1.6">
                Humans use <span class="highlight">Base 10</span> (10 fingers) &nbsp;|&nbsp;
                Computers use <span class="highlight">Base 2</span> (ON or OFF)
            </p>
            <p style="font-size:24px;color:{t['text_dim']};margin-top:16px">
                "2" in binary = <span style="color:#fab1a0;font-weight:700;font-size:32px">10</span>
                &nbsp;&nbsp;
                "4" in binary = <span style="color:#fab1a0;font-weight:700;font-size:32px">100</span>
            </p>
        </div>
    </div>"""

    # ── Scene 3: ASCII & RGB ───────────────────────────────
    if "ascii" in v or "color" in v or "pixel" in v or "rgb" in v or "letter" in v:
        return f"""
    <div class="particles">
        {''.join(f'<div class="particle" style="left:{5+i*12}%;width:{3+i%6}px;height:{3+i%6}px;background:{t["secondary"]};animation-duration:{7+i}s;animation-delay:{i*0.6}s"></div>' for i in range(12))}
    </div>

    <div class="center" style="position:relative;z-index:2">
        <h2 class="fade-in">🔤 From 1s and 0s to Text & Images</h2>

        <div class="card fade-in-d1" style="max-width:1000px;margin:0 auto">
            <div style="text-align:center;margin-bottom:30px">
                <span class="badge" style="background:linear-gradient(135deg,{t['primary']},{t['secondary']})">ASCII ENCODING</span>
            </div>
            <div class="ascii-chain">
                <div class="card" style="text-align:center;padding:30px;animation:none;border-color:{t['primary']}">
                    <div style="font-size:80px;font-weight:900;color:{t['primary']};font-family:{t['mono']}">A</div>
                    <div style="color:{t['text_dim']};font-size:18px;margin-top:8px">Letter</div>
                </div>
                <div class="ascii-arrow">→</div>
                <div class="card" style="text-align:center;padding:30px;animation:none;border-color:{t['secondary']}">
                    <div style="font-size:80px;font-weight:900;color:{t['secondary']};font-family:{t['mono']}">65</div>
                    <div style="color:{t['text_dim']};font-size:18px;margin-top:8px">Number</div>
                </div>
                <div class="ascii-arrow">→</div>
                <div class="code-block" style="font-size:32px;padding:20px 30px;animation:none;border-color:{t['accent']}">
                    <span style="color:#fab1a0">01000001</span>
                </div>
            </div>
            <p style="text-align:center;margin-top:24px;font-size:22px;color:{t['text_dim']}">
                Every character → unique number → binary code
            </p>
        </div>

        <div class="card fade-in-d2" style="max-width:1000px;margin:40px auto 0">
            <div style="text-align:center;margin-bottom:24px">
                <span class="badge" style="background:linear-gradient(135deg,{t['accent']},{t['primary']})">RGB COLOR ENCODING</span>
            </div>
            <div class="grid grid-3" style="gap:24px;text-align:center">
                <div class="card" style="animation:none;border-color:#ff4444">
                    <div style="width:100px;height:100px;border-radius:50%;background:#ff0000;margin:0 auto;box-shadow:0 0 40px #ff000080"></div>
                    <div style="font-size:36px;font-weight:800;color:#ff6666;font-family:{t['mono']};margin-top:16px">R: 255</div>
                    <div style="color:{t['text_dim']};font-size:16px;margin-top:4px">11111111</div>
                </div>
                <div class="card" style="animation:none;border-color:#44ff44">
                    <div style="width:100px;height:100px;border-radius:50%;background:#006400;margin:0 auto;box-shadow:0 0 40px #00640080"></div>
                    <div style="font-size:36px;font-weight:800;color:#66ff66;font-family:{t['mono']};margin-top:16px">G: 100</div>
                    <div style="color:{t['text_dim']};font-size:16px;margin-top:4px">01100100</div>
                </div>
                <div class="card" style="animation:none;border-color:#ff8800">
                    <div style="width:100px;height:100px;border-radius:50%;background:#ff6600;margin:0 auto;box-shadow:0 0 40px #ff660080"></div>
                    <div style="font-size:36px;font-weight:800;color:#ffaa44;font-family:{t['mono']};margin-top:16px">B: 0</div>
                    <div style="color:{t['text_dim']};font-size:16px;margin-top:4px">00000000</div>
                </div>
            </div>
            <div style="text-align:center;margin-top:24px">
                <span style="font-size:48px">🍊</span>
                <p style="font-size:28px;margin-top:8px">
                    R:255 + G:100 + B:0 = <span class="highlight">Orange!</span>
                </p>
            </div>
        </div>

        <p class="fade-in-d3" style="font-size:24px;color:{t['text_dim']};margin-top:30px">
            Every photo, video, and game = billions of 1s and 0s flashing on and off
        </p>
    </div>"""

    # ── Scene 4: Algorithms & Pseudocode ───────────────────
    if "algorithm" in v or "pseudocode" in v or "recipe" in v or "flowchart" in v:
        return f"""
    <div class="particles">
        {''.join(f'<div class="particle" style="left:{8+i*14}%;width:{3+i%5}px;height:{3+i%5}px;background:{t["secondary"]};animation-duration:{6+i}s;animation-delay:{i*0.8}s"></div>' for i in range(10))}
    </div>

    <div class="center" style="position:relative;z-index:2">
        <h2 class="fade-in">📝 Algorithms & Pseudocode</h2>

        <div class="card fade-in-d1" style="max-width:850px;margin:0 auto;text-align:center">
            <div style="font-size:80px">📋 = 💻</div>
            <h3 style="margin:20px 0">An Algorithm is just a <span class="highlight">recipe</span></h3>
            <p style="font-size:26px;color:{t['text_dim']};line-height:1.6">
                Step-by-step instructions to solve a problem<br>
                Follow them in order — mix them up and you get a mess! 🍰❌
            </p>
        </div>

        <div class="card fade-in-d2" style="max-width:850px;margin:40px auto 0;text-align:left">
            <h3 style="color:{t['primary']};margin-bottom:20px">🔐 Pseudocode: Login System</h3>
            <div class="code-block" style="font-size:24px;line-height:2.2">
                <span style="color:#cba6f7">ASK</span> <span style="color:{t['text']}">user for password</span><br>
                <span style="color:#cba6f7">IF</span> <span style="color:{t['text']}">password is correct</span><br>
                &nbsp;&nbsp;<span style="color:#a6e3a1">THEN</span> <span style="color:{t['text']}">→ Log in ✅</span><br>
                <span style="color:#cba6f7">ELSE</span><br>
                &nbsp;&nbsp;<span style="color:#f38ba8">THEN</span> <span style="color:{t['text']}">→ Show error message ❌</span><br>
                &nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#cba6f7">RETRY</span>
            </div>
        </div>

        <div class="card fade-in-d3" style="max-width:700px;margin:40px auto 0;text-align:center">
            <h3 style="color:{t['accent']};margin-bottom:30px">Flowchart Visualization</h3>
            <div>
                <div class="flow-box flow-process">🔐 Ask for Password</div>
                <div class="flow-line"></div>
                <div class="flow-arrow">⬇</div>
                <div class="flow-box flow-decision">❓ Is it correct?</div>
                <div style="display:flex;gap:80px;justify-content:center;margin-top:20px">
                    <div style="text-align:center">
                        <div class="flow-arrow">⬇</div>
                        <div class="flow-box flow-process" style="font-size:22px">✅ Log In</div>
                    </div>
                    <div style="text-align:center">
                        <div class="flow-arrow">⬇</div>
                        <div class="flow-box" style="background:linear-gradient(135deg,{t['accent']}33,{t['accent']}11);border:2px solid {t['accent']};color:{t['accent']};font-size:22px">
                            ❌ Show Error → Retry
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>"""

    # ── Scene 5: Inputs, Outputs, Loops, Functions ─────────
    if "function" in v or "loop" in v or "input" in v or "output" in v or "factory" in v:
        return f"""
    <div class="particles">
        {''.join(f'<div class="particle" style="left:{5+i*16}%;width:{3+i%6}px;height:{3+i%6}px;background:{t["primary"]};animation-duration:{4+i*1.8}s;animation-delay:{i*0.5}s"></div>' for i in range(10))}
    </div>

    <div class="center" style="position:relative;z-index:2">
        <h2 class="fade-in">🧬 Building Blocks of Every Program</h2>

        <div class="card fade-in-d1" style="max-width:1000px;margin:0 auto">
            <h3 style="text-align:center;color:{t['primary']};margin-bottom:30px">📥 Input → ⚙️ Function → 📤 Output</h3>
            <div class="factory-visual">
                <div class="card" style="text-align:center;animation:none;padding:30px;border-color:{t['primary']}">
                    <div style="font-size:80px">📥</div>
                    <div style="font-size:22px;color:{t['primary']};margin-top:12px;font-weight:700">INPUT</div>
                    <p style="color:{t['text_dim']};font-size:18px">Data in</p>
                </div>
                <div style="font-size:48px;color:{t['text_dim']}">➡️</div>
                <div class="factory-machine">
                    <div style="text-align:center">
                        <div style="font-size:48px">⚙️</div>
                        <div style="color:white;font-weight:800;font-size:24px;margin-top:8px">FUNCTION</div>
                    </div>
                </div>
                <div style="font-size:48px;color:{t['text_dim']}">➡️</div>
                <div class="card" style="text-align:center;animation:none;padding:30px;border-color:{t['secondary']}">
                    <div style="font-size:80px">📤</div>
                    <div style="font-size:22px;color:{t['secondary']};margin-top:12px;font-weight:700">OUTPUT</div>
                    <p style="color:{t['text_dim']};font-size:18px">Result out</p>
                </div>
            </div>
        </div>

        <div class="card fade-in-d2" style="max-width:900px;margin:40px auto 0">
            <h3 style="color:{t['accent']};text-align:center;margin-bottom:20px">🔄 Loops — Do It Again & Again</h3>
            <div class="grid grid-3" style="gap:24px;text-align:center">
                <div class="card" style="animation:none;padding:30px">
                    <div style="font-size:72px">🔄</div>
                    <h4 style="color:{t['primary']};margin-top:12px">Repeat</h4>
                    <p style="color:{t['text_dim']};font-size:18px">Do task N times</p>
                </div>
                <div class="card" style="animation:none;padding:30px">
                    <div style="font-size:72px">🔀</div>
                    <h4 style="color:{t['secondary']};margin-top:12px">Condition</h4>
                    <p style="color:{t['text_dim']};font-size:18px">While true, keep going</p>
                </div>
                <div class="card" style="animation:none;padding:30px">
                    <div style="font-size:72px">⏭️</div>
                    <h4 style="color:{t['accent']};margin-top:12px">Break</h4>
                    <p style="color:{t['text_dim']};font-size:18px">Stop when done</p>
                </div>
            </div>
        </div>

        <div class="card fade-in-d3" style="max-width:900px;margin:40px auto 0;text-align:center">
            <h3 style="color:{t['secondary']};margin-bottom:20px">🧬 The DNA of Every Program</h3>
            <div class="emoji-row">
                <div class="card" style="animation:none;padding:20px 30px">
                    <div style="font-size:48px">📥</div><div style="font-size:18px;margin-top:8px">Inputs</div>
                </div>
                <div style="font-size:36px;color:{t['text_dim']}">→</div>
                <div class="card" style="animation:none;padding:20px 30px">
                    <div style="font-size:48px">⚙️</div><div style="font-size:18px;margin-top:8px">Functions</div>
                </div>
                <div style="font-size:36px;color:{t['text_dim']}">→</div>
                <div class="card" style="animation:none;padding:20px 30px">
                    <div style="font-size:48px">🔀</div><div style="font-size:18px;margin-top:8px">Conditions</div>
                </div>
                <div style="font-size:36px;color:{t['text_dim']}">→</div>
                <div class="card" style="animation:none;padding:20px 30px">
                    <div style="font-size:48px">🔄</div><div style="font-size:18px;margin-top:8px">Loops</div>
                </div>
                <div style="font-size:36px;color:{t['text_dim']}">→</div>
                <div class="card" style="animation:none;padding:20px 30px;border-color:{t['accent']}">
                    <div style="font-size:48px">📤</div><div style="font-size:18px;margin-top:8px">Outputs</div>
                </div>
            </div>
            <p style="margin-top:24px;font-size:22px;color:{t['text_dim']}">
                From your phone's OS to rockets landing on drone ships
            </p>
        </div>
    </div>"""

    # ── Scene 6: Conclusion & Assignment ───────────────────
    if "conclusion" in v or "assignment" in v or "peanut" in v:
        return f"""
    <div class="particles">
        {''.join(f'<div class="particle" style="left:{random.randint(5,95)}%;width:{4+random.randint(0,8)}px;height:{4+random.randint(0,8)}px;background:{random.choice([t["primary"],t["secondary"],t["accent"]])};animation-duration:{4+random.randint(0,6)}s;animation-delay:{random.randint(0,5)*0.3}s"></div>' for i in range(20))}
    </div>

    <div class="center" style="position:relative;z-index:2">
        <div class="fade-in">
            <div style="font-size:100px">🎓</div>
            <h1 class="glow" style="margin-top:20px">Congratulations!</h1>
            <p style="font-size:36px;color:{t['secondary']};margin-top:16px;font-weight:300">
                You've completed <span class="highlight">Module 1</span>
            </p>
        </div>

        <div class="card fade-in-d1" style="max-width:900px;margin:40px auto 0">
            <h3 style="color:{t['primary']};margin-bottom:20px">📋 What You Learned</h3>
            <div class="grid grid-3" style="gap:20px;text-align:center">
                <div><div style="font-size:48px">💡</div><p style="margin-top:8px">Binary: 1s & 0s</p></div>
                <div><div style="font-size:48px">🔤</div><p style="margin-top:8px">ASCII & RGB Codes</p></div>
                <div><div style="font-size:48px">🧠</div><p style="margin-top:8px">Algorithms & Logic</p></div>
            </div>
        </div>

        <div class="assignment-box fade-in-d2" style="max-width:850px;margin:40px auto 0">
            <h3 style="color:{t['accent']};font-size:40px">📝 Your Assignment</h3>
            <p style="font-size:32px;margin-top:20px;line-height:1.5">
                Write Pseudocode for making a<br>
                <span class="highlight" style="font-size:42px">Peanut Butter & Jelly Sandwich</span> 🥪
            </p>
            <p style="font-size:22px;color:{t['text_dim']};margin-top:20px">
                💡 Remember: computers are dumb!<br>
                Tell them <span style="color:{t['accent']}">EVERY</span> step — including opening the jar! 😄
            </p>
        </div>

        <div class="fade-in-d3" style="margin-top:40px">
            <p style="font-size:28px;color:{t['text_dim']}">
                Next Module: <span class="highlight" style="font-size:32px">The C Programming Language</span> 🚀
            </p>
        </div>
    </div>"""

    # ── Default fallback ───────────────────────────────────
    return f"""
    <div class="center" style="padding:100px">
        <h1>{title}</h1>
        <p style="font-size:28px;color:{t['text_dim']};margin-top:20px">{visual[:400]}</p>
    </div>"""


def generate_all_slides(scenes: list[dict], scenes_dir: Path) -> list[Path]:
    """Generate HTML slides for all scenes — each scene is a multi-sub-slide carousel."""
    scenes_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, scene in enumerate(scenes):
        # Split narration into ~20s sub-slide chunks
        subslides = split_narration_for_subslides(scene)
        scene_with_subslides = dict(scene)
        scene_with_subslides["subslides"] = subslides
        log.info("  Scene %d: %d sub-slides (%.1fs each avg)", i + 1, len(subslides),
                  sum(s["target_seconds"] for s in subslides) / max(len(subslides), 1))

        html = create_slide_html(scene_with_subslides, i)
        path = scenes_dir / f"scene-{i+1:02d}.html"
        path.write_text(html, encoding="utf-8")
        paths.append(path)
        log.info("Generated slide: %s (%d sub-slides)", path.name, len(subslides))
    return paths


# ═══════════════════════════════════════════════════════════════════════════════
# 4.  AUDIO GENERATION  (mirrors v2 pipeline: async batch + silent fallback)
# ═══════════════════════════════════════════════════════════════════════════════

def estimate_duration(text: str) -> float:
    """Estimate narration duration in seconds based on word count."""
    words = len(text.split())
    return words / WPM * 60


def get_audio_duration(path: Path) -> float:
    """Return duration in seconds using ffprobe."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(r.stdout)
        return float(data["format"].get("duration", 0))
    except Exception:
        return 0.0


def make_silent_audio(output_path: Path, duration: float = 1.0) -> bool:
    """Create a silent MP3 placeholder via FFmpeg."""
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i",
             f"anullsrc=r=44100:cl=mono", "-t", str(duration),
             str(output_path)],
            capture_output=True, timeout=15, check=True,
        )
        return True
    except Exception:
        return False


async def _generate_one_audio(
    idx: int,
    scene: dict,
    semaphore: asyncio.Semaphore,
    audio_dir: Path,
) -> tuple[int, Path, dict]:
    """Generate narration for a single scene. Uses edge-tts (free) by default, falls back to ElevenLabs."""
    async with semaphore:
        text = scene["narration"]
        output_path = audio_dir / f"scene-{idx+1:02d}.mp3"

        # Skip if already exists
        if output_path.exists() and output_path.stat().st_size > 1000:
            log.info("  Scene %d: audio exists, skipping", idx + 1)
            duration = get_audio_duration(output_path)
            return idx, output_path, {"duration": duration, "cached": True}

        log.info("  Scene %d: requesting TTS (%d words)...", idx + 1, len(text.split()))

        # ── Primary: edge-tts (free, no API key) ─────────────
        if TTS_PROVIDER == "edge":
            try:
                import edge_tts  # noqa: E402
                voice = scene.get("edge_voice", EDGE_TTS_VOICE)
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(str(output_path))
                duration = get_audio_duration(output_path)
                log.info("  Scene %d: ✓ audio via edge-tts (%.1fs)", idx + 1, duration)
                return idx, output_path, {"duration": duration, "provider": "edge-tts"}
            except Exception as e:
                log.warning("  Scene %d: edge-tts failed (%s), trying ElevenLabs...", idx + 1, e)

        # ── Fallback: ElevenLabs cloud ───────────────────────
        if ELEVENLABS_API_KEY and ELEVENLABS_API_KEY not in ("", "your-elevenlabs-key-here"):
            try:
                import httpx  # noqa: E402
                voice_id = scene.get("voice_id", VOICE_ID)
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(
                        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                        headers={
                            "xi-api-key": ELEVENLABS_API_KEY,
                            "Content-Type": "application/json",
                            "Accept": "audio/mpeg",
                        },
                        json={
                            "text": text,
                            "model_id": "eleven_multilingual_v2",
                            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                        },
                    )
                    resp.raise_for_status()
                    output_path.write_bytes(resp.content)
                duration = get_audio_duration(output_path)
                log.info("  Scene %d: ✓ audio via ElevenLabs (%.1fs)", idx + 1, duration)
                return idx, output_path, {"duration": duration, "provider": "elevenlabs"}
            except Exception as e:
                log.error("  Scene %d: ElevenLabs also failed (%s)", idx + 1, e)

        # ── Last resort: silent placeholder ──────────────────
        log.warning("  Scene %d: all TTS providers failed — silent placeholder", idx + 1)
        silent_path = audio_dir / f"scene-{idx+1:02d}_silent.mp3"
        make_silent_audio(silent_path)
        return idx, silent_path, {"duration": 0.0, "error": "all_tts_failed"}


async def generate_all_narration_async(
    scenes: list[dict],
    audio_dir: Path,
) -> list[dict]:
    """Generate narration audio for all scenes concurrently (max 4 at a time)."""
    audio_dir.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(4)

    tasks = [_generate_one_audio(i, s, semaphore, audio_dir) for i, s in enumerate(scenes)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Attach audio info back to scenes
    updated = list(scenes)
    for r in results:
        if isinstance(r, BaseException):
            log.error("Batch audio error: %s", r)
            continue
        if not isinstance(r, tuple) or len(r) != 3:
            log.error("Unexpected audio result: %r", r)
            continue
        idx, path, info = r
        updated[idx]["audio_path"] = str(path)
        updated[idx]["audio_duration"] = info.get("duration", 0.0)
        if "error" in info:
            updated[idx]["audio_error"] = info["error"]

    return updated


# ═══════════════════════════════════════════════════════════════════════════════
# 5.  HTML → VIDEO (render slides as video segments)
# ═══════════════════════════════════════════════════════════════════════════════

def check_playwright() -> bool:
    """Check if Playwright is available for HTML rendering."""
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def _write_render_helper() -> Path:
    """Write a standalone render script used in a subprocess (avoids asyncio/sync conflict)."""
    helper = Path(__file__).parent / "_render_slide.py"
    helper.write_text(r'''"""Standalone HTML-slide to video recorder (run in own process).

Records the HTML page (with its JS-driven sub-slide carousel) for the given
duration using Playwright's native video recording, then exits.
"""
import sys
import time
from pathlib import Path

html_path = Path(sys.argv[1])
duration = float(sys.argv[2])
width = int(sys.argv[3])
height = int(sys.argv[4])
record_dir = Path(sys.argv[5])

try:
    from playwright.sync_api import sync_playwright

    # Allow small extra time so the last slide transitions complete
    record_duration = duration + 1.0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=[
                "--disable-web-security",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--autoplay-policy=no-user-gesture-required",
            ],
        )
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
            record_video_dir=str(record_dir),
            record_video_size={"width": width, "height": height},
        )
        page = context.new_page()
        page.goto(f"file:///{html_path.as_posix()}")
        # Wait for page load + JS to initialize
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(500)

        # Wait for the required duration while animations run
        time.sleep(record_duration)

        # Save the video
        video_path = page.video.path()
        page.close()
        context.close()
        browser.close()

    # Move the video to a predictable location
    import shutil
    final_path = record_dir / "output.webm"
    shutil.move(video_path, str(final_path))
    print("OK")
except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stderr)
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
''', encoding="utf-8")
    return helper


_RENDER_HELPER = _write_render_helper()


def render_slide_to_video(html_path: Path, output_path: Path, duration: float) -> bool:
    """Render an HTML slide carousel to a real video with animation playback.

    Uses Playwright's video recording to capture the live page (with JS
    transitions and CSS animations) for the full scene duration, then
    transcodes the WebM to H.264 MP4 via FFmpeg.
    """

    # Create a temporary directory for the video recording
    record_dir = output_path.parent / f"_rec_{output_path.stem}"
    record_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Step 1: Record the HTML page with Playwright
        result = subprocess.run(
            [sys.executable, str(_RENDER_HELPER),
             str(html_path), str(duration),
             str(WIDTH), str(HEIGHT), str(record_dir)],
            capture_output=True, text=True, timeout=int(duration + 60),
        )

        if result.returncode != 0:
            log.error("Playwright recording failed: %s", result.stderr.strip()[-400:] if result.stderr else "unknown")
            return False

        webm_path = record_dir / "output.webm"
        if not webm_path.exists():
            log.error("Recording produced no output.webm")
            return False

        # Step 2: Transcode WebM → MP4 (H.264)
        try:
            result = subprocess.run([
                "ffmpeg", "-y",
                "-i", str(webm_path),
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-vf", f"fps=30,scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:-1:-1:color=#0a0a1a,format=yuv420p",
                "-an",  # audio will be added by concat stage
                "-movflags", "+faststart",
                "-t", str(duration),
                str(output_path),
            ], capture_output=True, text=True, timeout=180)

            if result.returncode == 0:
                log.info("  ✓ Rendered %s (%.1fs, animated)", output_path.name, duration)
                return True
            else:
                log.error("FFmpeg transcode failed: %s", result.stderr[-300:])
                return False
        except subprocess.TimeoutExpired:
            log.error("FFmpeg transcode timed out for %s", output_path.name)
            return False
        except Exception as e:
            log.error("Transcode error: %s", e)
            return False

    finally:
        # Always clean up the recording directory
        import shutil
        if record_dir.exists():
            shutil.rmtree(record_dir, ignore_errors=True)


def render_all_scenes(scenes: list[dict], scenes_dir: Path, videos_dir: Path) -> list[Path]:
    """Render all scene HTML slides to video segments."""
    videos_dir.mkdir(parents=True, exist_ok=True)
    video_paths = []

    for i, scene in enumerate(scenes):
        html_path = scenes_dir / f"scene-{i+1:02d}.html"
        video_path = videos_dir / f"scene-{i+1:02d}.mp4"
        # code delete mt krna 
        audio_duration = float(scene.get("audio_duration", 0))
        duration = audio_duration + 1.0 if audio_duration > 0 else float(scene.get("estimated_duration") or scene["duration_seconds"])
        # duration = float(scene.get("estimated_duration") or scene["duration_seconds"])

        if not html_path.exists():
            log.warning("Missing HTML for scene %d, skipping", i + 1)
            continue

        log.info("Rendering scene %d/%d...", i + 1, len(scenes))

        if not render_slide_to_video(html_path, video_path, duration):
            log.error("Failed to render scene %d", i + 1)
            continue

        video_paths.append(video_path)

    return video_paths


# ═══════════════════════════════════════════════════════════════════════════════
# 6.  FINAL COMPOSITION
# ═══════════════════════════════════════════════════════════════════════════════

def concat_scenes_with_audio(scenes: list[dict], video_paths: list[Path], _audio_dir: Path, output_path: Path) -> bool:
    """Concatenate scene videos with narration audio into final video."""
    log.info("Compositing final video...")

    # Create a concat file list for ffmpeg
    concat_file = output_path.parent / "concat.txt"
    video_clips = []

    for i, (scene, video_path) in enumerate(zip(scenes, video_paths)):
        if not video_path.exists():
            continue

        audio_path = Path(scene.get("audio_path", ""))
        template_duration = float(scene.get("duration_seconds", 0))
        audio_duration = float(scene.get("audio_duration", 0))
        # Final duration: video drives, audio plays once. If template duration
        # is shorter than audio (rare), honor audio.
        # ye remove mt krna ok 
        duration = audio_duration + 1.0 if audio_duration > 0 else template_duration
        # duration = max(template_duration, audio_duration) if audio_duration > 0 else template_duration

        if audio_path.exists() and audio_path.stat().st_size > 1000:
            # Scene has narration — combine video + audio.
            # Video drives total length (template duration).
            # Audio plays once; remainder is silence (apad).
            scene_output = output_path.parent / f"sc_{i+1:02d}.mp4"
            result = subprocess.run([
                "ffmpeg", "-y",
                "-i", str(video_path),
                "-i", str(audio_path),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-af", "apad=pad_dur=999",  # pad audio with silence to fill video
                "-t", str(duration),
                str(scene_output),
            ], capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                video_clips.append(scene_output)
            else:
                log.warning("Scene %d audio merge failed, using video only", i + 1)
                video_clips.append(video_path)
        else:
            # No narration — just use the video
            video_clips.append(video_path)

    if not video_clips:
        log.error("No video clips to concatenate!")
        return False

    # Write concat list
    entries = [v.resolve() for v in video_clips]
    concat_file.write_text("".join(f"file '{v.as_posix()}'\n" for v in entries), encoding="utf-8")
    # ye code pahle the comment out ko remove mt krna or niche wali 3 line ko bhi remove mt krna ok 
    # concat_file.write_text("".join(f"file '{v.as_posix()}'\n" for v in video_clips), encoding="utf-8")
    
    

    # Concatenate all scenes (no re-encode since all segments share same codec)
    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        # "-i", str(concat_file), //ise remove mt krna aap ok 
        "-i", str(concat_file.resolve()),
        "-c", "copy", "-movflags", "+faststart",
        str(output_path),
    ], capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        log.error("FFmpeg concat error: %s", result.stderr[-1000:])
        return False

    size_mb = output_path.stat().st_size / (1024 * 1024)
    log.info("✓ Final video: %s (%.1f MB)", output_path, size_mb)
    return True


def add_intro_outro(final_path: Path, output_path: Path) -> bool:
    """Add intro and outro sequences."""
    # Simple: just copy for now — could add title card / credits later
    import shutil
    shutil.copy2(final_path, output_path)
    return True


def generate_thumbnail(final_path: Path, thumb_path: Path, timestamp: float = 5.0) -> bool:
    """Generate a thumbnail from the video at the given timestamp."""
    result = subprocess.run([
        "ffmpeg", "-y", "-ss", str(timestamp), "-i", str(final_path),
        "-vframes", "1", "-vf", f"scale={WIDTH}:{HEIGHT}",
        str(thumb_path),
    ], capture_output=True, text=True, timeout=30)

    if result.returncode == 0:
        log.info("✓ Thumbnail: %s", thumb_path)
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# 7.  MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

async def run_pipeline(project_dir: Path, topic: str, subtopic: str, explanation: str, skip_audio: bool = False) -> Path:
    """Run the complete video generation pipeline."""

    # ── Step 1: Load script ──────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STEP 1: Loading script")
    log.info("=" * 60)
    project_dir.mkdir(parents=True, exist_ok=True)
    script_text = load_or_create_script(project_dir, topic, subtopic, explanation)

    # ── Step 2: Parse scenes ─────────────────────────────────────────────────
    log.info("")
    log.info("=" * 60)
    log.info("STEP 2: Parsing scenes")
    log.info("=" * 60)
    scenes = parse_scenes(script_text)

    # Save scenes metadata
    scenes_meta_path = project_dir / "scenes.json"
    scenes_meta_path.write_text(json.dumps(scenes, indent=2), encoding="utf-8")
    log.info("Saved scene metadata to %s", scenes_meta_path)

    # ── Step 3: Generate HTML slides ─────────────────────────────────────────
    log.info("")
    log.info("=" * 60)
    log.info("STEP 3: Generating HTML slides (Presenton-style)")
    log.info("=" * 60)
    scenes_dir = project_dir / "scenes" / "html"
    slide_paths = generate_all_slides(scenes, scenes_dir)
    log.info("✓ Generated %d slides", len(slide_paths))

    # ── Step 4: Generate narration audio ────────────────────────────────────
    log.info("")
    log.info("=" * 60)
    log.info("STEP 4: Generating narration audio")
    log.info("=" * 60)
    audio_dir = project_dir / "audio" / "narration"

    if skip_audio:
        log.info("⚠ Skipping audio generation (--skip-audio)")
        for scene in scenes:
            scene["audio_path"] = ""
            scene["audio_duration"] = 0
            scene["estimated_duration"] = scene["duration_seconds"]
    else:
        scenes = await generate_all_narration_async(scenes, audio_dir)

        total_words = sum(len(s["narration"].split()) for s in scenes)
        total_audio = sum(s.get("audio_duration", 0) for s in scenes)
        log.info("✓ Generated narration: %d words, %.1f min total audio", total_words, total_audio / 60)

    # ── Step 5: Render scenes to video ──────────────────────────────────────
    log.info("")
    log.info("=" * 60)
    log.info("STEP 5: Rendering scenes to video segments")
    log.info("=" * 60)
    videos_dir = project_dir / "scenes" / "videos"
    video_paths = render_all_scenes(scenes, scenes_dir, videos_dir)
    log.info("✓ Rendered %d video segments", len(video_paths))

    if not video_paths:
        log.error("No video segments rendered — cannot continue")
        return project_dir

    # ── Step 6: Final composition ────────────────────────────────────────────
    log.info("")
    log.info("=" * 60)
    log.info("STEP 6: Final composition")
    log.info("=" * 60)
    renders_dir = project_dir / "renders"
    renders_dir.mkdir(parents=True, exist_ok=True)
    final_path = renders_dir / "final.mp4"

    success = concat_scenes_with_audio(scenes, video_paths, audio_dir, final_path)
    if not success:
        log.error("Final composition failed!")
        return project_dir

    # ── Step 7: Post-processing ──────────────────────────────────────────────
    log.info("")
    log.info("=" * 60)
    log.info("STEP 7: Post-processing")
    log.info("=" * 60)
    output_path = renders_dir / "video.mp4"
    add_intro_outro(final_path, output_path)
    generate_thumbnail(output_path, renders_dir / "thumbnail.jpg")

    # ── Summary ──────────────────────────────────────────────────────────────
    log.info("")
    log.info("=" * 60)
    log.info("🎬 VIDEO GENERATION COMPLETE!")
    log.info("=" * 60)
    log.info("  Output:  %s", output_path)
    log.info("  Scenes:  %d", len(scenes))
    log.info("  Slides:  %s", scenes_dir)
    log.info("  Audio:   %s", audio_dir)
    log.info("  Videos:  %s", videos_dir)
    log.info("=" * 60)

    # Print scene summary
    total_dur = sum(float(s.get("estimated_duration") or s["duration_seconds"]) for s in scenes)
    log.info("Total estimated duration: %.1f minutes", total_dur / 60)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="VideoForge — Educational Video Generator")
    parser.add_argument("--project-dir", type=str, default=None,
                        help="Project directory (default: ./projects/cs-module1)")
    parser.add_argument("--topic", type=str, default="", help="Video topic")
    parser.add_argument("--subtopic", type=str, default="", help="Video subtopic")
    parser.add_argument("--explanation", type=str, default="", help="Additional context")
    parser.add_argument("--skip-audio", action="store_true", help="Skip audio generation")
    args = parser.parse_args()

    topic = args.topic or "Computer Science Fundamentals"
    subtopic = args.subtopic or "The Computational Mindset & Binary"
    explanation = args.explanation or (
        "This module introduces absolute beginners to how computers think, work, "
        "and solve problems. Covers binary, ASCII, RGB, algorithms, pseudocode, "
        "inputs/outputs, functions, conditions, and loops."
    )

    project_name = "cs-module1"
    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = PROJECTS_DIR / project_name

    log.info("VideoForge — Educational Video Generator")
    log.info("Topic: %s", topic)
    log.info("Subtopic: %s", subtopic)
    log.info("Project: %s", project_dir)

    output = asyncio.run(run_pipeline(project_dir, topic, subtopic, explanation, args.skip_audio))
    log.info("Done! Output: %s", output)


if __name__ == "__main__":
    main()
