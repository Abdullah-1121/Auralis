"""
Single-file product dashboard served at GET /ui.

Design system (via ui-ux-pro-max): "Data-Dense Dashboard" — professional
light theme, navy primary #0F172A, blue CTA #0369A1, Fira Sans / Fira Code,
KPI stat cards, compact spacing, SVG icons only, WCAG AA contrast,
focus-visible rings, prefers-reduced-motion respected.

Still dependency-free at runtime: one HTML string, no build step, no JS
frameworks. The only external fetch is Google Fonts (display=swap).
"""

UI_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Auralis — Post-Call Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Fira+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --primary: #0F172A; --on-primary: #FFFFFF;
    --secondary: #334155; --accent: #0369A1; --accent-hover: #075985;
    --bg: #F8FAFC; --surface: #FFFFFF; --fg: #020617;
    --muted-bg: #E8ECF1; --border: #E2E8F0;
    --text-muted: #475569; --text-faint: #64748B;
    --ok: #047857; --ok-bg: #ECFDF5; --ok-border: #A7F3D0;
    --warn: #B45309; --warn-bg: #FFFBEB; --warn-border: #FDE68A;
    --bad: #B91C1C; --bad-bg: #FEF2F2; --bad-border: #FECACA;
    --accent-bg: #F0F9FF; --accent-border: #BAE6FD;
    --radius: 8px;
    --mono: "Fira Code", ui-monospace, SFMono-Regular, Consolas, monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }
  body {
    background: var(--bg); color: var(--fg);
    font: 14px/1.55 "Fira Sans", ui-sans-serif, system-ui, "Segoe UI", sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  button { cursor: pointer; font: inherit; }
  :focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 4px; }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
  }
  svg.ic { width: 16px; height: 16px; flex: none; stroke: currentColor; fill: none;
           stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }

  .app { display: grid; grid-template-columns: 260px 1fr; height: 100vh; }
  @media (max-width: 860px) { .app { grid-template-columns: 1fr; } .sidebar { display: none; } }

  /* ── Sidebar ─────────────────────────────────────────────── */
  .sidebar { background: var(--surface); border-right: 1px solid var(--border); display: flex; flex-direction: column; overflow: hidden; }
  .brand { display: flex; align-items: center; gap: 10px; padding: 16px 16px 12px; }
  .brand .mark {
    width: 30px; height: 30px; border-radius: 7px; flex: none; background: var(--primary);
    color: var(--on-primary); display: grid; place-items: center; font-weight: 700; font-size: 14px;
  }
  .brand .name { font-weight: 700; font-size: 15px; letter-spacing: -.01em; color: var(--primary); }
  .brand .tag { font-size: 11px; color: var(--text-faint); display: block; margin-top: -2px; }
  .new-call {
    margin: 4px 12px 12px; padding: 9px 14px; border-radius: var(--radius); border: 0;
    background: var(--accent); color: #fff; font-weight: 600; font-size: 13.5px;
    display: flex; align-items: center; justify-content: center; gap: 7px; transition: background .15s;
  }
  .new-call:hover { background: var(--accent-hover); }
  .side-label { padding: 6px 16px; font-size: 11px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--text-faint); }
  .call-list { overflow-y: auto; flex: 1; padding: 0 8px 14px; }
  .call-item {
    width: 100%; text-align: left; background: none; border: 0; border-left: 2px solid transparent;
    display: flex; align-items: center; gap: 9px; padding: 8px 10px; border-radius: 6px;
    transition: background .15s;
  }
  .call-item:hover { background: var(--bg); }
  .call-item.selected { background: var(--accent-bg); border-left-color: var(--accent); }
  .call-item .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
  .dot.done { background: #10B981; } .dot.failed { background: #EF4444; }
  .dot.working { background: var(--accent); animation: pulse 1s infinite alternate; }
  .call-item .who { min-width: 0; }
  .call-item .who b { display: block; font-size: 13px; font-weight: 600; color: var(--fg);
                      white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .call-item .who span { font-size: 11px; color: var(--text-faint); font-family: var(--mono); }
  .side-empty { padding: 10px 16px; color: var(--text-faint); font-size: 12.5px; line-height: 1.5; }

  /* ── Main ────────────────────────────────────────────────── */
  .main { overflow-y: auto; }
  .main-inner { max-width: 1060px; margin: 0 auto; padding: 22px 24px 80px; }
  .view { display: none; } .view.active { display: block; }
  h1.page { font-size: 19px; font-weight: 700; letter-spacing: -.01em; color: var(--primary); margin-bottom: 3px; }
  p.sub { color: var(--text-muted); margin-bottom: 18px; font-size: 13.5px; max-width: 68ch; }

  .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; margin-bottom: 12px; }
  .card h2 { font-size: 12px; font-weight: 600; letter-spacing: .07em; text-transform: uppercase; color: var(--text-faint); margin-bottom: 12px; display: flex; align-items: center; gap: 7px; }

  /* Form */
  .frow { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
  @media (max-width: 640px) { .frow { grid-template-columns: 1fr; } }
  label { display: block; font-size: 12px; color: var(--secondary); margin-bottom: 4px; font-weight: 500; }
  input, textarea {
    width: 100%; background: var(--surface); color: var(--fg); border: 1px solid var(--border);
    border-radius: 6px; padding: 8px 11px; font: inherit; font-size: 14px; transition: border-color .15s, box-shadow .15s;
  }
  @media (max-width: 640px) { input, textarea { font-size: 16px; } } /* avoid iOS zoom */
  input:focus, textarea:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(3,105,161,.12); }
  textarea { min-height: 200px; resize: vertical; line-height: 1.6; }
  .form-actions { display: flex; gap: 10px; align-items: center; margin-top: 14px; flex-wrap: wrap; }
  .btn { padding: 9px 18px; border-radius: 6px; border: 0; font-weight: 600; font-size: 13.5px;
         display: inline-flex; align-items: center; gap: 7px; transition: background .15s, border-color .15s; }
  .btn.primary { background: var(--accent); color: #fff; }
  .btn.primary:hover { background: var(--accent-hover); }
  .btn.ghost { background: var(--surface); color: var(--secondary); border: 1px solid var(--border); }
  .btn.ghost:hover { border-color: var(--text-faint); }
  .btn:disabled { opacity: .5; cursor: default; }
  .form-note { font-size: 12.5px; color: var(--bad); }

  /* Detail header */
  .detail-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; margin-bottom: 14px; flex-wrap: wrap; }
  .detail-head h1 { font-size: 18px; font-weight: 700; color: var(--primary); }
  .detail-head p { color: var(--text-muted); font-size: 12.5px; }
  .detail-head p .cid { font-family: var(--mono); font-size: 11.5px; color: var(--text-faint); }

  .badge { font-size: 11.5px; font-weight: 600; padding: 3px 10px; border-radius: 999px;
           border: 1px solid var(--border); color: var(--secondary); background: var(--surface);
           display: inline-flex; align-items: center; gap: 5px; }
  .badge svg.ic { width: 12px; height: 12px; }
  .badge.ok { color: var(--ok); border-color: var(--ok-border); background: var(--ok-bg); }
  .badge.warn { color: var(--warn); border-color: var(--warn-border); background: var(--warn-bg); }
  .badge.bad { color: var(--bad); border-color: var(--bad-border); background: var(--bad-bg); }
  .badge.accent { color: var(--accent); border-color: var(--accent-border); background: var(--accent-bg); }

  /* KPI stat cards */
  .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 12px; }
  @media (max-width: 720px) { .kpis { grid-template-columns: repeat(2, 1fr); } }
  .kpi { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 12px 14px; }
  .kpi .k-label { font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--text-faint); margin-bottom: 4px; }
  .kpi .k-value { font-family: var(--mono); font-size: 20px; font-weight: 600; color: var(--primary); font-variant-numeric: tabular-nums; }
  .kpi .k-value small { font-size: 12px; color: var(--text-faint); font-weight: 400; }
  .kpi .k-sub { font-size: 11.5px; color: var(--text-muted); margin-top: 2px; }
  .kpi.tone-ok .k-value { color: var(--ok); } .kpi.tone-warn .k-value { color: var(--warn); } .kpi.tone-bad .k-value { color: var(--bad); }

  /* Step tracker */
  .tracker { display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; }
  @media (max-width: 720px) { .tracker { grid-template-columns: repeat(3, 1fr); } }
  .step { text-align: center; padding: 10px 4px 8px; border-radius: 6px; background: var(--bg); border: 1px solid var(--border); }
  .step .ic-wrap { width: 24px; height: 24px; margin: 0 auto 6px; border-radius: 50%; display: grid; place-items: center;
    background: var(--surface); color: var(--text-faint); font-size: 11.5px; font-weight: 600;
    font-family: var(--mono); border: 1px solid var(--border); transition: all .2s; }
  .step .nm { font-size: 11px; color: var(--text-faint); line-height: 1.3; }
  .step.done { background: var(--surface); }
  .step.done .ic-wrap { background: var(--ok-bg); border-color: var(--ok-border); color: var(--ok); }
  .step.done .nm { color: var(--secondary); }
  .step.active { border-color: var(--accent-border); background: var(--accent-bg); }
  .step.active .ic-wrap { border-color: var(--accent); color: var(--accent); animation: pulse .9s infinite alternate; }
  .step.active .nm { color: var(--accent); font-weight: 600; }
  .step.failed { background: var(--bad-bg); border-color: var(--bad-border); }
  .step.failed .ic-wrap { background: var(--surface); border-color: var(--bad); color: var(--bad); }
  .step.failed .nm { color: var(--bad); font-weight: 600; }
  @keyframes pulse { from { opacity: .45 } to { opacity: 1 } }
  .fail-banner { margin-top: 12px; padding: 11px 13px; border-radius: 6px; font-size: 13px;
    background: var(--bad-bg); border: 1px solid var(--bad-border); color: var(--bad); }

  /* Results */
  .results-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: start; }
  @media (max-width: 860px) { .results-grid { grid-template-columns: 1fr; } }
  .col { min-width: 0; }
  .summary-text { font-size: 13.5px; color: var(--fg); max-width: 75ch; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
  .chip { background: var(--bg); border: 1px solid var(--border); border-radius: 999px; padding: 2px 10px; font-size: 12px; color: var(--text-muted); }
  .chip b { color: var(--fg); font-weight: 600; }

  /* Grounding */
  .g-list { display: flex; flex-direction: column; max-height: 430px; overflow-y: auto; border: 1px solid var(--border); border-radius: 6px; }
  .g-row { display: flex; gap: 9px; padding: 9px 11px; border-bottom: 1px solid var(--border); transition: background .15s; }
  .g-row:last-child { border-bottom: 0; }
  .g-row:hover { background: var(--bg); }
  .g-row .g-icon { margin-top: 2px; color: var(--ok); }
  .g-row.flagged .g-icon { color: var(--bad); }
  .g-row .cl { font-size: 13px; min-width: 0; }
  .g-row .fld { font-family: var(--mono); color: var(--accent); font-size: 10.5px; font-weight: 600;
                text-transform: uppercase; letter-spacing: .04em; display: block; margin-bottom: 1px; }
  .g-row .ev { display: block; margin-top: 2px; font-size: 12px; color: var(--text-faint); font-style: italic; }
  .g-row.flagged { background: var(--bad-bg); }
  .g-row.flagged .ev { color: var(--bad); font-style: normal; }

  /* Scorecard */
  .score-top { display: flex; align-items: center; gap: 18px; margin-bottom: 10px; }
  .gauge { position: relative; width: 88px; height: 88px; flex: none; }
  .gauge svg.g { transform: rotate(-90deg); }
  .gauge .val { position: absolute; inset: 0; display: grid; place-items: center;
    font-family: var(--mono); font-size: 24px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .gauge .val small { font-size: 10.5px; color: var(--text-faint); font-weight: 400; display: block; text-align: center; }
  .dims { flex: 1; min-width: 0; }
  .dim { margin-bottom: 9px; }
  .dim .top { display: flex; justify-content: space-between; font-size: 12.5px; margin-bottom: 3px; }
  .dim .top b { font-weight: 600; color: var(--fg); }
  .dim .top span { color: var(--text-muted); font-family: var(--mono); font-size: 12px; }
  .dim .bar { height: 5px; border-radius: 3px; background: var(--muted-bg); overflow: hidden; }
  .dim .bar i { display: block; height: 100%; border-radius: 3px; background: var(--accent); transition: width .4s ease; }
  .dim .cm { font-size: 11.5px; color: var(--text-faint); margin-top: 3px; }
  details.coach { margin-top: 4px; }
  details.coach summary { font-size: 13px; color: var(--accent); font-weight: 600; cursor: pointer; }
  details.coach summary:hover { color: var(--accent-hover); }
  details.coach h4 { font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--text-faint); margin: 11px 0 5px; }
  details.coach ul { padding-left: 17px; }
  details.coach li { font-size: 12.5px; color: var(--text-muted); margin: 3px 0; }

  /* Email */
  .email-meta { display: flex; flex-direction: column; gap: 2px; font-size: 12.5px; color: var(--text-muted);
    padding-bottom: 10px; border-bottom: 1px solid var(--border); margin-bottom: 10px; }
  .email-meta b { color: var(--fg); font-weight: 600; }
  .email-subject { font-size: 14.5px; font-weight: 700; color: var(--primary); margin-bottom: 8px; }
  .email-body { font-size: 13px; color: var(--secondary); white-space: pre-wrap; line-height: 1.65; max-width: 75ch; }
  .email-actions { display: flex; align-items: center; gap: 12px; margin-top: 14px; flex-wrap: wrap; }
  .send-note { font-size: 12.5px; color: var(--text-faint); }

  .empty { padding: 18px; text-align: center; color: var(--text-faint); font-size: 13px;
    border: 1px dashed var(--border); border-radius: 6px; }
  .skel { border-radius: 6px; background: linear-gradient(90deg, var(--muted-bg) 25%, #F1F5F9 50%, var(--muted-bg) 75%);
    background-size: 200% 100%; animation: shimmer 1.4s infinite; }
  @keyframes shimmer { from { background-position: 200% 0 } to { background-position: -200% 0 } }

  .toast { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%) translateY(80px);
    background: var(--primary); color: var(--on-primary); border-radius: 8px; padding: 10px 17px;
    font-size: 13px; box-shadow: 0 8px 24px rgba(2,6,23,.25); transition: transform .22s ease; z-index: 50; max-width: 90vw; }
  .toast.show { transform: translateX(-50%) translateY(0); }
</style>
</head>
<body>
<!-- Inline SVG icon set (Lucide outlines) -->
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <defs>
    <symbol id="i-plus" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></symbol>
    <symbol id="i-check" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></symbol>
    <symbol id="i-x" viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></symbol>
    <symbol id="i-alert" viewBox="0 0 24 24"><path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4M12 17h.01"/></symbol>
    <symbol id="i-send" viewBox="0 0 24 24"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4Z"/></symbol>
    <symbol id="i-zap" viewBox="0 0 24 24"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8Z"/></symbol>
    <symbol id="i-mail" viewBox="0 0 24 24"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/></symbol>
    <symbol id="i-shield" viewBox="0 0 24 24"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1Z"/></symbol>
    <symbol id="i-gauge" viewBox="0 0 24 24"><path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/></symbol>
    <symbol id="i-doc" viewBox="0 0 24 24"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></symbol>
  </defs>
</svg>

<div class="app">
  <aside class="sidebar">
    <div class="brand">
      <div class="mark">A</div>
      <div><span class="name">Auralis</span><span class="tag">post-call intelligence</span></div>
    </div>
    <button class="new-call" id="nav-new"><svg class="ic"><use href="#i-plus"/></svg>Analyze a call</button>
    <div class="side-label">Recent calls</div>
    <div class="call-list" id="call-list"><div class="side-empty">No calls yet.<br>Analyze your first call to see it here.</div></div>
  </aside>

  <main class="main"><div class="main-inner">

    <!-- ── New call ─────────────────────────────────────────── -->
    <section class="view active" id="view-new">
      <h1 class="page">Analyze a sales call</h1>
      <p class="sub">Paste a transcript. Auralis summarizes it, extracts insights, <b>verifies every claim against the transcript</b>, scores the rep, and drafts a follow-up from verified facts only.</p>
      <div class="card">
        <h2><svg class="ic"><use href="#i-doc"/></svg>Customer</h2>
        <div class="frow">
          <div><label for="f-name">Name</label><input id="f-name" autocomplete="off" placeholder="Jordan Malik"></div>
          <div><label for="f-company">Company</label><input id="f-company" autocomplete="off" placeholder="BrightPath Logistics"></div>
        </div>
        <div class="frow">
          <div><label for="f-role">Role</label><input id="f-role" autocomplete="off" placeholder="Head of Sales"></div>
          <div><label for="f-email">Email</label><input id="f-email" type="email" autocomplete="off" placeholder="jordan@brightpath.io"></div>
        </div>
      </div>
      <div class="card">
        <h2><svg class="ic"><use href="#i-doc"/></svg>Transcript</h2>
        <label for="f-transcript" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">Transcript</label>
        <textarea id="f-transcript" placeholder="Rep: Hi, thanks for making time today...&#10;Customer: ..."></textarea>
        <div class="form-actions">
          <button class="btn primary" id="submit-btn"><svg class="ic"><use href="#i-zap"/></svg>Analyze call</button>
          <button class="btn ghost" id="sample-btn">Load sample</button>
          <span class="form-note" id="submit-note" role="alert"></span>
        </div>
      </div>
    </section>

    <!-- ── Call detail ──────────────────────────────────────── -->
    <section class="view" id="view-detail">
      <div class="detail-head">
        <div><h1 id="d-name">—</h1><p id="d-meta">—</p></div>
        <div style="display:flex;gap:7px;flex-wrap:wrap" id="d-badges"></div>
      </div>

      <div class="kpis" id="d-kpis" style="display:none"></div>

      <div class="card">
        <h2><svg class="ic"><use href="#i-gauge"/></svg>Pipeline</h2>
        <div class="tracker" id="tracker"></div>
        <div class="fail-banner" id="fail-banner" style="display:none"></div>
      </div>

      <div id="d-results" style="display:none">
        <div class="card">
          <h2><svg class="ic"><use href="#i-doc"/></svg>Summary</h2>
          <p class="summary-text" id="d-summary"></p>
          <div class="chips" id="d-chips"></div>
        </div>

        <div class="results-grid">
          <div class="col"><div class="card">
            <h2 style="justify-content:space-between"><span style="display:flex;align-items:center;gap:7px"><svg class="ic"><use href="#i-shield"/></svg>Grounding report</span><span class="badge" id="d-gconf">—</span></h2>
            <div class="g-list" id="d-grounding"></div>
          </div></div>
          <div class="col"><div class="card">
            <h2><svg class="ic"><use href="#i-gauge"/></svg>Call scorecard</h2>
            <div class="score-top">
              <div class="gauge" id="d-gauge" role="img" aria-label="Overall call score"></div>
              <div class="dims" id="d-dims"></div>
            </div>
            <details class="coach"><summary>Coaching notes</summary><div id="d-coach"></div></details>
          </div></div>
        </div>

        <div class="card">
          <h2><svg class="ic"><use href="#i-mail"/></svg>Follow-up email <span style="text-transform:none;letter-spacing:0;font-weight:400">— drafted from verified facts only</span></h2>
          <div id="d-email"></div>
          <div class="email-actions">
            <button class="btn primary" id="approve-btn" style="display:none"><svg class="ic"><use href="#i-send"/></svg>Approve &amp; send</button>
            <span class="badge" id="d-emailstatus" style="display:none"></span>
            <span class="send-note" id="approve-note"></span>
          </div>
        </div>
      </div>

      <div id="d-loading">
        <div class="card"><div class="skel" style="height:13px;width:60%"></div><div class="skel" style="height:13px;width:85%;margin-top:9px"></div><div class="skel" style="height:13px;width:40%;margin-top:9px"></div></div>
      </div>
    </section>

  </div></main>
</div>

<div class="toast" id="toast" role="status" aria-live="polite"></div>

<script>
const STEPS = [
  ["summarizing", "Summarize"],
  ["extracting_insights", "Extract insights"],
  ["verifying_insights", "Verify claims"],
  ["drafting_followup", "Draft follow-up"],
  ["scoring_call", "Score the call"],
  ["writing_crm", "CRM record"],
];
const SAMPLE = {
  name: "Jordan Malik", company: "BrightPath Logistics", role: "Head of Sales", email: "jordan@brightpath.io",
  transcript: `Rep: Hi Jordan, thanks for making time today. Before we dive in, can you walk me through how your team currently handles inbound leads?
Jordan: Sure. Honestly it's a mess. Leads come in through the website form and email, and they sit in a shared inbox. Sometimes nobody follows up for three or four days.
Rep: Got it - so follow-up speed is the main pain?
Jordan: That, and visibility. My two SDRs work out of spreadsheets. I have no idea who contacted whom. We lost a deal last month because two reps emailed the same prospect with different pricing.
Rep: Ouch. What tools are you using today besides the spreadsheets?
Jordan: Slack for everything internal, and we just started paying for HubSpot but nobody set it up properly.
Rep: Understood. If we automated lead capture into HubSpot and posted alerts to Slack, what would that be worth to you?
Jordan: A lot. But I'll be honest, we got burned before. We paid an agency $8k last year for an automation project that never worked. So I'm cautious.
Rep: That's fair. What would make you feel confident this time?
Jordan: Seeing it work on our actual pipeline before we commit long-term. And keeping the initial spend small - I have maybe $3k for a pilot this quarter.
Rep: We can do a two-week pilot inside that budget. Who else would need to sign off?
Jordan: Our CTO, Amir. He'll want to review anything that touches our customer data.
Rep: Makes sense. How about I send you a pilot proposal tomorrow, and we book a technical call with Amir for next week?
Jordan: Send the proposal first. If it looks good, I'll loop in Amir.
Rep: Deal. I'll have it in your inbox by tomorrow morning.`,
};

let currentCallId = null;
let eventSource = null;
const $ = (id) => document.getElementById(id);
function esc(s) { const d = document.createElement("div"); d.textContent = s ?? ""; return d.innerHTML; }
function icon(name) { return `<svg class="ic" aria-hidden="true"><use href="#i-${name}"/></svg>`; }
function toast(msg) {
  const t = $("toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 4000);
}
function show(view) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  $(view).classList.add("active");
}

/* ── Sidebar ──────────────────────────────────────────────── */
async function refreshList() {
  try {
    const calls = await (await fetch("/calls?limit=25")).json();
    const box = $("call-list");
    if (!calls.length) {
      box.innerHTML = '<div class="side-empty">No calls yet.<br>Analyze your first call to see it here.</div>';
      return;
    }
    box.innerHTML = calls.map(c => {
      const cls = c.status === "done" ? "done" : c.status === "failed" ? "failed" : "working";
      const when = new Date(c.created_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
      return `<button class="call-item ${c.call_id === currentCallId ? "selected" : ""}" data-id="${c.call_id}">
        <span class="dot ${cls}" aria-hidden="true"></span>
        <span class="who"><b>${esc(c.customer_name || "Unknown")}</b><span>${when} · ${esc(c.status.replaceAll("_", " "))}</span></span>
      </button>`;
    }).join("");
    box.querySelectorAll(".call-item").forEach(el =>
      el.addEventListener("click", () => openCall(el.dataset.id)));
  } catch { /* sidebar is cosmetic — never break the app over it */ }
}

/* ── Submit ───────────────────────────────────────────────── */
async function submitCall() {
  const btn = $("submit-btn");
  btn.disabled = true; $("submit-note").textContent = "";
  try {
    const body = {
      transcript: $("f-transcript").value,
      customer: { name: $("f-name").value, company: $("f-company").value, role: $("f-role").value, email: $("f-email").value },
    };
    const resp = await fetch("/calls", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!resp.ok) {
      const e = await resp.json().catch(() => ({}));
      throw new Error(typeof e.detail === "string" ? e.detail : "Transcript must be at least 20 characters.");
    }
    const data = await resp.json();
    openCall(data.call_id);
  } catch (err) {
    $("submit-note").textContent = err.message;
  } finally {
    btn.disabled = false;
  }
}

/* ── Call detail ──────────────────────────────────────────── */
function renderTracker(status, failedStep) {
  const idx = STEPS.findIndex(([k]) => k === status);
  const failIdx = STEPS.findIndex(([k]) => k === failedStep);
  $("tracker").innerHTML = STEPS.map(([key, name], i) => {
    let cls = "", inner = String(i + 1);
    if (status === "done") { cls = "done"; inner = icon("check"); }
    else if (status === "failed") {
      if (i === failIdx) { cls = "failed"; inner = icon("x"); }
      else if (failIdx > -1 && i < failIdx) { cls = "done"; inner = icon("check"); }
    }
    else if (i < idx) { cls = "done"; inner = icon("check"); }
    else if (i === idx) { cls = "active"; }
    return `<div class="step ${cls}"><div class="ic-wrap">${inner}</div><div class="nm">${name}</div></div>`;
  }).join("");
}

function openCall(callId) {
  currentCallId = callId;
  if (eventSource) { eventSource.close(); eventSource = null; }
  show("view-detail");
  $("d-results").style.display = "none";
  $("d-kpis").style.display = "none";
  $("d-loading").style.display = "block";
  $("fail-banner").style.display = "none";
  $("d-badges").innerHTML = "";
  history.replaceState(null, "", "/ui?call=" + callId);
  refreshList();

  fetch("/calls/" + callId).then(r => {
    if (!r.ok) throw new Error("Call not found");
    return r.json();
  }).then(c => {
    $("d-name").textContent = c.customer.name || "Unknown customer";
    $("d-meta").innerHTML = esc([c.customer.role, c.customer.company].filter(Boolean).join(" · ")) +
      ` &nbsp;<span class="cid">${esc(callId)}</span>`;
    renderTracker(c.status, c.failed_step);
    if (c.status === "done" || c.status === "failed") renderResults(c);
    else watchLive(callId);
  }).catch(() => { toast("Call " + callId + " not found."); show("view-new"); });
}

function watchLive(callId) {
  eventSource = new EventSource(`/calls/${callId}/events`);
  eventSource.onmessage = (ev) => {
    const st = JSON.parse(ev.data);
    renderTracker(st.status, st.failed_step);
    if (st.status === "done" || st.status === "failed") {
      eventSource.close(); eventSource = null;
      fetch("/calls/" + callId).then(r => r.json()).then(renderResults);
      refreshList();
    }
  };
}

function badge(text, cls, ic) { return `<span class="badge ${cls || ""}">${ic ? icon(ic) : ""}${esc(text)}</span>`; }

function renderResults(c) {
  $("d-loading").style.display = "none";
  renderTracker(c.status, c.failed_step);

  // Header badges
  const badges = [];
  if (c.insights) badges.push(badge("Sentiment: " + c.insights.sentiment,
    c.insights.sentiment === "positive" ? "ok" : c.insights.sentiment === "negative" ? "bad" : ""));
  if (c.insights && c.insights.sales_stage) badges.push(badge(c.insights.sales_stage, "accent"));
  $("d-badges").innerHTML = badges.join("");

  // KPI cards
  const kpis = [];
  if (c.scorecard) {
    const s = c.scorecard.overall_score;
    kpis.push({ label: "Call score", value: `${s}<small> / 10</small>`, sub: "sales-coach assessment",
                tone: s >= 7 ? "ok" : s >= 5 ? "warn" : "bad" });
  }
  if (c.grounding) {
    const total = c.grounding.checks.length;
    const flagged = c.grounding.checks.filter(x => !x.supported).length;
    kpis.push({ label: "Claims verified", value: `${total - flagged}<small> / ${total}</small>`,
                sub: flagged === 0 ? "all grounded in transcript" : `${flagged} flagged for review`,
                tone: flagged === 0 ? "ok" : "warn" });
    kpis.push({ label: "Confidence", value: esc(c.grounding.overall_confidence),
                sub: "grounding verifier", tone: c.grounding.overall_confidence === "high" ? "ok" : c.grounding.overall_confidence === "medium" ? "warn" : "bad" });
  }
  kpis.push({ label: "Delivery", value: c.followup_approved ? esc(c.email_status.replaceAll("_", " ")) : "pending",
              sub: c.followup_approved ? "email dispatch" : "awaiting approval",
              tone: c.email_status === "sent" ? "ok" : c.email_status === "failed" ? "bad" : "" });
  $("d-kpis").innerHTML = kpis.map(k =>
    `<div class="kpi tone-${k.tone || "none"}"><div class="k-label">${k.label}</div><div class="k-value">${k.value}</div><div class="k-sub">${k.sub}</div></div>`).join("");
  $("d-kpis").style.display = "grid";

  if (c.status === "failed") {
    $("fail-banner").style.display = "block";
    $("fail-banner").innerHTML = `<b>Failed at ${esc(c.failed_step)}.</b> ${esc(c.error || "")} — earlier steps' results are preserved below.`;
  }

  const any = c.summary || c.grounding || c.scorecard || c.followup;
  $("d-results").style.display = any ? "block" : "none";
  if (!any) return;

  // Summary + chips
  $("d-summary").textContent = c.summary ? c.summary.summary : "No summary produced.";
  const chips = [];
  if (c.insights) {
    c.insights.pain_points.slice(0, 4).forEach(p => chips.push(`<span class="chip">pain: <b>${esc(p)}</b></span>`));
    c.insights.integrations.forEach(i => chips.push(`<span class="chip">${esc(i)}</span>`));
  }
  $("d-chips").innerHTML = chips.join("");

  // Grounding
  if (c.grounding) {
    const conf = c.grounding.overall_confidence;
    const g = $("d-gconf");
    g.textContent = conf + " confidence";
    g.className = "badge " + (conf === "high" ? "ok" : conf === "medium" ? "warn" : "bad");
    $("d-grounding").innerHTML = c.grounding.checks.map(ch => `
      <div class="g-row ${ch.supported ? "" : "flagged"}">
        <span class="g-icon">${icon(ch.supported ? "check" : "alert")}</span>
        <div class="cl"><span class="fld">${esc(ch.field)}</span>${esc(ch.claim)}
          <span class="ev">${ch.supported ? "“" + esc(ch.evidence) + "”" : esc(ch.evidence)}</span></div>
      </div>`).join("");
  } else {
    $("d-gconf").className = "badge"; $("d-gconf").textContent = "—";
    $("d-grounding").innerHTML = '<div class="empty">No grounding report was produced for this call.</div>';
  }

  // Scorecard
  if (c.scorecard) {
    const score = c.scorecard.overall_score;
    const pct = score / 10, r = 38, circ = 2 * Math.PI * r;
    const color = score >= 7 ? "var(--ok)" : score >= 5 ? "var(--warn)" : "var(--bad)";
    $("d-gauge").setAttribute("aria-label", `Overall call score ${score} out of 10`);
    $("d-gauge").innerHTML = `
      <svg class="g" width="88" height="88" viewBox="0 0 88 88">
        <circle cx="44" cy="44" r="${r}" fill="none" stroke="var(--muted-bg)" stroke-width="7"/>
        <circle cx="44" cy="44" r="${r}" fill="none" stroke="${color}" stroke-width="7"
          stroke-linecap="round" stroke-dasharray="${(circ * pct).toFixed(1)} ${circ.toFixed(1)}"/>
      </svg><div class="val">${score}<small>/ 10</small></div>`;
    const dims = [
      ["Discovery", c.scorecard.discovery_quality],
      ["Objection handling", c.scorecard.objection_handling],
      ["Next-step clarity", c.scorecard.next_step_clarity],
    ];
    $("d-dims").innerHTML = dims.map(([name, d]) => `
      <div class="dim">
        <div class="top"><b>${name}</b><span>${d.score}/5</span></div>
        <div class="bar"><i style="width:${d.score * 20}%"></i></div>
        <div class="cm">${esc(d.comment)}</div>
      </div>`).join("");
    const section = (title, items) => items.length
      ? `<h4>${title}</h4><ul>${items.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : "";
    $("d-coach").innerHTML =
      section("Missed questions", c.scorecard.missed_questions) +
      section("Deal risks", c.scorecard.deal_risks) +
      section("Coaching tips", c.scorecard.coaching_tips);
  }

  // Email
  const approveBtn = $("approve-btn");
  const statusTag = $("d-emailstatus");
  $("approve-note").textContent = "";
  if (c.followup) {
    $("d-email").innerHTML = `
      <div class="email-meta"><span>To: <b>${esc(c.followup.receiver_email)}</b></span><span>From: <b>Auralis</b> (sent on approval)</span></div>
      <div class="email-subject">${esc(c.followup.email_subject)}</div>
      <div class="email-body">${esc(c.followup.email_body)}</div>`;
    if (c.followup_approved) {
      approveBtn.style.display = "none";
      statusTag.style.display = "inline-flex";
      statusTag.innerHTML = icon(c.email_status === "sent" ? "check" : c.email_status === "failed" ? "x" : "alert")
        + " email " + esc(c.email_status.replaceAll("_", " "));
      statusTag.className = "badge " + (c.email_status === "sent" ? "ok" : c.email_status === "failed" ? "bad" : "warn");
    } else {
      approveBtn.style.display = "inline-flex"; approveBtn.disabled = false;
      statusTag.style.display = "none";
    }
  } else {
    $("d-email").innerHTML = '<div class="empty">No draft was produced for this call.</div>';
    approveBtn.style.display = "none"; statusTag.style.display = "none";
  }
}

async function approve() {
  const btn = $("approve-btn");
  btn.disabled = true;
  try {
    const resp = await fetch(`/calls/${currentCallId}/approve-followup`, { method: "POST" });
    const data = await resp.json();
    toast(data.detail || "Approved.");
    const c = await (await fetch("/calls/" + currentCallId)).json();
    renderResults(c);
  } catch { toast("Approval request failed."); btn.disabled = false; }
}

/* ── Wire-up ──────────────────────────────────────────────── */
$("submit-btn").addEventListener("click", submitCall);
$("approve-btn").addEventListener("click", approve);
$("nav-new").addEventListener("click", () => { show("view-new"); history.replaceState(null, "", "/ui"); currentCallId = null; refreshList(); });
$("sample-btn").addEventListener("click", () => {
  $("f-name").value = SAMPLE.name; $("f-company").value = SAMPLE.company;
  $("f-role").value = SAMPLE.role; $("f-email").value = SAMPLE.email;
  $("f-transcript").value = SAMPLE.transcript;
});

refreshList();
setInterval(refreshList, 20000);
const params = new URLSearchParams(location.search);
if (params.get("call")) openCall(params.get("call"));
</script>
</body>
</html>
"""
