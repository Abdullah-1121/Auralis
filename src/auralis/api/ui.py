"""
Single-file demo dashboard served at GET /ui.

Deliberately dependency-free (no build step, no CDN): one HTML string with
inline CSS/JS. It exists to demo the product — submit a transcript, watch
the pipeline steps complete live over SSE, review the grounding report and
scorecard, and approve the follow-up send.
"""

UI_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Auralis — Post-Call Intelligence</title>
<style>
  :root {
    --bg: #0d1117; --panel: #161b22; --border: #30363d; --text: #e6edf3;
    --muted: #8b949e; --accent: #58a6ff; --ok: #3fb950; --warn: #d29922;
    --bad: #f85149; --chip: #21262d;
  }
  * { box-sizing: border-box; margin: 0; }
  body { background: var(--bg); color: var(--text); font: 15px/1.5 -apple-system, "Segoe UI", Roboto, sans-serif; }
  .wrap { max-width: 1100px; margin: 0 auto; padding: 24px 16px 80px; }
  header { display: flex; align-items: baseline; gap: 12px; margin-bottom: 20px; }
  header h1 { font-size: 22px; }
  header span { color: var(--muted); font-size: 14px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
  .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
  .panel h2 { font-size: 15px; margin-bottom: 12px; color: var(--accent); }
  label { display: block; font-size: 12px; color: var(--muted); margin: 10px 0 4px; }
  input, textarea { width: 100%; background: var(--bg); color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; font: inherit; }
  textarea { min-height: 180px; resize: vertical; }
  .row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  button { background: #238636; color: #fff; border: 0; border-radius: 6px; padding: 10px 18px; font: inherit; font-weight: 600; cursor: pointer; margin-top: 14px; }
  button:disabled { opacity: .5; cursor: default; }
  button.secondary { background: var(--chip); border: 1px solid var(--border); }
  .steps { list-style: none; }
  .steps li { display: flex; align-items: center; gap: 10px; padding: 7px 4px; color: var(--muted); }
  .steps .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--border); flex: none; }
  .steps li.active { color: var(--text); }
  .steps li.active .dot { background: var(--accent); animation: pulse 1s infinite alternate; }
  .steps li.done { color: var(--text); }
  .steps li.done .dot { background: var(--ok); }
  .steps li.failed { color: var(--bad); }
  .steps li.failed .dot { background: var(--bad); }
  @keyframes pulse { from { opacity: .4 } to { opacity: 1 } }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0; }
  .chip { background: var(--chip); border: 1px solid var(--border); border-radius: 999px; padding: 2px 10px; font-size: 12.5px; }
  .check { border-left: 3px solid var(--ok); background: var(--bg); border-radius: 4px; padding: 8px 10px; margin: 6px 0; font-size: 13.5px; }
  .check.flagged { border-left-color: var(--bad); }
  .check .ev { color: var(--muted); font-style: italic; display: block; margin-top: 2px; }
  .score-row { display: flex; align-items: center; gap: 10px; margin: 8px 0; }
  .score-row .name { width: 150px; font-size: 13px; color: var(--muted); flex: none; }
  .bar { flex: 1; height: 8px; background: var(--chip); border-radius: 4px; overflow: hidden; }
  .bar i { display: block; height: 100%; background: var(--accent); }
  .big-score { font-size: 34px; font-weight: 700; }
  .email-box { background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 12px; white-space: pre-wrap; font-size: 14px; margin-top: 8px; }
  .status-line { margin-top: 10px; font-size: 13.5px; color: var(--muted); }
  .tag { font-size: 12px; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--border); }
  .tag.ok { color: var(--ok); border-color: var(--ok); }
  .tag.warn { color: var(--warn); border-color: var(--warn); }
  .tag.bad { color: var(--bad); border-color: var(--bad); }
  .hidden { display: none; }
  ul.plain { padding-left: 18px; font-size: 13.5px; }
  ul.plain li { margin: 4px 0; }
  h3.sub { font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; margin: 16px 0 6px; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Auralis</h1>
    <span>post-call sales intelligence — transcript in, verified follow-up out</span>
  </header>

  <div class="grid">
    <div>
      <div class="panel" id="form-panel">
        <h2>1 · Submit a call</h2>
        <div class="row2">
          <div><label>Customer name</label><input id="f-name" value=""></div>
          <div><label>Company</label><input id="f-company" value=""></div>
        </div>
        <div class="row2">
          <div><label>Role</label><input id="f-role" value=""></div>
          <div><label>Email</label><input id="f-email" value=""></div>
        </div>
        <label>Transcript</label>
        <textarea id="f-transcript" placeholder="Rep: Hi ... Customer: ..."></textarea>
        <button id="submit-btn">Analyze call</button>
      </div>

      <div class="panel" style="margin-top:16px">
        <h2>2 · Pipeline <span id="call-id-tag" class="tag hidden"></span></h2>
        <ul class="steps" id="steps">
          <li data-step="summarizing"><span class="dot"></span>Summarize the call</li>
          <li data-step="extracting_insights"><span class="dot"></span>Extract insights</li>
          <li data-step="verifying_insights"><span class="dot"></span>Verify claims against transcript</li>
          <li data-step="drafting_followup"><span class="dot"></span>Draft follow-up (verified facts only)</li>
          <li data-step="scoring_call"><span class="dot"></span>Score the rep's performance</li>
          <li data-step="writing_crm"><span class="dot"></span>Write CRM record</li>
        </ul>
        <div class="status-line" id="pipeline-status">Waiting for a call…</div>
      </div>
    </div>

    <div id="results" class="hidden">
      <div class="panel">
        <h2>3 · Results</h2>
        <div id="r-summary"></div>
        <h3 class="sub">Grounding report <span id="r-confidence" class="tag"></span></h3>
        <div id="r-grounding"></div>
        <h3 class="sub">Call scorecard</h3>
        <div class="score-row"><span class="big-score" id="r-overall"></span><span style="color:var(--muted)">/ 10 overall</span></div>
        <div id="r-dimensions"></div>
        <div id="r-coaching"></div>
      </div>
      <div class="panel" style="margin-top:16px">
        <h2>4 · Follow-up email <span id="r-email-status" class="tag hidden"></span></h2>
        <div id="r-email"></div>
        <button id="approve-btn" class="hidden">Approve &amp; send</button>
        <div class="status-line" id="approve-result"></div>
      </div>
    </div>
  </div>
</div>

<script>
const STEP_ORDER = ["summarizing","extracting_insights","verifying_insights",
                    "drafting_followup","scoring_call","writing_crm"];
let currentCallId = null;

function esc(s) { const d = document.createElement("div"); d.textContent = s ?? ""; return d.innerHTML; }

function setSteps(status, failedStep) {
  const idx = STEP_ORDER.indexOf(status);
  document.querySelectorAll("#steps li").forEach((li, i) => {
    li.className = "";
    const step = li.dataset.step;
    if (status === "done") li.className = "done";
    else if (status === "failed") li.className = step === failedStep ? "failed" : (STEP_ORDER.indexOf(failedStep) > i ? "done" : "");
    else if (i < idx) li.className = "done";
    else if (i === idx) li.className = "active";
  });
}

async function submitCall() {
  const body = {
    transcript: document.getElementById("f-transcript").value,
    customer: {
      name: document.getElementById("f-name").value,
      company: document.getElementById("f-company").value,
      role: document.getElementById("f-role").value,
      email: document.getElementById("f-email").value,
    },
  };
  const btn = document.getElementById("submit-btn");
  btn.disabled = true;
  try {
    const resp = await fetch("/calls", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body) });
    if (!resp.ok) { const e = await resp.json(); throw new Error(JSON.stringify(e.detail)); }
    const data = await resp.json();
    watchCall(data.call_id);
  } catch (err) {
    document.getElementById("pipeline-status").textContent = "Submit failed: " + err.message;
    btn.disabled = false;
  }
}

function watchCall(callId) {
  currentCallId = callId;
  const tag = document.getElementById("call-id-tag");
  tag.textContent = callId; tag.classList.remove("hidden");
  document.getElementById("results").classList.add("hidden");
  document.getElementById("pipeline-status").textContent = "Processing…";
  const es = new EventSource(`/calls/${callId}/events`);
  es.onmessage = (ev) => {
    const st = JSON.parse(ev.data);
    setSteps(st.status, st.failed_step);
    if (st.status === "done") {
      es.close();
      document.getElementById("pipeline-status").innerHTML =
        `Done. CRM: <span class="tag ${st.crm_status === "written" ? "ok" : st.crm_status === "failed" ? "bad" : "warn"}">${st.crm_status}</span>`;
      loadResults(callId);
    } else if (st.status === "failed") {
      es.close();
      document.getElementById("pipeline-status").innerHTML =
        `<span class="tag bad">failed at ${esc(st.failed_step)}</span> ${esc(st.error || "")}`;
      document.getElementById("submit-btn").disabled = false;
      loadResults(callId); // partial results survive — show them
    } else {
      document.getElementById("pipeline-status").textContent = "Processing: " + st.status.replaceAll("_", " ") + "…";
    }
  };
  es.onerror = () => { /* SSE closes when the server ends the stream */ };
}

async function loadResults(callId) {
  const c = await (await fetch(`/calls/${callId}`)).json();
  document.getElementById("results").classList.remove("hidden");
  document.getElementById("submit-btn").disabled = false;

  document.getElementById("r-summary").innerHTML = c.summary
    ? `<p style="font-size:14px">${esc(c.summary.summary)}</p>` +
      (c.insights ? `<div class="chips">
        <span class="chip">sentiment: ${esc(c.insights.sentiment)}</span>
        ${c.insights.sales_stage ? `<span class="chip">stage: ${esc(c.insights.sales_stage)}</span>` : ""}
        ${c.insights.integrations.map(i => `<span class="chip">${esc(i)}</span>`).join("")}
      </div>` : "")
    : "<p class='status-line'>No summary produced.</p>";

  const conf = document.getElementById("r-confidence");
  if (c.grounding) {
    conf.textContent = c.grounding.overall_confidence + " confidence";
    conf.className = "tag " + (c.grounding.overall_confidence === "high" ? "ok" : c.grounding.overall_confidence === "medium" ? "warn" : "bad");
    document.getElementById("r-grounding").innerHTML = c.grounding.checks.map(ch => `
      <div class="check ${ch.supported ? "" : "flagged"}">
        ${ch.supported ? "✓" : "⚠ FLAGGED"} <strong>${esc(ch.field)}</strong>: ${esc(ch.claim)}
        <span class="ev">${ch.supported ? "“" + esc(ch.evidence) + "”" : esc(ch.evidence)}</span>
      </div>`).join("");
  } else {
    conf.className = "tag hidden";
    document.getElementById("r-grounding").innerHTML = "<p class='status-line'>No grounding report.</p>";
  }

  if (c.scorecard) {
    document.getElementById("r-overall").textContent = c.scorecard.overall_score;
    const dims = [["Discovery", c.scorecard.discovery_quality], ["Objection handling", c.scorecard.objection_handling], ["Next-step clarity", c.scorecard.next_step_clarity]];
    document.getElementById("r-dimensions").innerHTML = dims.map(([name, d]) => `
      <div class="score-row"><span class="name">${name}</span>
        <div class="bar"><i style="width:${d.score * 20}%"></i></div>
        <span style="font-size:13px">${d.score}/5</span></div>
      <div style="font-size:12.5px;color:var(--muted);margin:-4px 0 8px 160px">${esc(d.comment)}</div>`).join("");
    document.getElementById("r-coaching").innerHTML =
      (c.scorecard.missed_questions.length ? `<h3 class="sub">Missed questions</h3><ul class="plain">${c.scorecard.missed_questions.map(q => `<li>${esc(q)}</li>`).join("")}</ul>` : "") +
      (c.scorecard.deal_risks.length ? `<h3 class="sub">Deal risks</h3><ul class="plain">${c.scorecard.deal_risks.map(q => `<li>${esc(q)}</li>`).join("")}</ul>` : "") +
      (c.scorecard.coaching_tips.length ? `<h3 class="sub">Coaching tips</h3><ul class="plain">${c.scorecard.coaching_tips.map(q => `<li>${esc(q)}</li>`).join("")}</ul>` : "");
  }

  const emailStatusTag = document.getElementById("r-email-status");
  const approveBtn = document.getElementById("approve-btn");
  if (c.followup) {
    document.getElementById("r-email").innerHTML = `
      <div class="status-line">To: ${esc(c.followup.receiver_email)}</div>
      <div class="email-box"><strong>${esc(c.followup.email_subject)}</strong>\n\n${esc(c.followup.email_body)}</div>`;
    emailStatusTag.classList.remove("hidden");
    emailStatusTag.textContent = c.followup_approved ? c.email_status.replaceAll("_", " ") : "awaiting approval";
    emailStatusTag.className = "tag " + (c.email_status === "sent" ? "ok" : c.followup_approved ? "warn" : "");
    approveBtn.classList.toggle("hidden", c.followup_approved);
    approveBtn.disabled = false;
  } else {
    document.getElementById("r-email").innerHTML = "<p class='status-line'>No draft produced.</p>";
    emailStatusTag.className = "tag hidden";
    approveBtn.classList.add("hidden");
  }
}

async function approve() {
  const btn = document.getElementById("approve-btn");
  btn.disabled = true;
  const resp = await fetch(`/calls/${currentCallId}/approve-followup`, { method: "POST" });
  const data = await resp.json();
  document.getElementById("approve-result").textContent = data.detail || JSON.stringify(data);
  loadResults(currentCallId);
}

document.getElementById("submit-btn").addEventListener("click", submitCall);
document.getElementById("approve-btn").addEventListener("click", approve);

// Deep link from Slack: /ui?call=<id>
const params = new URLSearchParams(location.search);
if (params.get("call")) {
  const id = params.get("call");
  fetch(`/calls/${id}`).then(r => {
    if (!r.ok) throw new Error();
    return r.json();
  }).then(c => {
    if (c.status === "done" || c.status === "failed") {
      currentCallId = id;
      const tag = document.getElementById("call-id-tag");
      tag.textContent = id; tag.classList.remove("hidden");
      setSteps(c.status, c.failed_step);
      document.getElementById("pipeline-status").textContent = c.status === "done" ? "Done." : "Failed.";
      loadResults(id);
    } else {
      watchCall(id);
    }
  }).catch(() => {
    document.getElementById("pipeline-status").textContent = `Call ${id} not found.`;
  });
}
</script>
</body>
</html>
"""
