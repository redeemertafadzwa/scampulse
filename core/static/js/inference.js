// On-device inference: TF-IDF (word + char_wb) + logistic regression, plus the
// same rule signals and cautious voting as engine.py. No ML libraries.
import { normalise, fingerprint } from "./normalise.js";

const SCAM = new Set(["Financial Scam", "Phishing", "Identity Fraud",
                      "Malicious Link", "AI-Enabled Threat"]);

const RULES = [
  ["asks for PIN/OTP", /\b(send|share|enter|reply with|provide)\b[^.]{0,25}\b(pin|otp|password|cvv|passcode)\b/, "Identity Fraud", 3],
  ["asks for ID/selfie", /\b(id|identity|national id|passport|kyc|selfie)\b[^.]{0,25}\b(photo|picture|send|upload|reply|number)\b/, "Identity Fraud", 3],
  ["asks for money", /\b(send|pay|deposit|transfer|reverse|activation|clearance|processing|registration)\b[^.]{0,25}\b(amounttoken|fee|money|cash|back)\b/, "Financial Scam", 3],
  ["unexpected prize", /\b(won|winner|congratulations|prize|reward|bonus|lottery|selected|free)\b/, "Financial Scam", 2],
  ["pressure / urgency", /(urgent|immediately|now|today only|expires?|within 24|before midnight|last chance|act now|hurry|quiet|secret)/, null, 1],
  ["suspicious link", /urltoken/, "Malicious Link", 2],
  ["voice/video claim", /(voice[\s-]?note|video|clip|recording)/, "AI-Enabled Threat", 2],
  ["authority impersonation", /(bank|ecocash|onemoney|cbz|zb bank|steward|telecash|nmb|econet|netone|telecel|ceo|boss|minister|government|customs|zesa|council|police)/, null, 1],
];

export const ACTIONS = {
  "Financial Scam": "Do not send money. Verify with the company using a number from their official website.",
  "Phishing": "Do not click the link or enter your details. Open the official app yourself instead.",
  "Identity Fraud": "Never send your ID, selfie, PIN or OTP. Real companies don't ask for these.",
  "Malicious Link": "Do not open the link. Type the official address yourself if you need the service.",
  "AI-Enabled Threat": "We can't check audio or video. Confirm it's really them another way.",
  "Benign": "No warning signs found, but stay alert if money or your PIN is involved.",
  "Uncertain": "Not sure - treat it as suspicious and verify before acting.",
};

function wordGrams(text, min, max) {
  const toks = text.match(/\b\w\w+\b/gu) || [];
  const grams = [];
  for (let n = min; n <= max; n++)
    for (let i = 0; i + n <= toks.length; i++) grams.push(toks.slice(i, i + n).join(" "));
  return grams;
}

function charWbGrams(text, min, max) {
  text = text.replace(/\s\s+/g, " ");
  const grams = [];
  for (const word of text.split(" ")) {
    if (!word) continue;
    const w = " " + word + " ", L = w.length;
    for (let n = min; n <= max; n++) {
      let offset = 0;
      grams.push(w.slice(0, n));
      while (offset + n < L) { offset++; grams.push(w.slice(offset, offset + n)); }
      if (offset === 0) break;
    }
  }
  return grams;
}

function blockVector(grams, block) {
  const counts = {};
  for (const g of grams) {
    const idx = block.vocab[g];
    if (idx !== undefined) counts[idx] = (counts[idx] || 0) + 1;
  }
  let norm = 0;
  const vals = {};
  for (const idx in counts) {
    const v = (1 + Math.log(counts[idx])) * block.idf[idx];
    vals[idx] = v; norm += v * v;
  }
  norm = Math.sqrt(norm) || 1;
  for (const idx in vals) vals[idx] /= norm;
  return vals;
}

function modelPredict(model, text) {
  const w = model.blocks.w, c = model.blocks.c;
  const nw = Object.keys(w.vocab).length;
  const wv = blockVector(wordGrams(text, w.ngram[0], w.ngram[1]), w);
  const cv = blockVector(charWbGrams(text, c.ngram[0], c.ngram[1]), c);
  const scores = model.intercept.slice();
  for (let k = 0; k < model.classes.length; k++) {
    const coef = model.coef[k];
    for (const idx in wv) scores[k] += coef[idx] * wv[idx];
    for (const idx in cv) scores[k] += coef[nw + Number(idx)] * cv[idx];
  }
  const m = Math.max(...scores);
  const exp = scores.map((s) => Math.exp(s - m));
  const sum = exp.reduce((a, b) => a + b, 0);
  const probs = exp.map((e) => e / sum);
  let best = 0;
  for (let i = 1; i < probs.length; i++) if (probs[i] > probs[best]) best = i;
  return { threat: model.classes[best], conf: probs[best] };
}

export function ruleAssess(text) {
  const n = normalise(text);
  const reasons = []; let score = 0, maxW = 0; const votes = {};
  for (const [label, rx, threat, weight] of RULES) {
    if (rx.test(n)) {
      reasons.push(label); score += weight; maxW = Math.max(maxW, weight);
      if (threat) votes[threat] = (votes[threat] || 0) + weight;
    }
  }
  let ruleThreat = null, bestv = 0;
  for (const t in votes) if (votes[t] > bestv) { bestv = votes[t]; ruleThreat = t; }
  return { reasons, score, ruleThreat, maxW };
}

// optional blocklist: array of confirmed fingerprints -> instant Danger
export function assess(text, model, blocklist) {
  const { reasons, score, ruleThreat, maxW } = ruleAssess(text);

  if (blocklist && blocklist.length) {
    const fp = fingerprint(text);
    for (const b of blocklist) {
      if (b.f === fp || b.f === fp) {
        return { verdict: "Danger", threat_type: b.c || "Financial Scam", risk: "High",
                 reasons: ["reported by the community before", ...reasons], confidence: 1,
                 action: ACTIONS[b.c] || ACTIONS["Financial Scam"] };
      }
    }
  }

  let mThreat = null, mConf = 0;
  if (model) { const r = modelPredict(model, normalise(text)); mThreat = r.threat; mConf = r.conf; }

  const modelScam = SCAM.has(mThreat);
  const rulesScam = maxW >= 3 || score >= 4;

  if (modelScam || rulesScam) {
    let threat = (rulesScam && ruleThreat) ? ruleThreat : mThreat;
    if (modelScam && maxW < 3) threat = mThreat;
    const risk = (maxW >= 3 || score >= 4 || mConf >= 0.6 ||
                  threat === "Identity Fraud" || threat === "Phishing") ? "High" : "Medium";
    return { verdict: risk === "High" ? "Danger" : "Be careful", threat_type: threat, risk,
             reasons: reasons.length ? reasons : [`matches known ${threat} pattern`],
             confidence: +mConf.toFixed(2), action: ACTIONS[threat] || ACTIONS["Financial Scam"] };
  }
  if (maxW >= 2 && mConf < 0.5) {
    return { verdict: "Be careful", threat_type: "Uncertain", risk: "Medium",
             reasons: reasons.length ? reasons : ["unclear message"],
             confidence: +mConf.toFixed(2), action: ACTIONS["Uncertain"] };
  }
  return { verdict: "No warning signs found", threat_type: "Benign", risk: "Low",
           reasons, confidence: +mConf.toFixed(2), action: ACTIONS["Benign"] };
}

// human-readable scam name shown to the user
export const PLAIN_NAME = {
  "Financial Scam": "Money scam", "Phishing": "Fake login / account trick",
  "Identity Fraud": "Stealing your ID or PIN", "Malicious Link": "Dangerous link",
  "AI-Enabled Threat": "Fake boss / fake voice or video", "Benign": "No clear scam signs",
  "Uncertain": "Not sure",
};
