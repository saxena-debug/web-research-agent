import re
from pathlib import Path
import config


def _md_to_html(text):
    # handle bold headers GPT sometimes outputs instead of proper heading tags
    text = re.sub(r'^\*\*([^\n]+?)\*\*$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$',  r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$',   r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*',   r'<em>\1</em>', text)

    def replace_list(m):
        items = m.group(0).strip().split('\n')
        lis = ''.join('<li>' + item.lstrip('- ').strip() + '</li>' for item in items if item.strip())
        return '<ul>' + lis + '</ul>'

    text = re.sub(r'(^- .+$\n?)+', replace_list, text, flags=re.MULTILINE)

    # wrap loose text in <p> tags
    parts = re.split(r'\n{2,}', text.strip())
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p.startswith('<'):
            out.append(p)
        else:
            out.append('<p>' + p + '</p>')

    return '\n'.join(out)


def export_html(result):
    report_dir = Path(config.REPORT_DIR)
    report_dir.mkdir(parents=True, exist_ok=True)

    run_id  = result['run_id']
    goal    = result['goal']
    elapsed = result['total_time']
    tokens  = result['total_tokens']
    score   = result['quality_score']

    report_html = _md_to_html(result['report'])

    # build sources list — just links, keep it simple
    sources_html = ''
    for s in result['sources']:
        url   = s.get('url', '')
        title = s.get('title', '') or url
        sources_html += '<li><a href="' + url + '" target="_blank">' + title + '</a></li>\n'

    # images — just drop them in a div, nothing fancy
    images_html = ''
    if result.get('images'):
        for img in result['images']:
            images_html += '<img src="' + img + '" style="max-width:200px; margin:4px;" onerror="this.style.display=\'none\'">\n'
        images_html = '<div style="margin: 16px 0;">' + images_html + '</div>'

    template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Research Report</title>
    <style>
        body {{
            font-family: Georgia, serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 0 20px;
            color: #222;
            line-height: 1.7;
        }}
        h1, h2, h3 {{ font-family: Arial, sans-serif; }}
        h2 {{ border-bottom: 1px solid #ddd; padding-bottom: 4px; }}
        .meta {{ color: #888; font-size: 0.85rem; margin-bottom: 24px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 5px; }}
        a {{ color: #1a5276; }}
        .sources ul {{ list-style: disc; }}
    </style>
</head>
<body>
    <h1>Research Report</h1>
    <div class="meta">
        Run: {run_id} &nbsp;|&nbsp; {elapsed}s &nbsp;|&nbsp; {tokens} tokens &nbsp;|&nbsp; quality score: {score:.2f}
    </div>
    <p><strong>Goal:</strong> {goal}</p>

    {images_html}

    <div class="report">
        {report_html}
    </div>

    <div class="sources">
        <h2>Sources</h2>
        <ul>
            {sources_html}
        </ul>
    </div>
</body>
</html>'''

    html = template.format(
        run_id=run_id,
        elapsed=elapsed,
        tokens=tokens,
        score=score,
        goal=goal,
        images_html=images_html,
        report_html=report_html,
        sources_html=sources_html,
    )

    path = report_dir / ('run_' + run_id + '.html')
    with open(path, 'w') as f:
        f.write(html)

    return str(path)
