"""Optional reproducible PDF copies. Markdown remains the approved retrieval source."""
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from xml.sax.saxutils import escape

root=Path(__file__).resolve().parents[1]/'knowledge_base'
(root/'pdf').mkdir(exist_ok=True)
styles=getSampleStyleSheet()
for path in (root/'markdown').glob('*.md'):
    story=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        if line:
            style='Title' if line.startswith('# ') else 'Heading2' if line.startswith('## ') else 'BodyText'
            story.extend([Paragraph(escape(line.lstrip('# ')),styles[style]),Spacer(1,10)])
    SimpleDocTemplate(str(root/'pdf'/f'{path.stem}.pdf'),pagesize=A4).build(story)
print('Generated optional fictional policy PDF copies.')
