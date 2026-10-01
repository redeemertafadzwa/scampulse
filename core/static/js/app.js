import { assess, PLAIN_NAME } from "./inference.js";
import { redact, fingerprint } from "./normalise.js";
import { STRINGS } from "./strings.js";

const $ = (s) => document.querySelector(s);
const LS = window.localStorage;
let MODEL = null, BLOCKLIST = [], LANG = LS.getItem("sp_lang") || "en";
let lastText = "", lastResult = null, feedEtag = null, mvEtag = null;

// ---------- device token (anonymous, local) ----------
function device() {
  let t = LS.getItem("sp_device");
  if (!t) { t = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2)); LS.setItem("sp_device", t); }
  return t;
}
const HEADERS = () => ({ "Content-Type": "application/json", "X-Device-Token": device() });

// ---------- i18n (English complete; others fall back to English) ----------
function t(key) {
  const pack = STRINGS[LANG] || {};
  const entry = pack[key];
  if (entry && entry.reviewed) return entry.text;      // only show reviewed strings
  return (STRINGS.en[key] || { text: key }).text;      // fallback to English
}
function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
}

// ---------- navigation ----------
function show(name) {
  document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
  $("#screen-" + name).classList.add("active");
  document.querySelectorAll("#nav button").forEach((b) =>
    b.classList.toggle("active", b.dataset.screen === name));
  window.scrollTo(0, 0);
}
document.querySelectorAll("#nav button").forEach((b) =>
  b.addEventListener("click", () => {
    show(b.dataset.screen);
    if (b.dataset.screen === "send") renderSend(false);
    if (b.dataset.screen === "feed") loadFeed();
  }));
$("#btn-settings").addEventListener("click", () => show("settings"));

function toast(msg) {
  const el = $("#toast"); el.textContent = msg; el.hidden = false;
  setTimeout(() => { el.hidden = true; }, 2600);
}
function esc(s) { return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

// ---------- model ----------
async function loadModel() {
  try { MODEL = await (await fetch("/static/model.json", { cache: "no-cache" })).json();
        LS.setItem("sp_model", JSON.stringify(MODEL)); }
  catch { const c = LS.getItem("sp_model"); if (c) MODEL = JSON.parse(c); }
}

// ---------- check flow ----------
$("#btn-paste").addEventListener("click", async () => {
  try { $("#msg").value = await navigator.clipboard.readText(); }
  catch { toast("Clipboard blocked — paste manually"); }
});
$("#btn-clear").addEventListener("click", () => { $("#msg").value = ""; });
$("#btn-check").addEventListener("click", runCheck);
$("#btn-check-another").addEventListener("click", () => { show("check"); $("#msg").focus(); });

function runCheck() {
  const text = $("#msg").value.trim();
  if (!text) { toast("Paste a message first"); return; }
  lastText = text;
  lastResult = assess(text, MODEL, BLOCKLIST);
  renderVerdict(lastResult, text);
  show("verdict");
}

const FLAGS = [
  [/\b(pin|otp|password|cvv|passcode)\b/gi, "asks for PIN/OTP"],
  [/\b(national id|id number|selfie|passport|kyc)\b/gi, "asks for ID"],
  [/((https?:\/\/|www\.)\S+|\b[a-z0-9][\w\-.]*\.(?:com|net|org|co|invalid|xyz|link|online|site|top|info|click|app)\b\S*)/gi, "suspicious link"],
  [/\b(urgent|immediately|today only|expires?|before midnight|last chance|hurry|quiet|secret)\b/gi, "pressure"],
  [/\b(won|winner|congratulations|prize|reward|bonus|lottery|free)\b/gi, "unexpected prize"],
  [/\b(fee|deposit|activation|clearance|processing|registration)\b/gi, "asks for money"],
  [/\b(voice ?-?note|video|clip|recording)\b/gi, "voice/video claim"],
];
function highlight(text) {
  let h = esc(text);
  for (const [rx, label] of FLAGS)
    h = h.replace(rx, (m) => `<span class="highlight" title="${label}">${m}</span>`);
  return h;
}

function renderVerdict(r, text) {
  const map = { "Danger": ["danger", "!", t("danger")], "Be careful": ["caution", "~", t("becareful")],
                "No warning signs found": ["ok", "✓", t("nowarn")] };
  const [cls, sym, word] = map[r.verdict] || map["No warning signs found"];
  const band = $("#band"); band.className = "band " + cls;
  $("#band-sym").textContent = sym; $("#band-word").textContent = word;
  $("#verdict-name").textContent = PLAIN_NAME[r.threat_type] || r.threat_type;
  $("#verdict-why").textContent = r.reasons && r.reasons.length
    ? `This looks like ${(PLAIN_NAME[r.threat_type] || "a risk").toLowerCase()} — ${r.reasons[0]}.`
    : "No clear warning signs in this message.";
  const act = $("#verdict-action"); act.textContent = r.action;
  act.onclick = () => { if (r.risk === "High") startSend(true); else show("check"); };

  const flags = (r.reasons || []).map((x) => `<li><span class="flag">${esc(x)}</span></li>`).join("");
  $("#why-body").innerHTML =
    `<p class="eyebrow">The message</p><p>${highlight(text)}</p>` +
    (flags ? `<p class="eyebrow">Red-flag signals</p><ul class="reasons">${flags}</ul>` : "") +
    `<p class="muted" style="font-size:.85rem">Technical type: ${esc(r.threat_type)} · confidence ${r.confidence}</p>`;
}

// ---------- read aloud ----------
$("#btn-read").addEventListener("click", () => {
  if (!("speechSynthesis" in window)) return;
  const u = new SpeechSynthesisUtterance(
    `${$("#band-word").textContent}. ${$("#verdict-name").textContent}. ${$("#verdict-why").textContent}`);
  speechSynthesis.speak(u);
});

// ---------- report as scam (opt-in, redacted) ----------
$("#btn-report-scam").addEventListener("click", async () => {
  const red = redact(lastText);
  if (!confirm("This is exactly what will be sent (identifying details removed):\n\n" + red +
               "\n\nNothing else leaves your phone. Send this report?")) return;
  const fp = fingerprint(lastText);
  BLOCKLIST.push({ f: fp, c: lastResult.threat_type });           // instant local catch
  LS.setItem("sp_blocklist", JSON.stringify(BLOCKLIST));
  queueOutbox({ redacted_text: red, claimed_category: lastResult.threat_type });
  flushOutbox();
  toast("Reported. Shown as unverified until confirmed.");
});
$("#btn-fine").addEventListener("click", () => toast("Thanks — counted as ‘this is fine’."));

function queueOutbox(item) {
  const box = JSON.parse(LS.getItem("sp_outbox") || "[]"); box.push(item);
  LS.setItem("sp_outbox", JSON.stringify(box));
}
async function flushOutbox() {
  if (!navigator.onLine) return;
  const box = JSON.parse(LS.getItem("sp_outbox") || "[]"); const keep = [];
  for (const item of box) {
    try { const r = await fetch("/api/reports/", { method: "POST", headers: HEADERS(), body: JSON.stringify(item) });
          if (!r.ok) keep.push(item); }
    catch { keep.push(item); }
  }
  LS.setItem("sp_outbox", JSON.stringify(keep));
}
window.addEventListener("online", flushOutbox);

// ---------- make report ----------
$("#btn-make-report").addEventListener("click", () => {
  if (!lastResult) { toast("Check a message first"); return; }
  const now = new Date().toISOString().replace("T", " ").slice(0, 16);
  const id = "SP-" + Date.now().toString(36).toUpperCase();
  $("#report-text").textContent =
`ScamPulse report
ID:        ${id}
Time:      ${now}
Channel:   (as received)
Threat:    ${lastResult.threat_type}
Risk:      ${lastResult.risk}
Signals:   ${(lastResult.reasons || []).join(", ") || "—"}
Action:    ${lastResult.action}

Message (redacted):
${redact(lastText)}

— Generated by ScamPulse. All identifying details removed.`;
  show("report");
});
$("#btn-copy").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("#report-text").textContent); toast("Copied"); }
  catch { toast("Copy blocked"); }
});
$("#btn-download").addEventListener("click", () => {
  const blob = new Blob([$("#report-text").textContent], { type: "text/plain" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
  a.download = "scampulse-report.txt"; a.click();
});

// ---------- feed ----------
async function loadFeed() {
  try {
    const r = await fetch("/api/feed/", { headers: feedEtag ? { "If-None-Match": feedEtag } : {} });
    if (r.status === 304) return;
    feedEtag = r.headers.get("ETag");
    const data = await r.json(); LS.setItem("sp_feed", JSON.stringify(data)); renderFeed(data);
  } catch { const c = LS.getItem("sp_feed"); if (c) renderFeed(JSON.parse(c)); }
}
function renderFeed(data) {
  if (!data.length) { $("#feed-list").innerHTML = `<p class="muted">No confirmed scams yet.</p>`; return; }
  $("#feed-list").innerHTML = data.map((f) => `
    <div class="family">
      <div class="count">${f.reports_today || f.report_count}</div>
      <div style="flex:1">
        <div><span class="tag ${f.is_example ? "ex" : ""}">${f.is_example ? "Example" : f.category}</span></div>
        <div style="margin:4px 0">${esc(f.representative_text)}</div>
        <div class="muted" style="font-size:.82rem">${f.report_count} report(s) · ${f.category}</div>
      </div>
    </div>`).join("");
}

// ---------- model version polling ----------
async function pollModelVersion() {
  try {
    const r = await fetch("/api/model-version/", { headers: mvEtag ? { "If-None-Match": mvEtag } : {} });
    if (r.status === 304) return;
    mvEtag = r.headers.get("ETag");
    const v = await r.json();
    if (v.version && v.version !== LS.getItem("sp_modelver")) {
      LS.setItem("sp_modelver", v.version); await loadModel();
      $("#last-updated").textContent = "Last updated: model " + v.version + ", " + new Date().toLocaleString();
    }
  } catch { /* offline: keep current model */ }
}

// ---------- before you send ----------
const WHO = ["Someone I know (message or voice note)", "My boss or work", "A company or bank",
             "A government office", "A seller", "Someone new"];
const Q = ["Are they in a hurry?", "Did they contact you first?", "Are they asking you to keep it secret?"];
let sendState = { who: null, ans: [null, null, null] };
function startSend(fromHigh) {
  sendState = { who: null, ans: [null, null, null] };
  show("send"); renderSend(fromHigh);
}
function renderSend(fromHigh) {
  const banner = fromHigh ? `<div class="rec warn"><strong>Hold on. Check before you send.</strong></div>` : "";
  const who = WHO.map((w, i) => `<button class="choice ${sendState.who === i ? "sel" : ""}" data-who="${i}">${w}</button>`).join("");
  const qs = Q.map((q, i) => `<div class="field"><label>${q}</label>
     <div class="btn-row"><button class="btn btn-ghost btn-sm q" data-q="${i}" data-v="1">Yes</button>
     <button class="btn btn-ghost btn-sm q" data-q="${i}" data-v="0">No</button>
     <span class="pill" id="qp${i}">${sendState.ans[i] === null ? "—" : sendState.ans[i] ? "Yes" : "No"}</span></div></div>`).join("");
  $("#send-flow").innerHTML =
    `${banner}<div class="card"><p class="eyebrow">Who is asking you for money?</p>${who}</div>
     <div class="card"><p class="eyebrow">Three quick questions</p>${qs}</div>
     <div id="send-out"></div>`;
  $("#send-flow").querySelectorAll("[data-who]").forEach((b) =>
    b.onclick = () => { sendState.who = +b.dataset.who; renderSend(fromHigh); computeSend(); });
  $("#send-flow").querySelectorAll(".q").forEach((b) =>
    b.onclick = () => { sendState.ans[+b.dataset.q] = +b.dataset.v; renderSend(fromHigh); computeSend(); });
  computeSend();
}
function computeSend() {
  if (sendState.who === null || sendState.ans.includes(null)) return;
  const risky = sendState.ans[0] + (sendState.ans[1]) + sendState.ans[2];  // hurry + contacted-first + secret
  const sw = LS.getItem("sp_safeword");
  const steps = [
    "Call the official number from the company's website or your bank card — not the number in the message.",
    "Ask something only the real person would know.",
    "Wait 10 minutes and talk to someone you trust.",
  ];
  if (sw) steps.push(`Ask for your family/office safe-word (“${esc(sw)}”).`);
  const bad = risky >= 2 || sendState.who >= 4;
  $("#send-out").innerHTML = `<div class="rec ${bad ? "warn" : ""}">
    <strong>${bad ? "Do not send money yet." : "Looks lower-risk, but still verify."}</strong>
    <ul>${steps.map((s) => `<li>${s}</li>`).join("")}</ul>
    <p class="muted" style="font-size:.85rem">This is advice only. ScamPulse never blocks or controls payments.</p></div>`;
}

// ---------- settings ----------
$("#lang").value = LANG;
$("#lang").addEventListener("change", (e) => { LANG = e.target.value; LS.setItem("sp_lang", LANG); applyI18n(); });
$("#safeword").value = LS.getItem("sp_safeword") || "";
$("#safeword").addEventListener("change", (e) => LS.setItem("sp_safeword", e.target.value.trim()));
$("#btn-privacy").addEventListener("click", () => show("privacy"));
$("#btn-delete").addEventListener("click", () => {
  if (confirm("Delete the device token, safe-word, local blocklist and queued reports from this phone?")) {
    ["sp_device", "sp_safeword", "sp_blocklist", "sp_outbox", "sp_feed", "sp_model", "sp_modelver"].forEach((k) => LS.removeItem(k));
    BLOCKLIST = []; toast("Local data deleted.");
  }
});

// ---------- init ----------
async function init() {
  applyI18n();
  BLOCKLIST = JSON.parse(LS.getItem("sp_blocklist") || "[]");
  if (!("speechSynthesis" in window)) $("#btn-read").style.display = "none";
  await loadModel();
  startSendPlaceholder();
  loadFeed(); pollModelVersion(); flushOutbox();
  setInterval(() => { if (navigator.onLine) { loadFeed(); pollModelVersion(); } }, 30000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden && navigator.onLine) { loadFeed(); pollModelVersion(); } });

  // shared text (PWA share_target, GET)
  const shared = new URLSearchParams(location.search).get("text");
  if (shared) { $("#msg").value = shared; runCheck(); }

  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
}
function startSendPlaceholder() {
  // make the "Before you send" tab usable even without a prior verdict
  $("#screen-send").querySelector("#send-flow") && renderSend(false);
}
init();
