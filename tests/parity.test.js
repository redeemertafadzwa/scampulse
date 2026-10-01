// Node parity test: run the same inputs through normalise.js and compare to
// the Python outputs in parity_cases.json. Exit non-zero on any mismatch.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { redact, normalise, fingerprint } from "../core/static/js/normalise.js";

const here = dirname(fileURLToPath(import.meta.url));
const cases = JSON.parse(readFileSync(join(here, "parity_cases.json"), "utf-8"));

let fails = 0;
for (const c of cases) {
  for (const [fn, name] of [[redact, "redact"], [normalise, "normalise"], [fingerprint, "fingerprint"]]) {
    const got = fn(c.in);
    if (got !== c[name]) {
      fails++;
      if (fails <= 10) {
        console.log(`MISMATCH ${name}\n  in : ${JSON.stringify(c.in)}\n  py : ${JSON.stringify(c[name])}\n  js : ${JSON.stringify(got)}`);
      }
    }
  }
}
console.log(`\n${cases.length} cases x3 funcs = ${cases.length * 3} checks | ${fails} mismatches`);
if (fails) { console.error("PARITY FAILED"); process.exit(1); }
console.log("PARITY OK");
