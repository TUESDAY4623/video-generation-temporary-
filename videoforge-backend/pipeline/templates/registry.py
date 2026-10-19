"""Template registry for rendering HTML scene templates."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TemplateRegistry:
    """Manages HTML templates for video scenes."""

    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, str] = {}

    def get_template(self, name: str) -> str | None:
        """Get a template by name."""
        if name in self._cache:
            return self._cache[name]

        template_path = self.templates_dir / name
        if not template_path.exists():
            return None

        content = template_path.read_text(encoding="utf-8")
        self._cache[name] = content
        return content

    def render_template(self, name: str, context: dict[str, Any]) -> str:
        """Render a template with the given context."""
        template = self.get_template(name)
        if template is None:
            logger.warning(f"Template {name} not found, using inline template")
            return build_inline_template(name.split("/")[-1].replace(".html", ""), context)

        return self._render(template, context)

    def _render(self, template: str, context: dict[str, Any]) -> str:
        """Simple template rendering with {{key}} substitution."""
        result = template
        for key, value in context.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    placeholder = "{{" + f"{key}.{sub_key}" + "}}"
                    result = result.replace(placeholder, str(sub_value))
            else:
                placeholder = "{{" + key + "}}"
                result = result.replace(placeholder, str(value))
        return result

    def list_templates(self) -> list[str]:
        """List all available templates."""
        return [f.name for f in self.templates_dir.rglob("*.html")]

    def register_template(self, name: str, content: str) -> None:
        """Register a template programmatically."""
        self._cache[name] = content
        template_path = self.templates_dir / name
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text(content, encoding="utf-8")


def build_inline_template(scene_type: str, context: dict[str, Any]) -> str:
    """Build a simple inline HTML template for a scene type."""
    title = _esc(context.get("title", ""))
    text = _esc(context.get("text", ""))
    topic = _esc(context.get("topic", ""))
    palette = context.get("palette", {
        "primary": "#1a1a2e",
        "secondary": "#16213e",
        "accent": "#e94560",
        "text": "#ffffff",
        "text_secondary": "#a0a0a0",
        "background": "#0f0f23",
    })

    if scene_type == "hero_title":
        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
  body {{ margin:0; background:{palette.get('background', '#0f0f23')}; color:{palette.get('text', '#fff')}; font-family:'Segoe UI',sans-serif; display:flex; align-items:center; justify-content:center; height:100vh; overflow:hidden; }}
  .container {{ text-align:center; padding:40px; max-width:1200px; }}
  h1 {{ font-size:4em; color:{palette.get('accent', '#e94560')}; margin-bottom:20px; text-shadow:0 4px 20px rgba(0,0,0,0.5); }}
  .subtitle {{ font-size:1.8em; color:{palette.get('text_secondary', '#a0a0a0')}; animation: fadeIn 2s ease-in; }}
  @keyframes fadeIn {{ from {{ opacity:0; transform:translateY(20px); }} to {{ opacity:1; transform:translateY(0); }} }}
</style></head>
<body><div class="container"><h1>{title}</h1><p class="subtitle">{topic}</p></div></body></html>"""

    if scene_type == "stat_card":
        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
  body {{ margin:0; background:{palette.get('primary', '#1a1a2e')}; color:{palette.get('text', '#fff')}; font-family:'Segoe UI',sans-serif; display:flex; align-items:center; justify-content:center; height:100vh; }}
  .stat-box {{ text-align:center; padding:60px; background:{palette.get('secondary', '#16213e')}; border-radius:20px; border-left:6px solid {palette.get('accent', '#e94560')}; box-shadow:0 10px 40px rgba(0,0,0,0.3); }}
  .number {{ font-size:6em; font-weight:bold; color:{palette.get('accent', '#e94560')}; }}
  .label {{ font-size:1.5em; color:{palette.get('text_secondary', '#a0a0a0')}; margin-top:10px; }}
</style></head>
<body><div class="stat-box"><div class="number">{title}</div><div class="label">{text}</div></div></body></html>"""

    # Default: text_card
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
  body {{ margin:0; background:{palette.get('background', '#0f0f23')}; color:{palette.get('text', '#fff')}; font-family:'Segoe UI',sans-serif; display:flex; align-items:center; justify-content:center; height:100vh; padding:60px; box-sizing:border-box; }}
  .content {{ max-width:1000px; }}
  h2 {{ font-size:2.5em; color:{palette.get('accent', '#e94560')}; margin-bottom:30px; }}
  p {{ font-size:1.4em; line-height:1.8; color:{palette.get('text_secondary', '#a0a0a0')}; }}
</style></head>
<body><div class="content"><h2>{title}</h2><p>{text}</p></div></body></html>"""


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return (text.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;"))
