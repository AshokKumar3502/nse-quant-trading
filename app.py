import os
from dotenv import load_dotenv

load_dotenv()

from pathlib import Path
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from supabase import create_client, Client

st.set_page_config(
    page_title="NSE Quantitative Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "output"

REPORTS = {
    "All Scores": "all_scores.csv",
    "Next-Day Candidates": "next_day_candidates.csv",
    "Swing Candidates": "swing_candidates.csv",
    "Historical Setup Stats": "historical_setup_stats.csv",
    "Position Selection": "position_selection.csv",
    "High-Priority Overlap": "high_priority_overlap.csv",
}

def secret(name, default=None):
    try:
        value = st.secrets.get(name)
        if value is not None:
            return value
    except Exception:
        pass
    return os.getenv(name, default)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = (
    os.getenv("SUPABASE_ANON_KEY")
    or os.getenv("SUPABASE_KEY")
)


PAYMENT_API_URL = secret(
    "PAYMENT_API_URL",
    "https://nse-quant-trading.onrender.com",
)
RAZORPAY_KEY_ID = secret("RAZORPAY_KEY_ID")
RAZORPAY_PLAN_ID = secret(
    "RAZORPAY_PLAN_ID",
    "plan_TVJ8M57jAt8Ddj",
)

supabase = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    except Exception:
        supabase = None

st.markdown(
    """
    <style>
    .block-container{max-width:1900px;padding:1.2rem 2rem 3rem}
    .paid-box{border:1px solid rgba(128,128,128,.30);border-radius:14px;padding:22px;margin:10px 0}
    </style>
    """,
    unsafe_allow_html=True,
)

for key, value in {
    "analysis_symbol": None,
    "logged_in": False,
    "user": None,
    "access_token": None,
    "subscription": None,
    "checkout_subscription_id": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

def clear_login():
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.subscription = None
    st.session_state.analysis_symbol = None
    st.session_state.checkout_subscription_id = None

def login_user(email, password):
    if supabase is None:
        return False, "Supabase is not configured in Streamlit Secrets."
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        session = getattr(response, "session", None)
        user = getattr(response, "user", None)
        if not session or not user:
            return False, "Login failed. Check email and password."
        st.session_state.logged_in = True
        st.session_state.user = user
        st.session_state.access_token = session.access_token
        return True, None
    except Exception as exc:
        return False, str(exc)

def register_user(email, password):
    if supabase is None:
        return False, "Supabase is not configured in Streamlit Secrets."
    try:
        response = supabase.auth.sign_up(
            {"email": email, "password": password}
        )
        user = getattr(response, "user", None)
        session = getattr(response, "session", None)
        if not user:
            return False, "Registration failed."
        if session:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.session_state.access_token = session.access_token
            return True, None
        return True, "Account created. Check your email to confirm your account."
    except Exception as exc:
        return False, str(exc)

def load_subscription():
    if supabase is None or not st.session_state.logged_in:
        return None
    try:
        user = st.session_state.user
        user_id = getattr(user, "id", None)
        if not user_id:
            return None
        client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        # Keep the authenticated user's JWT for RLS.
        client.auth.set_session(st.session_state.access_token, "")
        response = (
            client.table("subscriptions")
            .select(
                "status,plan_name,amount,razorpay_subscription_id,"
                "start_date,end_date"
            )
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception:
        return None

def subscription_is_active(subscription):
    return bool(
        subscription
        and str(subscription.get("status", "")).lower()
        in {"active", "authenticated"}
    )

# ------------------------- LOGIN -------------------------

if not st.session_state.logged_in:
    st.title("📈 NSE Quantitative Trading Dashboard")
    st.caption("Login required to access the stock research dashboard.")

    if supabase is None:
        st.error(
            "Supabase authentication is not configured. "
            "Add SUPABASE_URL and SUPABASE_ANON_KEY to Streamlit Secrets."
        )
        st.stop()

    login_tab, register_tab = st.tabs(["🔐 Login", "📝 Create Account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            if not email or not password:
                st.error("Enter both email and password.")
            else:
                ok, message = login_user(email.strip(), password)
                if ok:
                    if message:
                        st.info(message)
                    st.rerun()
                else:
                    st.error(message)

    with register_tab:
        with st.form("register_form"):
            new_email = st.text_input("Email", placeholder="you@example.com")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            register = st.form_submit_button(
                "Create Account",
                use_container_width=True,
            )
        if register:
            if not new_email or not new_password:
                st.error("Enter email and password.")
            elif len(new_password) < 8:
                st.error("Password must be at least 8 characters.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                ok, message = register_user(
                    new_email.strip(), new_password
                )
                if ok:
                    if message:
                        st.success(message)
                    if st.session_state.logged_in:
                        st.rerun()
                else:
                    st.error(message)
    st.stop()

# ------------------------- SIDEBAR -------------------------

with st.sidebar:
    st.success(f"Logged in\n{getattr(st.session_state.user, 'email', 'User')}")
    if st.button("🚪 Logout", use_container_width=True):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        clear_login()
        st.rerun()

# ------------------------- SUBSCRIPTION -------------------------

subscription = load_subscription()
st.session_state.subscription = subscription

if not subscription_is_active(subscription):
    st.title("🔐 NSE Quant Trading")
    st.markdown(
        """
        <div class="paid-box">
        <h2>Premium Stock Research</h2>
        <p>
        Access intraday candidates, swing candidates, historical setup
        validation, position selection, high-priority overlap and
        individual stock analysis.
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.metric("Monthly Subscription", "₹100 / month")

    if subscription:
        st.info(
            f"Current subscription status: **{subscription.get('status', 'unknown')}**"
        )
    else:
        st.info("No active subscription found for this account.")

    if not RAZORPAY_KEY_ID:
        st.warning(
            "Razorpay checkout is not configured yet. "
            "Add RAZORPAY_KEY_ID to Streamlit Secrets."
        )
        st.stop()

    if st.button(
        "💳 Subscribe for ₹100 / month",
        type="primary",
        use_container_width=True,
    ):
       

        try:
            response = requests.post(
                f"{PAYMENT_API_URL.rstrip('/')}/create-subscription",
                headers={
                    "Authorization": f"Bearer {st.session_state.access_token}",
                    "Content-Type": "application/json",
                },
                json={},
                timeout=30,
            )
            if response.status_code != 200:
                try:
                    detail = response.json()
                except Exception:
                    detail = response.text
                st.error(f"Unable to create subscription: {detail}")
            else:
                data = response.json()
                sid = data.get("subscription_id")
                if sid:
                    st.session_state.checkout_subscription_id = sid
                else:
                    st.error("Payment API did not return a subscription ID.")
        except Exception as exc:
            st.error(f"Payment service error: {exc}")

    sid = st.session_state.checkout_subscription_id
    if sid:
        checkout_html = f"""
        <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
        <button id="rzp-button" style="
            width:100%;padding:14px;border:0;border-radius:8px;
            cursor:pointer;font-size:16px;font-weight:600;">
            Continue to Razorpay Checkout
        </button>
        <script>
        document.getElementById("rzp-button").onclick = function(e) {{
            var options = {{
                "key": "{RAZORPAY_KEY_ID}",
                "subscription_id": "{sid}",
                "name": "NSE Quant Trading",
                "description": "₹100 monthly subscription",
                "handler": function(response) {{
                    document.getElementById("rzp-button").innerText =
                        "Payment submitted — refresh this page after payment.";
                }},
                "theme": {{"color": "#3399cc"}}
            }};
            var rzp = new Razorpay(options);
            rzp.on("payment.failed", function(response) {{
                alert("Payment failed: " + response.error.description);
            }});
            rzp.open();
            e.preventDefault();
        }};
        </script>
        """
        st.components.v1.html(
    checkout_html,
    height=750,
    scrolling=True,
)
        st.info(
            "After payment, Razorpay sends the verified webhook to the "
            "payment backend. Refresh this page after successful payment."
        )

    st.markdown("---")
    st.caption(
        "Access is controlled by verified subscription status. "
        "The browser cannot activate a subscription itself."
    )
    st.stop()

# ------------------------- DASHBOARD -------------------------

st.title("📈 NSE Quantitative Trading Dashboard")
st.caption("Exact scanner reports • no mandatory filters • six-report research view")
st.success(
    f"Premium access active — "
    f"{subscription.get('plan_name', 'Monthly Plan')}"
)

@st.cache_data(ttl=300, show_spinner=False)
def load_csv(name):
    p = OUTPUT / name
    if not p.exists():
        return pd.DataFrame()
    try:
        d = pd.read_csv(p, low_memory=False)
        d.columns = [str(c).strip().replace("\n", " ") for c in d.columns]
        return d
    except Exception as e:
        return pd.DataFrame({"_READ_ERROR_": [str(e)]})

def symbol_col(df):
    if df.empty:
        return None
    for c in [
        "SYMBOL", "Symbol", "symbol", "STOCK", "Stock",
        "TICKER", "Ticker", "SECURITY", "Security"
    ]:
        if c in df.columns:
            return c
    for c in df.columns:
        u = str(c).upper()
        if "SYMBOL" in u or "TICKER" in u:
            return c
    return None

def fmt(v):
    if pd.isna(v):
        return "—"
    if isinstance(v, float):
        return f"{v:,.4f}".rstrip("0").rstrip(".")
    return str(v)

reports = {k: load_csv(v) for k, v in REPORTS.items()}

mods = []
for filename in REPORTS.values():
    p = OUTPUT / filename
    if p.exists():
        mods.append(datetime.fromtimestamp(p.stat().st_mtime))
if mods:
    st.info(f"Latest report update: {max(mods):%d-%b-%Y %H:%M:%S}")

all_df = reports["All Scores"]
next_df = reports["Next-Day Candidates"]
swing_df = reports["Swing Candidates"]
pos_df = reports["Position Selection"]
overlap_df = reports["High-Priority Overlap"]

c = st.columns(6)
metrics = [
    ("All Scores", all_df),
    ("Next-Day", next_df),
    ("Swing", swing_df),
    ("Position", pos_df),
    ("High Priority", overlap_df),
    ("Reports Loaded", None),
]
for box, (title, df) in zip(c, metrics):
    value = (
        f"{sum(not x.empty for x in reports.values())}/6"
        if df is None else f"{len(df):,}"
    )
    box.metric(title, value)

st.markdown("## 📊 Generated Reports")
tabs = st.tabs(list(REPORTS))

for tab, (name, filename) in zip(tabs, REPORTS.items()):
    with tab:
        df = reports[name]
        if df.empty:
            st.warning(
                f"{name}: file missing or empty. Expected output/{filename}"
            )
            continue

        st.write(f"**Rows:** {len(df):,}  |  **Columns:** {len(df.columns):,}")

        q = st.text_input(
            "Search (optional)",
            key="q_" + name,
            placeholder="Leave blank to show the complete report",
        )
        view = df
        if q.strip():
            mask = (
                view.astype(str)
                .apply(
                    lambda s: s.str.contains(
                        q.strip(), case=False, na=False
                    )
                )
                .any(axis=1)
            )
            view = view.loc[mask]

        try:
            ev = st.dataframe(
                view,
                hide_index=True,
                width="stretch",
                height=650,
                on_select="rerun",
                selection_mode="single-row",
            )
            rows = getattr(ev.selection, "rows", []) if ev else []
        except TypeError:
            st.dataframe(
                view,
                hide_index=True,
                width="stretch",
                height=650,
            )
            rows = []

        if rows:
            sc = symbol_col(view)
            if sc:
                sym = str(view.iloc[rows[0]][sc])
                st.session_state.analysis_symbol = sym
                st.success(
                    f"Selected {sym}. Use the Stock Analysis section below."
                )

sym = st.session_state.analysis_symbol

if sym:
    st.markdown("---")
    st.header(f"🔬 Stock Analysis — {sym}")

    if st.button("Close Stock Analysis"):
        st.session_state.analysis_symbol = None
        st.rerun()

    found = []
    for name, df in reports.items():
        sc = symbol_col(df)
        if sc:
            m = df[
                df[sc].astype(str).str.upper().eq(sym.upper())
            ]
            if not m.empty:
                found.append((name, m))

    if not found:
        st.warning("No matching rows found in the six reports.")
    else:
        for name, m in found:
            st.subheader(name)
            st.dataframe(
                m,
                hide_index=True,
                width="stretch",
                height=min(500, 120 + 35 * len(m)),
            )

        common = {}
        keys = [
            "BIAS", "CONFIDENCE", "SCORE", "NEXT_DAY_SCORE",
            "SWING_SCORE", "HISTORICAL_SCORE", "POSITION_SCORE",
            "FACTOR_RATIO", "ALIGNED_FACTORS", "CMP",
            "EXPECTED_RANGE_LOW_PCT", "EXPECTED_RANGE_HIGH_PCT",
            "INVALIDATION", "PRIMARY_DRIVER", "CONFLICTING_SIGNAL",
            "TRADE_MODE", "IN_NEXT_DAY", "IN_SWING", "OVERLAP",
        ]
        for _, m in found:
            r = m.iloc[0]
            for k in keys:
                if k in r.index and k not in common:
                    common[k] = r[k]

        if common:
            st.subheader("Key fields")
            cc = st.columns(4)
            for i, (k, v) in enumerate(common.items()):
                cc[i % 4].metric(k.replace("_", " "), fmt(v))

st.markdown("---")
st.caption(
    "Research/ranking tool only. Scores are not guaranteed returns; "
    "leverage magnifies gains and losses."
)
