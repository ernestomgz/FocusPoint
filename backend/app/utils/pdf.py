from pathlib import Path
from weasyprint import HTML, CSS

def render_html_to_pdf(html_str: str, output_path: Path, css_paths: list[Path] | None = None):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    css_objs = [CSS(filename=str(p)) for p in (css_paths or [])]
    HTML(string=html_str).write_pdf(str(output_path), stylesheets=css_objs)
    return output_path

