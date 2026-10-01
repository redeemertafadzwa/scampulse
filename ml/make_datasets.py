"""
Generate four SEPARATE synthetic datasets (never mixed):
  training.csv  - 150+ varied messages used to train/write rules
  test.csv      - 100+ fresh messages, different phrasings, never used to train
  disguised.csv - typos, leetspeak, look-alike links, mixed English/Shona
  legit.csv     - genuine messages that contain scary words (OTP, bank, verify)

All content is synthetic. Every link uses example.invalid. Seeded for
reproducibility. Columns: text, threat_type, risk.
"""
import csv
import os
import random

random.seed(42)
HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "data")
os.makedirs(OUT, exist_ok=True)

BANKS = ["EcoCash", "OneMoney", "CBZ", "ZB Bank", "Steward Bank", "Telecash", "NMB"]
TELCO = ["Econet", "NetOne", "Telecel"]
AMT = ["$5", "$20", "US$50", "RTGS 2000", "$150", "ZWL 50000", "$10"]
LINK = ["http://ecocash-verify.example.invalid/login",
        "http://bit.example.invalid/claim", "www.econet-bonus.example.invalid",
        "http://cbz-secure.example.invalid/auth", "http://parcel-zw.example.invalid/pay"]
NAME = ["Td", "Rue", "Tapiwa", "Chipo", "Farai", "Nyasha"]
CODE = ["4821", "9930", "1127", "7765"]

# ---------- TRAINING templates (phrasing pool A) ----------
TRAIN = {
    "Financial Scam": [
        "Congratulations! You have won {amt} in the {telco} promotion. Send $3 to claim your prize now.",
        "Dear customer, your {bank} account will be credited {amt}. Pay a {amt2} activation fee first.",
        "You received {amt} by mistake on {bank}. Please reverse it back to this number urgently.",
        "FREE {telco} data bundle offer! Reply with your PIN to activate {amt} worth of data.",
        "Job offer: earn {amt} weekly from home. Pay {amt2} registration to start today.",
        "Your parcel is held at customs. Pay {amt2} clearance fee immediately or it is returned.",
        "Hello, I am stuck and need {amt} urgently. Send to this {bank} number, I will repay tomorrow.",
    ],
    "Phishing": [
        "{bank} ALERT: your account is suspended. Verify now at {link} to avoid closure.",
        "Dear client, unusual login detected. Confirm your details here {link} within 24 hours.",
        "Your {bank} wallet is locked. Log in at {link} and enter your PIN to unlock.",
        "Security notice: update your {bank} password immediately via {link}.",
    ],
    "Identity Fraud": [
        "To verify your {bank} account, send a photo of your national ID and a selfie to this number.",
        "KYC update required. Reply with your full ID number and date of birth to keep your account.",
        "We need to confirm your identity. Send your ID card photo and PIN to continue.",
    ],
    "Malicious Link": [
        "Claim your {telco} reward here {link} - offer ends tonight!",
        "Track your delivery now: {link}",
        "You have 1 pending payment. Open {link} to release the funds.",
    ],
    "AI-Enabled Threat": [
        "Voice note from your boss: please buy airtime worth {amt} and send codes, I'm in a meeting.",
        "This is the CEO. I sent a voice note - process an urgent payment of {amt} now, keep it quiet.",
        "Watch this official video from the minister announcing free grants: {link}",
    ],
    "Benign": [
        "Hi, are we still meeting at 3pm today?",
        "Your {telco} airtime balance is {amt}. Thank you.",
        "Reminder: school fees are due on Friday. Please visit the bursar's office.",
        "Thanks for your payment. Your order will be delivered tomorrow.",
        "Your verification code is {code}. Keep it private, we will never ask for it.",
        "You logged in to {bank} successfully. If this was not you, call the branch.",
        "Your {bank} mini-statement: balance {amt}. Thank you for banking with us.",
        "{telco} recharge successful: {amt} airtime added to your line.",
        "School notice: term fees {amt} due Friday, pay at the school office.",
        "Council notice: scheduled power maintenance tomorrow from 8 to 11am.",
        "For your security, update your password from time to time in the official app.",
        "Your card ending 12 was used for {amt} at a store. Contact us if this was not you.",
        "Confirm your email address to switch on notifications in the official app.",
    ],
}

# ---------- TEST templates (phrasing pool B - different wording) ----------
TEST = {
    "Financial Scam": [
        "WINNER! Your number was selected for {amt}. A small {amt2} fee unlocks the payout.",
        "Refund of {amt} pending on {bank}. Confirm by sending {amt2} processing charge.",
        "I mistakenly sent {amt} to you via {bank}. Kindly send it back now, I'm desperate.",
        "Bonus {amt} data on {telco} today only - share your mobile money PIN to receive it.",
        "Work-from-home vacancy pays {amt}/week. Deposit {amt2} for your starter kit.",
    ],
    "Phishing": [
        "Notice from {bank}: verify your identity at {link} or lose access today.",
        "Your online banking is blocked. Reactivate via {link} using your card PIN.",
        "{bank} secure team: click {link} to re-confirm your login before midnight.",
    ],
    "Identity Fraud": [
        "Account audit: upload your ID photo and a selfie holding it to this chat to stay active.",
        "Confirm ownership - reply with ID number, PIN and your mother's maiden name.",
    ],
    "Malicious Link": [
        "Your reward is waiting, tap {link} before it expires.",
        "Parcel undelivered. Reschedule at {link} now.",
    ],
    "AI-Enabled Threat": [
        "Boss here (voice note) - urgently send {amt} airtime codes, cannot call right now.",
        "Official clip of the governor giving out {amt} relief: {link}",
    ],
    "Benign": [
        "Good morning, please send the report when you can.",
        "Your statement for this month is ready at the branch.",
        "ZESA notice: scheduled power maintenance on Sunday 9am-12pm.",
        "Delivery update: your package arrives between 2 and 4pm.",
    ],
}

RISK = {"Financial Scam": "High", "Phishing": "High", "Identity Fraud": "High",
        "Malicious Link": "Medium", "AI-Enabled Threat": "High", "Benign": "Low"}

# ---------- LEGIT: genuine messages that contain scary trigger words ----------
LEGIT = [
    "Your one-time PIN is {code}. Do not share it with anyone. - {bank}",
    "{bank}: your OTP for login is {code}. It expires in 5 minutes.",
    "You have successfully logged in to {bank} online banking.",
    "Your {bank} statement is ready. Log in to the official app to view it.",
    "Payment of {amt} to ZESA was successful. Thank you.",
    "{telco} account verification complete. No further action needed.",
    "Urgent: your school fees balance is {amt}, payable at the bursary by Friday.",
    "Your bank card ending 44 was used for {amt} at a supermarket. Call us if this wasn't you.",
    "Verify your email to finish creating your account on our portal (official app only).",
    "Reminder: update your password regularly for security. Use the official {bank} app.",
    "Your airtime recharge of {amt} on {telco} was successful.",
    "Council notice: water will be disconnected for maintenance tomorrow 8am.",
]


def fill(t):
    return (t.replace("{amt}", random.choice(AMT))
             .replace("{amt2}", random.choice(AMT))
             .replace("{bank}", random.choice(BANKS))
             .replace("{telco}", random.choice(TELCO))
             .replace("{link}", random.choice(LINK))
             .replace("{code}", random.choice(CODE))
             .replace("{name}", random.choice(NAME)))


def build(templates, reps):
    rows = []
    for threat, temps in templates.items():
        for t in temps:
            for _ in range(reps):
                rows.append((fill(t), threat, RISK[threat]))
    return rows


_LEET = {"a": "@", "e": "3", "o": "0", "i": "1", "s": "$"}
SHONA = ["mari", "bhero", "tumira", "iye zvino", "ndapota", "chimbidza"]


def disguise(text):
    out = []
    for w in text.split():
        if len(w) > 3 and random.random() < 0.4:
            w = "".join(_LEET.get(c, c) if random.random() < 0.5 else c for c in w)
        out.append(w)
    s = " ".join(out)
    if random.random() < 0.5:
        s = s.replace("http://", "").replace("example.invalid", "examp1e-inv.co")
    if random.random() < 0.6:
        s += " " + random.choice(SHONA)
    return s


def write(name, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["text", "threat_type", "risk"])
        w.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    train = build(TRAIN, 7)
    test = build(TEST, 6)
    # disguised: scam rows only, transformed (never-cleared check)
    scam_src = [r for r in build(TEST, 3) if r[1] != "Benign"]
    disg = [(disguise(t), th, rk) for (t, th, rk) in scam_src]
    legit = [(fill(t), "Benign", "Low") for t in LEGIT for _ in range(8)]

    random.shuffle(train); random.shuffle(test); random.shuffle(disg); random.shuffle(legit)
    print("training.csv :", write("training.csv", train))
    print("test.csv     :", write("test.csv", test))
    print("disguised.csv:", write("disguised.csv", disg))
    print("legit.csv    :", write("legit.csv", legit))
