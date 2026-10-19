"""Content generators for visual assets."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class CodeVisualizationGenerator:
    """Generates code visualization HTML for code_viz scenes."""

    async def generate(
        self,
        code: str,
        language: str = "python",
        title: str = "",
        theme: str = "dark",
    ) -> str:
        """Generate an HTML page with syntax-highlighted code."""
        escaped = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title or language.title()}</title>
<style>
  body {{ margin:0; background:#0d1117; color:#c9d1d9; font-family:'Fira Code','Consolas',monospace; padding:40px; }}
  .header {{ color:#58a6ff; font-size:1.5em; margin-bottom:20px; }}
  pre {{ background:#161b22; padding:20px; border-radius:8px; overflow-x:auto; line-height:1.6; }}
</style>
</head>
<body>
<div class="header">{title or language.title()}</div>
<pre>{escaped}</pre>
</body>
</html>"""


class ChartGenerator:
    """Generates chart visualizations using HTML/CSS/JS."""

    async def generate_bar_chart(
        self,
        data: dict[str, float],
        title: str = "",
        x_label: str = "",
        y_label: str = "",
    ) -> str:
        """Generate an HTML bar chart."""
        return self._fallback_chart_html(data, title, "bar")

    async def generate_line_chart(
        self,
        data: dict[str, list[float]],
        title: str = "",
        x_label: str = "",
        y_label: str = "",
    ) -> str:
        """Generate an HTML line chart."""
        return self._fallback_chart_html(data, title, "line")

    async def generate_pie_chart(
        self,
        data: dict[str, float],
        title: str = "",
    ) -> str:
        """Generate an HTML pie/doughnut chart."""
        return self._fallback_chart_html(data, title, "doughnut")

    def _fallback_chart_html(self, data: dict, title: str, chart_type: str) -> str:
        """Generate a simple fallback chart HTML using Chart.js."""
        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  body {{ margin:0; background:#0d1117; color:#fff; font-family:'Segoe UI',sans-serif; display:flex; align-items:center; justify-content:center; height:100vh; padding:40px; }}
  .chart-container {{ width:90%; max-width:1200px; }}
  h2 {{ color:#e94560; text-align:center; }}
</style></head>
<body>
<div class="chart-container">
  <h2>{title}</h2>
  <canvas id="chart"></canvas>
</div>
<script>
  const ctx = document.getElementById('chart').getContext('2d');
  new Chart(ctx, {{
    type: '{chart_type}',
    data: {{
      labels: {list(data.keys())!r},
      datasets: [{{ label: '{title}', data: {list(data.values())!r}, backgroundColor: '#e94560' }}]
    }},
    options: {{ responsive: true, plugins: {{ legend: {{ labels: {{ color: '#fff' }} }} }} }}
  }});
</script>
</body></html>"""


class DiagramGenerator:
    """Generates diagram visualizations."""

    async def generate_flowchart(
        self,
        nodes: list[str],
        edges: list[tuple[str, str]],
        title: str = "",
    ) -> str:
        """Generate an HTML flowchart using Mermaid.js."""
        return self._fallback_diagram_html(nodes, edges, title)

    def _fallback_diagram_html(self, nodes: list[str], edges: list[tuple[str, str]], title: str) -> str:
        """Generate a simple fallback diagram HTML using Mermaid."""
        mermaid_edges = "\n  ".join(f"{e[0]} --> {e[1]}" for e in edges)
        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<style>
  body {{ margin:0; background:#0d1117; color:#fff; font-family:'Segoe UI',sans-serif; padding:40px; }}
  h2 {{ color:#e94560; text-align:center; }}
</style></head>
<body>
<h2>{title}</h2>
<div class="mermaid">
graph TD
  {mermaid_edges}
</div>
<script>mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});</script>
</body></html>"""
