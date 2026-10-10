"""Veridex engine: rule-based claim -> evidence -> verification -> safe decision.
Explainable by design: every point of risk traces to a named indicator."""
import re
from urllib.parse import urlparse

# name: (weight, stage, regex, why it matters)
TACTICS = {
    "Authority impersonation": (14, 0, r"\b(bank|fraud department|police|customs|income tax|irs|government|support team|security team|ceo|manager|courier|paypal|amazon|hr)\b",
        "Claims to be an institution you trust, so you lower your guard."),
    "Fear / threat": (18, 1, r"\b(suspend\w*|frozen|freeze|blocked|closed|arrest\w*|legal action|penalty|compromised|hacked|flagged|fail(ure)? to)\b",
        "Threatens a loss to push you to react instead of think."),
    "Urgency": (18, 2, r"\b(urgent|immediately|within \d+ ?(minutes?|mins?|hours?)|right now|today only|last chance|asap|expires?)\b",
        "A short deadline removes time to verify."),
    "Secrecy / isolation": (16, 3, r"\b(do not (tell|contact|inform|share this)|don'?t (tell|contact)|keep (this )?(secret|confidential)|tell no one|nobody)\b|\bdo not contact anyone\b",
        "Cuts you off from people who could spot the scam."),
    "Credential / OTP request": (22, 4, r"\b(otp|pin|password|cvv|one[- ]time|verification code|login details|aadhaar|card number)\b",
        "Real organisations never ask for these by message or call."),
    "Financial action": (22, 5, r"(₹|rs\.?|inr|\$|usd)\s?\d[\d,]*|\b(transfer|send|pay|deposit|gift cards?|upi|wire|bitcoin|crypto)\b",
        "Asks for money or payment to a destination you didn't choose."),
    "Reward / lure": (12, 1, r"\b(won|winner|prize|lottery|free|bonus|refund|cashback|guaranteed returns?|work from home|earn \d+)\b",
        "Offers something too good to be true to lower suspicion."),
}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "rb.gy", "shorturl.at"}
BAD_TLDS = (".xyz", ".top", ".click", ".icu", ".work", ".zip", ".support", ".live")

VERIFY = {
    "Authority impersonation": ["Don't trust the caller ID or sender name alone; both can be faked.",
        "Hang up or close the chat, then open the official app or type the website yourself.",
        "Call the number printed on your card or the organisation's official site."],
    "Fear / threat": ["Check your account or status inside the official app, not through this message.",
        "Ask: has anything actually happened? Threats with no proof are a warning sign."],
    "Urgency": ["Treat any deadline as unconfirmed until the organisation confirms it independently.",
        "Take 10 minutes. Real problems survive a pause."],
    "Secrecy / isolation": ["Show this message to someone you trust before doing anything.",
        "Legitimate organisations never tell you to hide a request from family."],
    "Credential / OTP request": ["Never share OTPs, PINs, CVV or passwords, even with 'staff'.",
        "If you already shared one, contact your bank through its official line now."],
    "Financial action": ["Do not pay into an account supplied by the message.",
        "Confirm the payee and amount with the organisation through an official channel first."],
    "Reward / lure": ["Search the offer on the official website. If it isn't there, treat it as unconfirmed.",
        "You can't win a contest you never entered."],
}

def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 3]

def analyze_url(url):
    flags = []
    u = urlparse(url if "//" in url else "http://" + url)
    host = (u.hostname or "").lower()
    if u.scheme != "https": flags.append("Not using HTTPS")
    if re.fullmatch(r"[\d.]+", host): flags.append("Uses a raw IP address instead of a name")
    if host in SHORTENERS: flags.append("Shortened link hides the real destination")
    if host.endswith(BAD_TLDS): flags.append("Uses a domain ending often seen in throwaway sites")
    if host.startswith("xn--") or "xn--" in host: flags.append("Look-alike (punycode) characters in the domain")
    if host.count("-") >= 2: flags.append("Many hyphens in the domain name")
    if host.count(".") >= 3: flags.append("Unusually many subdomains")
    if "@" in url: flags.append("Contains '@', which can disguise the real host")
    if re.search(r"(login|verify|secure|update|account)", host): flags.append("Security words in the domain name (common in fake sites)")
    return host, flags

def analyze(text):
    t = text.strip()
    hits = {}
    for name, (w, stage, rx, why) in TACTICS.items():
        m = re.findall(rx, t, flags=re.I)
        if m: hits[name] = (w, stage, why)
    # Safe-notice guard: "do not share your OTP" is a warning, not a request.
    safe_notice = re.search(r"\b(do not share|don'?t share|never (ask|share|call)|will never ask)\b", t, flags=re.I)
    if safe_notice and not any(k in hits for k in ("Urgency", "Fear / threat")) and not re.search(r"(https?://|www\.)", t, flags=re.I):
        for k in ("Secrecy / isolation", "Credential / OTP request", "Authority impersonation"):
            hits.pop(k, None)
    urls = re.findall(r"(?:https?://|www\.)\S+|\b[\w-]+\.(?:com|net|org|in|xyz|top|click|icu|co)\S*", t, flags=re.I)
    url_results = [(u,) + analyze_url(u) for u in dict.fromkeys(urls)]

    claims = []
    for s in _sentences(t):
        tags = [n for n, (_, _, rx, _) in TACTICS.items() if re.search(rx, s, flags=re.I)]
        if tags:
            claims.append({"claim": s, "tactics": tags, "status": "UNVERIFIED",
                           "evidence": "No independent evidence provided in the message."})
    # score: explainable sum of named factors
    factors = [(n, h[0], h[2]) for n, h in hits.items()]
    n_unv = len(claims)
    if n_unv >= 3: factors.append(("Several unverified claims", 8, "Multiple claims, none backed by independent evidence."))
    for u, host, fl in url_results:
        if fl: factors.append((f"Suspicious link ({host})", min(6 * len(fl), 15), "; ".join(fl)))
    score = min(100, sum(f[1] for f in factors))
    if score < 25: level, color = "LOW RISK", "#9ABC04"
    elif score < 50: level, color = "MODERATE RISK", "#FFCA26"
    elif score < 75: level, color = "ELEVATED RISK", "#F86015"
    else: level, color = "HIGH RISK", "#D42518"
    stages = sorted(hits.items(), key=lambda kv: kv[1][1])
    pattern = [n for n, _ in stages]
    summary = ("This interaction contains multiple high-risk indicators and could not be independently verified."
               if score >= 50 else "Some risk indicators were found. Verify independently before acting."
               if score >= 25 else "Few risk indicators were found, but this is not a guarantee. Stay cautious with money or personal data.")
    checklist = ["Sender identity verified independently", "Official channel confirmed (app or website you opened yourself)",
                 "The claimed issue confirmed independently"]
    if "Financial action" in hits: checklist += ["Payment destination verified with the organisation", "Amount confirmed independently"]
    if "Urgency" in hits: checklist.append("Deadline confirmed independently")
    return dict(score=score, level=level, color=color, summary=summary, hits=hits, claims=claims,
                factors=factors, pattern=pattern, urls=url_results, checklist=checklist,
                verify={n: VERIFY[n] for n in hits}, unverified=n_unv)

DO = ["Contact the organisation through its official app or website", "Ask a trusted person for a second opinion",
      "Take screenshots, then report it (in India: cybercrime.gov.in or call 1930)", "Block the sender after reporting"]
DONT = ["Click links in the message", "Share OTPs, PINs or passwords", "Transfer money under pressure",
        "Install apps the sender suggests", "Keep chatting with the sender"]

# ---- ML component (optional: used only if train.py has produced model.joblib) ----
import os
_MODEL = None
def model_prob(text):
    """Returns (probability, band) from the trained classifier, or None if no model file yet."""
    global _MODEL
    path = os.path.join(os.path.dirname(__file__), "model.joblib")
    if _MODEL is None and os.path.exists(path):
        import joblib; _MODEL = joblib.load(path)
    if _MODEL is None: return None
    p = float(_MODEL.predict_proba([text])[0][1])
    band = "Safe" if p < 0.3 else "Suspicious" if p < 0.7 else "High-risk scam"
    return p, band
