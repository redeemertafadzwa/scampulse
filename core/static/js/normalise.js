// ScamPulse shared text module (JS) - mirrors normalise.py EXACTLY.
// A parity test feeds 200+ inputs through both and fails on any difference.

const LEET = { "0": "o", "1": "l", "3": "e", "4": "a", "5": "s",
               "7": "t", "8": "b", "@": "a", "$": "s", "|": "l" };

const URL = /(?:https?:\/\/|www\.)\S+|\b[a-z0-9][a-z0-9\-.]*\.(?:com|net|org|co|co\.zw|zw|link|xyz|info|invalid|click|top|live|app|ru|cn|tk|ml|ga|cf|gq|shop|online|site)\b(?:\/\S*)?/gi;
const PHONE = /(?:\+?263|0)(?:7[0-9]|86)\d(?:[\s\-]?\d){6,7}/g;
const AMOUNT = /(?:us\$|usd|zwl|rtgs|zar|r|\$|€|£)\s?\d[\d,]*(?:\.\d+)?|\b\d[\d,]*(?:\.\d+)?\s?(?:usd|dollars?|rands?|bond|zwl|rtgs|pounds?)\b/gi;
const ACCOUNT = /\b\d{6,}\b/g;
const NAME = /\b(dear|hi|hello|hey|mr|mrs|ms|miss|dr)\b[\s,]+([A-Z][a-z]+)/g;
const SPACE = /\s+/g;

function collapse(s) { return s.replace(SPACE, " ").trim(); }

export function redact(text) {
  if (!text) return "";
  let t = text;
  t = t.replace(URL, "[link]");
  t = t.replace(PHONE, "[phone]");
  t = t.replace(AMOUNT, "[amount]");
  t = t.replace(NAME, "$1 [name]");
  t = t.replace(ACCOUNT, "[number]");
  return collapse(t);
}

export function normalise(text) {
  if (!text) return "";
  let t = text.toLowerCase();
  t = t.replace(URL, " urltoken ");
  t = t.replace(PHONE, " phonetoken ");
  t = t.replace(AMOUNT, " amounttoken ");
  t = t.replace(ACCOUNT, " numtoken ");
  return collapse(t);
}

export function fingerprint(text) {
  let t = normalise(text);
  t = t.replace(/[0135784@$|]/g, (c) => LEET[c]);
  t = t.replace(/(urltoken|phonetoken|amounttoken|numtoken)/g, " ");
  t = t.replace(/[^a-z\s]/g, " ");
  return collapse(t);
}

export function shingles(text, k = 3) {
  const words = fingerprint(text).split(" ").filter(Boolean);
  if (words.length < 6) return new Set(words.length ? [words.join(" ")] : []);
  const out = new Set();
  for (let i = 0; i <= words.length - k; i++) out.add(words.slice(i, i + k).join(" "));
  return out;
}

export function similarity(a, b) {
  const sa = shingles(a), sb = shingles(b);
  if (!sa.size || !sb.size) return fingerprint(a) === fingerprint(b) ? 1 : 0;
  let inter = 0;
  for (const s of sa) if (sb.has(s)) inter++;
  const union = sa.size + sb.size - inter;
  return union ? inter / union : 0;
}
