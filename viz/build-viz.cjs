#!/usr/bin/env node
/*
 * build-viz.cjs — the deterministic renderer for the Visual Comprehension Layer.
 *
 * The thinking (what the boxes are, the labels, the narrative, the self-check) is done by
 * Claude in the command. This script does only the MECHANICAL, repeatable part so output is
 * consistent and never hand-assembled:
 *   1. compile the Map's D2 source -> SVG (offline, via the `d2` binary)
 *   2. inject the VIZ payload into viz/template.html at <!--VIZ_CONTENT-->  -> <name>.viz.html
 *   3. write a human-diffable <name>.viz.md (the source of truth)
 *
 * Because the SVG is embedded, every .viz.html is already fully self-contained and portable
 * (no mermaid.min.js, no vendor file, no network) — so --inline is the default behaviour and
 * the flag is accepted as a no-op for compatibility with the documented interface.
 *
 * Usage:
 *   node viz/build-viz.cjs --payload <payload.json> --name <map|changes|plan> [--outdir viz/output] [--inline]
 *
 * payload.json shape (see viz/VISUAL-STYLE.md §6), PLUS a `mapD2` string holding the Map's D2
 * source. The script compiles mapD2 -> SVG and sets payload.mapSVG before injecting. If mapD2
 * is absent but mapSVG is present, the SVG is used as-is.
 */
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const os = require('os');

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  if (i === -1) return def;
  const v = process.argv[i + 1];
  return (v && !v.startsWith('--')) ? v : true;
}

const VIZ_DIR = path.resolve(__dirname);            // the viz/ root (this file lives there)
const TEMPLATE = path.join(VIZ_DIR, 'template.html');
const SENTINEL = '<!--VIZ_CONTENT-->';
const ALLOWED = new Set(['map', 'changes', 'plan']);

function resolveD2() {
  const candidates = ['d2', path.join(os.homedir(), '.local/bin/d2'), '/opt/homebrew/bin/d2', '/usr/local/bin/d2'];
  for (const c of candidates) {
    try { execFileSync(c, ['--version'], { stdio: 'ignore' }); return c; } catch (_) {}
  }
  return null;
}

function compileD2(d2bin, d2src) {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'viz-d2-'));
  const inF = path.join(tmp, 'map.d2'), outF = path.join(tmp, 'map.svg');
  fs.writeFileSync(inF, d2src);
  execFileSync(d2bin, ['--theme', '0', '--pad', '24', inF, outF], { stdio: 'pipe' });
  const svg = fs.readFileSync(outF, 'utf8');
  fs.rmSync(tmp, { recursive: true, force: true });
  return svg;
}

function vizToMarkdown(v) {
  const L = [];
  L.push(`# ${v.title || 'Visualization'} — ${v.scope || 'visualization'}`, '');
  if (v.breadcrumb) L.push(`> ${v.breadcrumb.join(' › ')}`, '');
  L.push('## The Map (D2 source)', '', '```d2', (v.mapD2 || '(SVG supplied directly)').trim(), '```', '');
  if (v.mapNodes) { L.push('Pieces:', ''); v.mapNodes.forEach(n => L.push(`- **${n.label}** (${n.role}${n.here ? ', ← you are here' : ''}) — \`${n.sub || ''}\` — ${n.explain || ''}`)); L.push(''); }
  if (v.flow) { L.push('## The Journey', '', v.flow.map(x => x.arrow ? `→ *(${x.arrow})*` : `**${x.label}**`).join(' '), ''); }
  if (v.shape) { L.push('## The Shape', ''); v.shape.forEach(x => L.push(x.t ? `↓ *${x.t}*` : `- ${x.lbl}: \`${x.code}\``)); L.push(''); }
  if (v.steps) { L.push('## The Steps', ''); v.steps.forEach((x, i) => L.push(`${i + 1}. **${x.who}** → ${x.what}`)); L.push(''); }
  if (v.narr) { L.push('## In plain words', ''); ['map','flow','shape','steps'].forEach(k => v.narr[k] && L.push(`**${k}:** ${v.narr[k].replace(/<\/?b>/g, '')}`, '')); }
  if (v.uncertain && v.uncertain.length) { L.push('## ⚠ Not fully sure', ''); v.uncertain.forEach(u => L.push(`- ${u}`)); L.push(''); }
  if (v.footer) L.push('---', '', `*${v.footer}*`);
  return L.join('\n');
}

function main() {
  const name = arg('name');
  const payloadPath = arg('payload');
  const outdir = path.resolve(arg('outdir', path.join(VIZ_DIR, 'output')));
  if (!name || !ALLOWED.has(name)) { console.error('ERROR: --name must be one of map|changes|plan'); process.exit(2); }
  if (!payloadPath || payloadPath === true) { console.error('ERROR: --payload <file.json> required'); process.exit(2); }
  if (!fs.existsSync(TEMPLATE)) { console.error('ERROR: template not found at ' + TEMPLATE); process.exit(2); }

  let v;
  try { v = JSON.parse(fs.readFileSync(payloadPath, 'utf8')); }
  catch (e) { console.error('ERROR: cannot parse payload JSON: ' + e.message); process.exit(2); }

  // no-code-skip: command sets status:"empty" -> we still write a viewer that shows the empty state,
  // but the command itself decides whether to call us at all. Here we honor an explicit skip.
  if (v.skip) { console.log('SKIP: ' + (v.skipReason || 'no code changes — nothing to visualize')); process.exit(0); }

  // compile the Map
  if (v.mapD2 && !v.mapSVG) {
    const d2 = resolveD2();
    if (!d2) { console.error('ERROR: d2 not found on PATH or ~/.local/bin. Install d2, or supply mapSVG directly.'); process.exit(3); }
    try { v.mapSVG = compileD2(d2, v.mapD2); }
    catch (e) {
      // CQ4/T8: a label broke the render. Produce an error-state viewer rather than a blank/no file.
      v.status = 'error';
      v.error = 'The map could not be drawn (a label may contain characters that broke the diagram). ' +
                'Check quoting/escaping per VISUAL-STYLE.md §4. Details: ' + (e.stderr ? e.stderr.toString().slice(0, 300) : e.message);
    }
  }

  fs.mkdirSync(outdir, { recursive: true });
  const tmpl = fs.readFileSync(TEMPLATE, 'utf8');
  // Inject the payload as an inline <script>. Two safeguards (both load-bearing):
  //   1. Escape every "<" to < so a literal "</script>" inside any payload string
  //      (labels, narrative, code samples, or d2's echoed error text) cannot break out of
  //      the data <script> and corrupt window.VIZ. (< re-parses to "<" in the JSON string.)
  //   2. Use a FUNCTION replacer so "$&", "$`", "$'", "$$" sequences in the JSON are inserted
  //      literally instead of being expanded as String.prototype.replace special patterns.
  const dataTag = '<script>window.VIZ=' + JSON.stringify(v).replace(/</g, '\\u003c') + ';<\/script>';
  const html = tmpl.replace(SENTINEL, () => dataTag);
  const htmlPath = path.join(outdir, `${name}.viz.html`);
  const mdPath = path.join(outdir, `${name}.viz.md`);
  fs.writeFileSync(htmlPath, html);
  fs.writeFileSync(mdPath, vizToMarkdown(v));

  // Decision 7: output capped at 6 files (3 commands x 2). Warn if exceeded (stale files).
  const extra = fs.readdirSync(outdir).filter(f => f.endsWith('.viz.md') || f.endsWith('.viz.html'));
  const note = extra.length > 6 ? `  (note: ${extra.length} files in output/ — expected ≤6; remove stale ones)` : '';

  console.log('WROTE ' + mdPath);
  console.log('WROTE ' + htmlPath + (v.status === 'error' ? '  [ERROR STATE — render failed, see viewer]' : '') + note);
  console.log('OPEN  file://' + htmlPath);
}
main();
