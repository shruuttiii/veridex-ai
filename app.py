import streamlit as st, plotly.graph_objects as go
from engine import analyze, model_prob, DO, DONT

SUN, CREAM, CARROT, FOREST, TOMATO, KIWI = "#FFCA26", "#F3E8CC", "#F86015", "#19532B", "#D42518", "#9ABC04"
DEMO = ("URGENT: Your bank account has been flagged for suspicious activity. You have 30 minutes to transfer ₹50,000 "
        "to the secure account below. Failure to do so will result in immediate account suspension. Do not contact anyone about this matter.")

st.set_page_config(page_title="Veridex AI", page_icon="🛡️", layout="wide")
st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@600;800&family=DM+Sans:wght@400;500;700&display=swap');
html, body, [class*="css"], .stMarkdown {{ font-family:'DM Sans',sans-serif; color:{FOREST}; }}
h1,h2,h3,.disp {{ font-family:'Baloo 2',cursive !important; color:{FOREST}; letter-spacing:.2px; }}
.block-container {{ max-width:1080px; padding-top:1.5rem; }}
header[data-testid="stHeader"] {{ background:transparent; }}
.hero {{ background:{FOREST}; border-radius:36px; padding:44px 48px; margin-bottom:22px; }}
.hero .disp {{ font-size:3.4rem; font-weight:800; color:{SUN}; line-height:1; margin:0; }}
.hero .tag {{ font-family:'Baloo 2'; font-size:1.7rem; color:{CREAM}; margin-top:10px; }}
.hero .sub {{ color:{CREAM}; opacity:.85; margin-top:8px; max-width:560px; }}
.tile {{ border-radius:28px; padding:20px 22px; min-height:116px; }}
.tile .n {{ font-family:'Baloo 2'; font-size:2.6rem; font-weight:800; line-height:1.05; }}
.tile .l {{ font-weight:700; font-size:.95rem; }}
.card {{ background:#fff; border-radius:26px; padding:20px 24px; margin-bottom:14px; }}
.chip {{ display:inline-block; border-radius:999px; padding:5px 14px; margin:3px 4px 3px 0; font-weight:700; font-size:.88rem; }}
.arrow {{ color:{CARROT}; font-weight:800; margin:0 2px; }}
.pill {{ border-radius:999px; padding:3px 12px; font-weight:700; font-size:.8rem; background:{SUN}; color:{FOREST}; }}
.plus {{ color:{TOMATO}; font-weight:800; }}
textarea {{ border-radius:20px !important; }}
.stButton>button {{ background:{CARROT}; color:#fff; border:0; border-radius:999px; padding:.6rem 2rem; font-weight:700; font-family:'Baloo 2'; font-size:1.1rem; }}
.stButton>button:hover {{ background:{TOMATO}; color:#fff; }}
.stButton>button:focus-visible {{ outline:3px solid {SUN}; }}
</style>""", unsafe_allow_html=True)

st.markdown("""<div class="hero"><p class="disp">VERIDEX AI</p>
<div class="tag">Verify the claim. Before you trust the story.</div>
<div class="sub">Paste a message, email, job offer or link. Veridex breaks it into claims, shows how you're being pushed, and tells you what to check before you act.</div></div>""", unsafe_allow_html=True)

if "text" not in st.session_state: st.session_state.text = ""
c1, c2 = st.columns([5, 1.4])
with c2:
    if st.button("Try a demo", key="demo"): st.session_state.text = DEMO
with c1:
    st.caption("Your text is analysed in this session and not stored.")
text = st.text_area("Suspicious content or URL", key="text", height=150, label_visibility="collapsed",
                    placeholder="Paste the suspicious message, email, payment request or link here")
go_btn = st.button("Analyze")

if go_btn and not text.strip():
    st.warning("Paste a message or link first, then select Analyze.")
elif go_btn:
    r = analyze(text)
    col = r["color"]; dark = col in (TOMATO, CARROT)
    fg = "#fff" if dark else FOREST
    tiles = [(r["level"], "Risk level", col, fg), (f'{r["score"]}/100', "Risk score", FOREST, SUN),
             (len(r["claims"]), "Claims detected", SUN, FOREST), (len(r["hits"]), "Manipulation tactics", KIWI, FOREST)]
    for c, (n, l, bg, f) in zip(st.columns(4), tiles):
        c.markdown(f'<div class="tile" style="background:{bg};color:{f}"><div class="n" style="font-size:{"1.6rem" if isinstance(n,str) and "RISK" in n else "2.6rem"}">{n}</div><div class="l">{l}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="card" style="margin-top:16px;border-left:12px solid {col}"><b>{r["summary"]}</b></div>', unsafe_allow_html=True)

    mp = model_prob(text)
    if mp:
        st.markdown(f'<div class="card"><b>ML model view:</b> {mp[1]} ({mp[0]:.0%} scam-likelihood). Trained on a public dataset; this is a second opinion next to the rule-based score, not a verdict.</div>', unsafe_allow_html=True)

    g1, g2 = st.columns([1, 1.4])
    with g1:
        fig = go.Figure(go.Indicator(mode="gauge+number", value=r["score"], number={"font": {"color": FOREST, "family": "Baloo 2"}},
            gauge={"axis": {"range": [0, 100], "tickcolor": FOREST}, "bar": {"color": FOREST, "thickness": .25},
                   "steps": [{"range": [0, 25], "color": KIWI}, {"range": [25, 50], "color": SUN},
                             {"range": [50, 75], "color": CARROT}, {"range": [75, 100], "color": TOMATO}]}))
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=0), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        st.subheader("Why this score")
        if r["factors"]:
            for n, w, why in r["factors"]:
                st.markdown(f'<span class="plus">+{w}</span> **{n}**: {why}', unsafe_allow_html=True)
        else: st.write("No risk indicators matched.")

    st.subheader("How you're being pushed")
    if r["pattern"]:
        chips = '<span class="arrow">→</span>'.join(f'<span class="chip" style="background:{[FOREST,TOMATO,CARROT,SUN,KIWI,TOMATO][i%6]};color:{"#fff" if i%6 in (0,1,2,5) else FOREST}">{p}</span>' for i, p in enumerate(r["pattern"]))
        st.markdown(f'<div class="card">{chips}</div>', unsafe_allow_html=True)

    st.subheader("Claims and evidence")
    if not r["claims"]: st.write("No notable claims found.")
    for i, c in enumerate(r["claims"], 1):
        tags = " ".join(f'<span class="chip" style="background:{CREAM}">{t}</span>' for t in c["tactics"])
        st.markdown(f'<div class="card"><span class="pill">⚠️ {c["status"]}</span> &nbsp;<b>Claim {i}:</b> “{c["claim"]}”<br><small>{c["evidence"]}</small><br>{tags}</div>', unsafe_allow_html=True)

    if r["urls"]:
        st.subheader("Link check")
        for u, host, fl in r["urls"]:
            st.markdown(f'<div class="card"><b>{u}</b><br>' + ("<br>".join("• " + f for f in fl) if fl else "No rule-based red flags. This does not prove the link is safe.") + "</div>", unsafe_allow_html=True)

    st.subheader("What should you verify?")
    st.caption("Always use an independent channel. Never use contact details from the message itself.")
    for name, steps in r["verify"].items():
        st.markdown(f'<div class="card"><b>{name}</b><br>' + "<br>".join("• " + s for s in steps) + "</div>", unsafe_allow_html=True)
    st.markdown("**What would need to be true for this to be legitimate?**")
    done = [st.checkbox(x, key=f"chk{i}") for i, x in enumerate(r["checklist"])]
    if not all(done): st.error("If any of these can't be confirmed independently, do not act.")
    else: st.success("Everything confirmed through channels you chose yourself. Proceed with care.")

    st.subheader("What should you do now?")
    d1, d2 = st.columns(2)
    d1.markdown(f'<div class="card" style="background:{KIWI}"><b>Do</b><br>' + "<br>".join("✓ " + x for x in DO) + "</div>", unsafe_allow_html=True)
    d2.markdown(f'<div class="card" style="background:{TOMATO};color:#fff"><b>Don\'t</b><br>' + "<br>".join("✗ " + x for x in DONT) + "</div>", unsafe_allow_html=True)
    st.caption("Veridex is a decision-support tool. It cannot confirm that something is or isn't a scam.")
