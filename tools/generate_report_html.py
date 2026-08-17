#!/usr/bin/env python3
"""Generate a styled HTML report from REPORT.md using the same CSS as the original."""
import re
import markdown

REPORT_PATH = "../REPORT.md"
OUTPUT_PATH = "../report.html"

CSS = """
:root { color-scheme: dark; --ground: #0b0b0d; --surface: #131317; --surface-2: #1a1a20; --code-bg: #08080a; --border: #26262d; --border-soft: #1c1c22; --text: #e8e6e0; --text-dim: #8f8f97; --text-dimmer: #55555c; --accent: #ef2c4a; --accent-soft: rgba(239,44,74,0.12); --accent-line: rgba(239,44,74,0.35); --amber: #f5a524; --code-text: #d4d8d0; --mono: "SF Mono", ui-monospace, "Menlo", "Cascadia Code", "Consolas", monospace; --sans: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", "Helvetica Neue", system-ui, sans-serif; }
* { box-sizing: border-box; }
html,body { margin:0; padding:0; background:var(--ground); color:var(--text); font-family:var(--sans); font-size:15px; line-height:1.55; -webkit-font-smoothing:antialiased; font-variant-numeric:tabular-nums; }
.wrap { display:grid; grid-template-columns:minmax(0,1fr); max-width:1180px; margin:0 auto; padding:48px 32px 96px; gap:40px; }
@media (min-width:1000px) { .wrap { grid-template-columns:minmax(0,1fr) 220px; gap:56px; padding:56px 40px 120px; } }
.hero { border:1px solid var(--border); background:var(--surface); padding:32px 32px 28px; position:relative; }
.hero::before { content:""; position:absolute; top:0; left:0; right:0; height:2px; background:linear-gradient(90deg,var(--accent) 0%,var(--accent) 20%,transparent 60%); }
.hero-tag { font-family:var(--mono); font-size:11px; letter-spacing:0.18em; text-transform:uppercase; color:var(--text-dim); margin:0 0 10px; }
.hero-tag em { color:var(--accent); font-style:normal; }
.hero h1 { font-family:var(--mono); font-weight:600; font-size:clamp(26px,4vw,38px); line-height:1.15; margin:0 0 8px; letter-spacing:-0.005em; text-wrap:balance; }
.hero-sub { color:var(--text-dim); font-size:16px; margin:0 0 24px; max-width:60ch; }
.chip { display:grid; grid-template-columns:max-content 1fr; gap:4px 24px; font-family:var(--mono); font-size:12.5px; border-top:1px dashed var(--border); padding-top:20px; }
.chip dt { color:var(--text-dimmer); letter-spacing:0.1em; text-transform:uppercase; font-size:11px; align-self:baseline; }
.chip dd { margin:0; color:var(--text); }
.chip dd code { background:transparent; padding:0; color:var(--accent); }
aside.toc { order:2; }
@media (min-width:1000px) { aside.toc { position:sticky; top:32px; align-self:start; max-height:calc(100vh - 64px); overflow-y:auto; padding-right:6px; } }
.toc-label { font-family:var(--mono); font-size:10.5px; letter-spacing:0.22em; text-transform:uppercase; color:var(--text-dimmer); padding:0 4px 8px; border-bottom:1px solid var(--border-soft); margin-bottom:6px; }
.toc a { display:flex; gap:12px; align-items:baseline; padding:5px 4px; color:var(--text-dim); text-decoration:none; font-size:12.5px; line-height:1.35; border-left:1px solid transparent; padding-left:8px; margin-left:-8px; transition:color 120ms,border-color 120ms; }
.toc a:hover { color:var(--text); border-left-color:var(--accent); }
.toc-num { font-family:var(--mono); font-size:10.5px; color:var(--text-dimmer); min-width:34px; flex-shrink:0; }
.toc-title { flex:1; }
main { order:1; min-width:0; }
.section { padding:32px 0 0; margin-top:8px; scroll-margin-top:16px; }
.section + .section { border-top:1px solid var(--border-soft); padding-top:44px; margin-top:40px; }
.sec-head { display:flex; gap:20px; align-items:baseline; margin:0 0 20px; }
.sec-num { font-family:var(--mono); font-size:11.5px; letter-spacing:0.12em; color:var(--accent); padding:3px 8px; border:1px solid var(--accent-line); background:var(--accent-soft); flex-shrink:0; align-self:center; font-weight:500; }
.section h2 { font-family:var(--mono); font-weight:600; font-size:22px; margin:0; color:var(--text); text-wrap:balance; letter-spacing:-0.005em; }
.section h3 { font-family:var(--mono); font-weight:600; font-size:14px; letter-spacing:0.02em; color:var(--amber); margin:28px 0 10px; text-transform:none; }
.section p { margin:12px 0; max-width:72ch; }
.section a { color:var(--text); text-decoration:underline; text-decoration-color:var(--accent-line); text-underline-offset:2px; }
.section a:hover { text-decoration-color:var(--accent); }
.section ul,.section ol { margin:12px 0; padding-left:20px; max-width:72ch; }
.section li { margin:6px 0; padding-left:4px; }
.section li::marker { color:var(--text-dimmer); }
code { font-family:var(--mono); font-size:0.9em; background:var(--surface-2); padding:1px 5px; border-radius:2px; color:var(--text); border:1px solid var(--border-soft); }
strong code { color:var(--amber); }
pre.code { background:var(--code-bg); border:1px solid var(--border); padding:16px 20px; margin:18px 0; overflow-x:auto; position:relative; font-size:12.5px; line-height:1.55; }
pre.code::before { content:""; position:absolute; top:0; left:0; right:0; height:1px; background:linear-gradient(90deg,var(--accent-line) 0%,transparent 40%); }
pre.code code { background:transparent; border:none; padding:0; color:var(--code-text); font-size:inherit; white-space:pre; }
pre.code[data-lang]::after { content:attr(data-lang); position:absolute; top:6px; right:10px; font-family:var(--mono); font-size:9.5px; letter-spacing:0.15em; text-transform:uppercase; color:var(--text-dimmer); }
.table-wrap { overflow-x:auto; margin:18px 0; border:1px solid var(--border); }
table { width:100%; border-collapse:collapse; font-size:13px; background:var(--surface); font-variant-numeric:tabular-nums; }
th { text-align:left; padding:10px 14px; font-family:var(--mono); font-weight:600; font-size:10.5px; letter-spacing:0.14em; text-transform:uppercase; color:var(--text-dim); border-bottom:1px solid var(--border); background:var(--surface-2); white-space:nowrap; }
td { padding:10px 14px; border-bottom:1px solid var(--border-soft); color:var(--text); vertical-align:top; }
tr:last-child td { border-bottom:none; }
tr:hover td { background:rgba(255,255,255,0.02); }
td code { background:rgba(0,0,0,0.35); border-color:rgba(255,255,255,0.05); color:var(--code-text); font-size:12px; }
footer.foot { margin-top:72px; padding-top:24px; border-top:1px solid var(--border-soft); color:var(--text-dimmer); font-family:var(--mono); font-size:11.5px; letter-spacing:0.06em; display:flex; justify-content:space-between; flex-wrap:wrap; gap:16px; }
footer.foot .mark { color:var(--accent); }
::selection { background:var(--accent); color:var(--ground); }
::-webkit-scrollbar { width:10px; height:10px; }
::-webkit-scrollbar-track { background:var(--ground); }
::-webkit-scrollbar-thumb { background:var(--border); }
::-webkit-scrollbar-thumb:hover { background:var(--text-dimmer); }
"""

def slugify(text):
    """Generate a URL-safe slug from heading text."""
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[\s_-]+', '-', text.strip())
    return text

def parse_report(md_text):
    """Parse REPORT.md into hero metadata, TOC entries, and section HTML."""
    lines = md_text.split('\n')

    # Extract hero metadata from the header section
    hero_title = "RPG69 — Roland MC-101 Firmware Analysis"
    hero_sub = "Structural analysis of Roland's Zen-Core groovebox firmware. Encryption analysis of the encrypted main app, full decode of the inter-core UMDW protocol, parameter address model, wave-ROM directory, boot loader, and factory test-mode dispatch. Cross-verified against MC-707 v1.82 — <strong>same encryption key confirmed</strong>, 26 non-code files byte-identical between the two products."

    # Find all ## headings for TOC and section splitting
    sections = []
    current_section_lines = []
    current_h2 = None
    current_h2_num = None

    in_code_block = False

    for line in lines:
        # Track code blocks
        if line.strip().startswith('```'):
            in_code_block = not in_code_block

        if not in_code_block and line.startswith('## ') and not line.startswith('### '):
            # Save previous section
            if current_h2 is not None:
                sections.append((current_h2_num, current_h2, '\n'.join(current_section_lines)))
            # Start new section
            heading_text = line[3:].strip()
            # Extract section number if present (e.g., "1. File layout" → "1", "File layout")
            match = re.match(r'^(\d+)\.\s+(.*)', heading_text)
            if match:
                num = int(match.group(1))
                title = match.group(2)
                # Use hex numbering like the original (0x00, 0x01, ...)
                h2_num = f"0x{num-1:02X}"
            else:
                h2_num = ""
                title = heading_text
            current_h2 = title
            current_h2_num = h2_num
            current_section_lines = []
        elif current_h2 is not None:
            current_section_lines.append(line)

    # Don't forget the last section
    if current_h2 is not None:
        sections.append((current_h2_num, current_h2, '\n'.join(current_section_lines)))

    return hero_title, hero_sub, sections

def md_to_html(md_text):
    """Convert markdown to HTML with extensions."""
    return markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'codehilite', 'toc'])

def build_section_html(num, title, body_md):
    """Build a styled section with the sec-num badge."""
    slug = slugify(title)
    body_html = markdown.markdown(body_md, extensions=['tables', 'fenced_code'])

    # Wrap tables in .table-wrap divs
    body_html = re.sub(r'(<table)', '<div class="table-wrap">\\1', body_html)
    body_html = re.sub(r'(</table>)', '\\1</div>', body_html)

    # Add data-lang to code blocks
    body_html = re.sub(r'<pre><code', '<pre class="code"><code', body_html)
    body_html = re.sub(r'</code></pre>', '</code></pre>', body_html)

    sec_num_html = f'<span class="sec-num">{num}</span>' if num else ''

    return f'''<section class="section" id="{slug}"><header class="sec-head">{sec_num_html}<h2>{title}</h2></header>

{body_html}

</section>'''

def build_toc(sections):
    """Build the TOC sidebar."""
    toc_entries = []
    for num, title, _ in sections:
        slug = slugify(title)
        toc_entries.append(f'<a href="#{slug}"><span class="toc-num">{num}</span><span class="toc-title">{title}</span></a>')
    return '\n'.join(toc_entries)

def main():
    with open(REPORT_PATH, 'r') as f:
        md_text = f.read()

    hero_title, hero_sub, sections = parse_report(md_text)

    sections_html = '\n\n'.join(build_section_html(num, title, body) for num, title, body in sections)
    toc_html = build_toc(sections)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MC-101 Firmware Analysis</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="wrap">
  <main>
    <header class="hero">
      <p class="hero-tag">Firmware analysis &middot; <em>Roland MC-101 + MC-707</em> &middot; v1.82</p>
      <h1>{hero_title}</h1>
      <p class="hero-sub">{hero_sub}</p>
      <dl class="chip">
        <dt>File</dt>       <dd><code>MC101_UPA_up.bin</code> &middot; 20,285,440 bytes &middot; GNU tar</dd>
        <dt>Codename</dt>   <dd><code>RPG69</code> (MC-101) &middot; <code>RPG68</code> (MC-707) &middot; Zen-Core &middot; HW SKU <code>KY022</code></dd>
        <dt>SoC family</dt> <dd><code>Roland BMC</code> &middot; Cortex-M4/M7 &middot; panel via STM32G0 @115.2k UART/MIDI</dd>
        <dt>MIDI ID</dt>    <dd><code>0x5E</code> (MC-101) &middot; <code>0x5D</code> (MC-707) &middot; manufacturer <code>0x41</code></dd>
        <dt>Build</dt>      <dd><code>2023-05-17 22:54:58</code></dd>
      </dl>
    </header>
{sections_html}
    <footer class="foot">
      <span>Generated from <code>REPORT.md</code> &middot; <span class="mark">MC-101 SysEx &amp; Protocol Analysis</span></span>
      <span>EU Directive 2009/24/EC &middot; interoperability research</span>
    </footer>
  </main>
  <aside class="toc">
    <div class="toc-label">Contents</div>
{toc_html}
  </aside>
</div>
</body>
</html>
'''

    with open(OUTPUT_PATH, 'w') as f:
        f.write(html)
    print(f"Written {OUTPUT_PATH} ({len(html)} bytes)")

if __name__ == '__main__':
    main()
