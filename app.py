"""
Biotech Lead Generator production Streamlit app.
Connects to the FastAPI backend.
"""

import os
from typing import Any, Optional

import pandas as pd
import plotly.express as px
import streamlit as st

import api_client as api


st.set_page_config(
    page_title="Biotech Lead Generator",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _get_setting(name: str, default: str = "") -> str:
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except Exception:
        return os.getenv(name, default)


def _extract_items(payload: Any) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "data" in payload:
            nested = _extract_items(payload["data"])
            if nested:
                return nested
        for key in ("items", "leads", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def _score_icon(score: Optional[int]) -> str:
    value = score or 0
    if value >= 70:
        return "🟢"
    if value >= 50:
        return "🟡"
    return "🔴"


def _priority_label(score: Optional[int]) -> str:
    value = score or 0
    if value >= 70:
        return "High"
    if value >= 50:
        return "Medium"
    return "Low"


@st.cache_data(ttl=300, show_spinner=False)
def _cached_leads(token: str, min_score: int = 0, search: str = "") -> list:
    try:
        payload = api.get_leads(token, page_size=200, min_score=min_score, search=search)
    except api.APIError as exc:
        if exc.status_code == 401:
            raise
        return []
    except Exception:
        return []
    return _extract_items(payload)


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_billing(token: str) -> dict:
    try:
        payload = api.get_billing_summary(token)
    except api.APIError as exc:
        if exc.status_code == 401:
            raise
        return {"tier": "free", "status": "free", "monthly_limit": 100}
    except Exception:
        return {"tier": "free", "status": "free", "monthly_limit": 100}
    return payload if isinstance(payload, dict) else {"tier": "free", "monthly_limit": 100}


def is_logged_in() -> bool:
    return bool(st.session_state.get("token"))


def get_token() -> Optional[str]:
    return st.session_state.get("token")


def get_user() -> Optional[dict]:
    return st.session_state.get("user")


def logout() -> None:
    for key in ("token", "refresh_token", "user", "page"):
        st.session_state.pop(key, None)
    st.rerun()


def _try_refresh() -> bool:
    refresh_tok = st.session_state.get("refresh_token")
    if not refresh_tok:
        return False
    try:
        data = api.refresh_token(refresh_tok)
    except Exception:
        return False

    st.session_state["token"] = data["access_token"]
    if data.get("refresh_token"):
        st.session_state["refresh_token"] = data["refresh_token"]
    return True


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("### 🧬 Biotech Leads")
        st.markdown("---")

        if is_logged_in():
            user = get_user() or {}
            tier = user.get("subscription_tier", "free").upper()
            tier_color = {
                "FREE": "🔵",
                "PRO": "🟣",
                "TEAM": "🟢",
                "ENTERPRISE": "🟡",
            }.get(tier, "🔵")

            st.markdown(f"**{user.get('full_name', 'User')}**")
            st.caption(f"{tier_color} {tier} plan")
            st.markdown("---")

            pages = {
                "🏠 Dashboard": "dashboard",
                "🔍 Search Leads": "search",
                "📋 My Leads": "leads",
                "⚙️ Pipelines": "pipelines",
                "🎯 Scoring": "scoring",
                "📤 Export": "export",
                "💳 Billing": "billing",
            }
            for label, page_id in pages.items():
                if st.button(label, use_container_width=True, key=f"nav_{page_id}"):
                    st.session_state["page"] = page_id
                    st.rerun()

            st.markdown("---")
            billing = _cached_billing(get_token())
            limit = billing.get("monthly_limit", 100)
            if limit < 999999:
                st.caption(f"Plan limit: {limit:,} leads/mo")
            if billing.get("tier") == "free":
                if st.button("⬆️ Upgrade", use_container_width=True, key="sidebar_upgrade"):
                    st.session_state["page"] = "billing"
                    st.rerun()

            st.markdown("---")
            if st.button("🚪 Sign out", use_container_width=True):
                logout()
        else:
            if st.button("🔑 Sign in", use_container_width=True):
                st.session_state["page"] = "login"
                st.rerun()
            if st.button("📝 Create account", use_container_width=True):
                st.session_state["page"] = "register"
                st.rerun()

        feedback_url = _get_setting(
            "FEEDBACK_FORM_URL",
            "https://forms.gle/C8JUbHWGgM7NoR3V7",
        )
        st.markdown("---")
        st.markdown(f"[📬 Give feedback]({feedback_url})")
        st.markdown("---")
        st.caption("v2.0 · [Docs](https://github.com) · [Status](https://status.biotech-leads.app)")


def page_login() -> None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🧬 Sign in")
        if st.session_state.pop("session_expired", False):
            st.warning("Your session expired. Please sign in again.")

        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter your email and password.")
                return

            with st.spinner("Signing in..."):
                try:
                    data = api.login(email, password)
                except api.APIError as exc:
                    st.error(f"Sign in failed: {exc.detail}")
                    return

            st.session_state["token"] = data["access_token"]
            st.session_state["refresh_token"] = data.get("refresh_token", "")
            st.session_state["user"] = data.get("user", {})
            st.session_state["page"] = "dashboard"
            st.rerun()


def page_register() -> None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🧬 Create account")
        st.caption("Free plan includes 100 leads/month.")

        with st.form("register_form"):
            full_name = st.text_input("Full name")
            email = st.text_input("Email")
            password = st.text_input(
                "Password",
                type="password",
                help="Min 8 chars, one uppercase, one number",
            )
            submitted = st.form_submit_button("Create account", use_container_width=True)

        if submitted:
            if not all([full_name, email, password]):
                st.error("All fields are required.")
                return

            with st.spinner("Creating account..."):
                try:
                    api.register(email, password, full_name)
                except api.APIError as exc:
                    st.error(f"Registration failed: {exc.detail}")
                    return

            st.success("Account created. Please sign in.")
            st.session_state["page"] = "login"
            st.rerun()


def page_dashboard() -> None:
    st.markdown("## 🏠 Dashboard")
    token = get_token()

    billing = _cached_billing(token)
    leads = _cached_leads(token, 0, "")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Leads", len(leads))
    with col2:
        high_priority = sum(1 for lead in leads if (lead.get("propensity_score") or 0) >= 70)
        st.metric("High Priority", high_priority)
    with col3:
        avg_score = (
            sum(lead.get("propensity_score") or 0 for lead in leads) / len(leads)
            if leads
            else 0
        )
        st.metric("Avg Score", f"{avg_score:.1f}")
    with col4:
        limit = billing.get("monthly_limit", 100)
        st.metric("Monthly Limit", f"{limit:,}" if limit < 999999 else "Unlimited")

    try:
        usage_data = api.get_usage_stats(token, days=14)
    except api.APIError as exc:
        if exc.status_code == 401:
            raise
    except Exception:
        usage_data = []
    else:
        rows = _extract_items(usage_data) or usage_data
        if isinstance(rows, list) and rows:
            activity_df = pd.DataFrame(rows)
            if {"date", "leads_created"}.issubset(activity_df.columns):
                st.markdown("---")
                st.markdown("#### Activity - last 14 days")
                fig = px.bar(
                    activity_df,
                    x="date",
                    y="leads_created",
                    labels={"date": "", "leads_created": "Leads"},
                    color_discrete_sequence=["#2563EB"],
                )
                fig.update_layout(
                    height=220,
                    showlegend=False,
                    margin=dict(t=10, b=20, l=0, r=0),
                    plot_bgcolor="white",
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
                )
                st.plotly_chart(fig, use_container_width=True)

    if leads:
        st.markdown("---")
        col_chart, col_tier = st.columns(2)

        with col_chart:
            scores = [lead.get("propensity_score") or 0 for lead in leads]
            fig = px.histogram(
                x=scores,
                nbins=20,
                title="Score Distribution",
                labels={"x": "Propensity Score", "y": "Count"},
                color_discrete_sequence=["#2563EB"],
            )
            fig.update_layout(showlegend=False, height=300, margin=dict(t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

        with col_tier:
            tier_counts = {"High (70+)": 0, "Medium (50-69)": 0, "Low (<50)": 0}
            for lead in leads:
                score = lead.get("propensity_score") or 0
                if score >= 70:
                    tier_counts["High (70+)"] += 1
                elif score >= 50:
                    tier_counts["Medium (50-69)"] += 1
                else:
                    tier_counts["Low (<50)"] += 1
            fig2 = px.pie(
                values=list(tier_counts.values()),
                names=list(tier_counts.keys()),
                title="Priority Breakdown",
                color_discrete_sequence=["#16A34A", "#CA8A04", "#DC2626"],
            )
            fig2.update_layout(height=300, margin=dict(t=40, b=0))
            st.plotly_chart(fig2, use_container_width=True)

    steps_done = {
        "account_created": True,
        "first_search": len(leads) > 0,
        "high_priority_found": any((lead.get("propensity_score") or 0) >= 70 for lead in leads),
        "exported": st.session_state.get("has_exported", False),
    }

    if not all(steps_done.values()):
        st.markdown("---")
        st.markdown("#### 🎯 Getting started")
        cols = st.columns(4)
        checklist = [
            ("✅" if steps_done["account_created"] else "⬜", "Create account"),
            ("✅" if steps_done["first_search"] else "⬜", "Run first search"),
            ("✅" if steps_done["high_priority_found"] else "⬜", "Find a 70+ lead"),
            ("✅" if steps_done["exported"] else "⬜", "Export leads"),
        ]
        for index, (icon, label) in enumerate(checklist):
            with cols[index]:
                st.markdown(f"{icon} {label}")

        if not steps_done["first_search"]:
            if st.button("Run your first search ->", type="primary"):
                st.session_state["page"] = "search"
                st.rerun()

    if billing.get("tier") == "free":
        st.markdown("---")
        st.info(
            "Upgrade to Pro to unlock 1,000 leads/month, five data sources, and AI scoring."
        )
        if st.button("Upgrade to Pro ->", type="primary"):
            st.session_state["page"] = "billing"
            st.rerun()


def page_search() -> None:
    st.markdown("## 🔍 Search Leads")
    token = get_token()

    with st.form("search_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input(
                "Search PubMed",
                placeholder="e.g. DILI 3D in-vitro toxicology organoid",
                help="Searches PubMed for recent authors publishing on this topic",
            )
        with col2:
            max_results = st.selectbox("Results", [25, 50, 100], index=1)
        submitted = st.form_submit_button("Search", use_container_width=True)

    if submitted and query:
        with st.spinner(f"Searching PubMed for '{query}'..."):
            try:
                result = api.search_pubmed(token, query, max_results)
            except api.APIError as exc:
                if exc.status_code == 401:
                    raise
                if api.is_quota_exceeded(exc):
                    st.error("You've reached your monthly lead limit.")
                    st.info("Upgrade to Pro for 1,000 leads/month.")
                    if st.button("Upgrade to Pro - $49/month", type="primary"):
                        st.session_state["page"] = "billing"
                        st.rerun()
                else:
                    st.error(f"Search failed: {exc.detail}")
                return

        leads = result if isinstance(result, list) else result.get("leads", _extract_items(result))
        if not leads:
            st.warning("No leads found. Try different search terms.")
            return

        st.success(f"Found {len(leads)} leads. Saved to My Leads automatically.")
        df = pd.DataFrame(leads)
        if "propensity_score" in df.columns:
            df = df.sort_values("propensity_score", ascending=False)
            df["priority"] = df["propensity_score"].apply(
                lambda score: f"{_score_icon(score)} {_priority_label(score)}"
            )

        display_cols = [
            column
            for column in (
                "priority",
                "name",
                "title",
                "company",
                "location",
                "propensity_score",
            )
            if column in df.columns
        ]

        column_config = {}
        if "propensity_score" in df.columns:
            column_config["propensity_score"] = st.column_config.ProgressColumn(
                "Score",
                min_value=0,
                max_value=100,
                format="%d",
            )

        st.dataframe(
            df[display_cols],
            use_container_width=True,
            height=400,
            column_config=column_config,
        )
        st.download_button(
            "Download these results as CSV",
            data=df[display_cols].to_csv(index=False).encode("utf-8"),
            file_name="search_results.csv",
            mime="text/csv",
        )


def page_leads() -> None:
    st.markdown("## 📋 My Leads")
    token = get_token()

    col_search, col_score, col_sort = st.columns([3, 2, 2])
    with col_search:
        search = st.text_input(
            "Filter",
            placeholder="Name or company...",
            label_visibility="collapsed",
        )
    with col_score:
        min_score = st.slider("Min score", 0, 100, 0, label_visibility="collapsed")
    with col_sort:
        sort_by = st.selectbox(
            "Sort",
            ["Score desc", "Score asc", "Recent"],
            label_visibility="collapsed",
        )

    with st.spinner("Loading leads..."):
        leads = _cached_leads(token, min_score, search)

    if not leads:
        st.info("No leads yet. Use Search to find and add leads from PubMed.")
        if st.button("Go to Search ->"):
            st.session_state["page"] = "search"
            st.rerun()
        return

    if sort_by == "Score desc":
        leads = sorted(leads, key=lambda lead: lead.get("propensity_score") or 0, reverse=True)
    elif sort_by == "Score asc":
        leads = sorted(leads, key=lambda lead: lead.get("propensity_score") or 0)
    else:
        leads = sorted(
            leads,
            key=lambda lead: lead.get("created_at") or lead.get("updated_at") or "",
            reverse=True,
        )

    st.caption(f"{len(leads)} leads")

    for lead in leads:
        score = lead.get("propensity_score") or 0
        name = lead.get("name") or "Unknown"
        title = lead.get("title") or ""
        company = lead.get("company") or ""
        label = f"{_score_icon(score)} {name} - {title} @ {company} - Score: {score}"

        with st.expander(label, expanded=False):
            col_left, col_right = st.columns(2)
            with col_left:
                st.markdown(f"**Location:** {lead.get('location') or '-'}")
                st.markdown(f"**Email:** {lead.get('email') or '-'}")
                if lead.get("linkedin_url"):
                    st.markdown(f"**LinkedIn:** [{lead['linkedin_url']}]({lead['linkedin_url']})")
            with col_right:
                st.markdown(f"**Score:** {score}/100")
                publication_title = lead.get("publication_title") or lead.get("recent_publication")
                if publication_title:
                    year = lead.get("publication_year", "")
                    preview = str(publication_title)[:80]
                    suffix = f" ({year})" if year else ""
                    st.markdown(f"**Publication{suffix}:** {preview}...")
                if lead.get("company_funding"):
                    st.markdown(f"**Funding:** {lead['company_funding']}")


def page_pipelines() -> None:
    st.markdown("## ⚙️ Search Pipelines")
    token = get_token()

    st.markdown(
        "Pipelines run automated PubMed searches on a schedule and add new leads to your list automatically."
    )

    with st.expander("Create new pipeline", expanded=False):
        with st.form("pipeline_form"):
            pipeline_name = st.text_input(
                "Pipeline name",
                placeholder="e.g. Weekly DILI search",
            )
            pipeline_query = st.text_input(
                "PubMed query",
                placeholder="e.g. drug-induced liver injury organoid 3D",
            )
            pipeline_schedule = st.selectbox("Schedule", ["manual", "daily", "weekly"])
            submitted = st.form_submit_button("Create pipeline")

        if submitted:
            if not pipeline_name or not pipeline_query:
                st.warning("Name and query are both required.")
            else:
                with st.spinner("Creating pipeline..."):
                    try:
                        api.create_pipeline(token, pipeline_name, pipeline_query, pipeline_schedule)
                    except api.APIError as exc:
                        if exc.status_code == 401:
                            raise
                        st.error(f"Failed to create pipeline: {exc.detail}")
                    else:
                        st.success(f"Pipeline '{pipeline_name}' created.")
                        st.rerun()

    try:
        pipelines = api.get_pipelines(token)
    except api.APIError as exc:
        if exc.status_code == 401:
            raise
        st.error(f"Could not load pipelines: {exc.detail}")
        return

    if not pipelines:
        st.info("No pipelines yet. Create one above.")
        return

    st.markdown(f"**{len(pipelines)} pipeline{'s' if len(pipelines) != 1 else ''}**")
    status_icon = {"active": "🟢", "paused": "⏸️", "error": "🔴"}

    for index, pipeline in enumerate(pipelines):
        icon = status_icon.get(str(pipeline.get("status", "")).lower(), "⚪")
        schedule = pipeline.get("schedule", "manual")
        last_run = str(pipeline.get("last_run") or "Never")[:10]
        pipeline_id = pipeline.get("id")
        button_key = f"run_{pipeline_id or index}"

        col_info, col_run = st.columns([5, 1])
        with col_info:
            st.markdown(
                f"{icon} **{pipeline.get('name', 'Unnamed')}** - `{schedule}` - Last run: {last_run}"
            )
        with col_run:
            if st.button("Run", key=button_key, use_container_width=True, disabled=not pipeline_id):
                with st.spinner("Starting..."):
                    try:
                        api.run_pipeline(token, str(pipeline_id))
                    except api.APIError as exc:
                        if exc.status_code == 401:
                            raise
                        st.error(f"Failed: {exc.detail}")
                    else:
                        st.success("Pipeline started. Check My Leads in a few minutes.")


def page_scoring() -> None:
    st.markdown("## 🎯 Scoring Configuration")
    token = get_token()

    try:
        config = api.get_score_config(token)
    except api.APIError as exc:
        if exc.status_code == 401:
            raise
        st.error(f"Could not load scoring config: {exc.detail}")
        return

    weights = config.get("weights", {}) if isinstance(config, dict) else {}
    if not weights:
        st.info("No scoring weights found. The default algorithm is active.")
        return

    st.markdown(
        "Adjust the weight of each factor in the 0-100 propensity score. Higher weight means more influence."
    )
    st.markdown("---")

    weight_labels = {
        "seniority_score": "Seniority level",
        "title_relevance": "Title relevance",
        "is_decision_maker": "Decision maker",
        "has_recent_pub": "Has recent publication",
        "pub_count_norm": "Publication count",
        "h_index_norm": "H-index",
        "has_nih_active": "Active NIH grant",
        "nih_award_norm": "NIH award size",
        "has_private_funding": "Private funding",
        "has_email": "Email found",
        "email_confidence": "Email confidence",
        "has_linkedin_verified": "LinkedIn verified",
        "is_conference_speaker": "Conference speaker",
        "institution_type_score": "Institution type",
        "recency_score": "Recency",
    }

    new_weights = {}
    items = list(weights.items())
    split = max(1, (len(items) + 1) // 2)
    col1, col2 = st.columns(2)

    for column, chunk in ((col1, items[:split]), (col2, items[split:])):
        with column:
            for key, value in chunk:
                label = weight_labels.get(key, key.replace("_", " ").title())
                new_weights[key] = st.slider(
                    label,
                    min_value=0.0,
                    max_value=20.0,
                    value=float(value or 0),
                    step=0.5,
                    key=f"weight_{key}",
                )

    st.markdown("---")
    col_save, col_rescore = st.columns(2)

    with col_save:
        if st.button("Save weights", type="primary"):
            with st.spinner("Saving scoring weights..."):
                try:
                    api.update_score_weights(token, new_weights)
                except api.APIError as exc:
                    if exc.status_code == 401:
                        raise
                    st.error(f"Could not save weights: {exc.detail}")
                else:
                    st.success("Scoring weights saved.")

    with col_rescore:
        if st.button("Re-score all my leads", type="primary"):
            with st.spinner("Re-scoring leads with current weights..."):
                try:
                    result = api.rescore_all_leads(token)
                except api.APIError as exc:
                    if exc.status_code == 401:
                        raise
                    st.error(f"Re-scoring failed: {exc.detail}")
                else:
                    count = result.get("updated", result.get("count", "all"))
                    st.success(f"Re-scored {count} leads.")


def page_export() -> None:
    st.markdown("## 📤 Export Leads")
    token = get_token()

    col1, col2 = st.columns(2)
    with col1:
        fmt = st.selectbox("Format", ["csv", "xlsx"], index=0)
    with col2:
        min_score = st.slider("Minimum score to include", 0, 100, 0)

    if st.button("Generate export", type="primary"):
        with st.spinner("Generating export file..."):
            try:
                content = api.export_leads(token, format=fmt, min_score=min_score)
            except api.APIError as exc:
                if exc.status_code == 401:
                    raise
                if api.is_quota_exceeded(exc):
                    st.error("You've reached your monthly lead limit.")
                    st.info("Upgrade to Pro for 1,000 leads/month.")
                    if st.button("Upgrade to Pro - $49/month", type="primary", key="export_upgrade"):
                        st.session_state["page"] = "billing"
                        st.rerun()
                elif exc.status_code == 403:
                    st.error("Export requires a Pro plan or higher.")
                    if st.button("Upgrade to unlock exports", key="export_plan_upgrade"):
                        st.session_state["page"] = "billing"
                        st.rerun()
                else:
                    st.error(f"Export failed: {exc.detail}")
                return

        mime = (
            "text/csv"
            if fmt == "csv"
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.session_state["has_exported"] = True
        st.download_button(
            label=f"Download {fmt.upper()}",
            data=content,
            file_name=f"biotech_leads.{fmt}",
            mime=mime,
        )


def _start_checkout(token: str, price_setting: str) -> None:
    price_id = _get_setting(price_setting)
    if not price_id:
        st.error("Stripe price ID not configured. Contact support.")
        return

    with st.spinner("Opening checkout..."):
        try:
            url = api.create_checkout_session(token, price_id)
        except api.APIError as exc:
            if exc.status_code == 401:
                raise
            st.error(f"Checkout failed: {exc.detail}")
            return

    st.markdown(f"[Click here to complete payment ->]({url})")
    st.info("After payment, return here and refresh to see your updated plan.")


def page_billing() -> None:
    st.markdown("## 💳 Billing & Plans")
    token = get_token()

    try:
        billing = api.get_billing_summary(token)
    except api.APIError as exc:
        if exc.status_code == 401:
            raise
        st.error(f"Could not load billing info: {exc.detail}")
        billing = {"tier": "free", "status": "free", "monthly_limit": 100}

    current_tier = billing.get("tier", "free")
    tier_labels = {
        "free": "🔵 Free",
        "pro": "🟣 Pro",
        "team": "🟢 Team",
        "enterprise": "🟡 Enterprise",
    }
    st.info(f"Current plan: **{tier_labels.get(current_tier, current_tier.title())}**")

    st.markdown("---")
    st.markdown("### Choose a plan")

    col_free, col_pro, col_team = st.columns(3)

    with col_free:
        st.markdown("#### 🔵 Free")
        st.markdown("**$0/month**")
        st.markdown("- 100 leads/month\n- PubMed only\n- CSV export\n- Community support")
        if current_tier == "free":
            st.button("Current plan", disabled=True, key="free_btn", use_container_width=True)

    with col_pro:
        st.markdown("#### 🟣 Pro")
        st.markdown("**$49/month**")
        st.markdown("- 1,000 leads/month\n- 5 data sources\n- AI scoring\n- All exports\n- Email support")
        if current_tier == "pro":
            st.button("Current plan", disabled=True, key="pro_btn", use_container_width=True)
        elif st.button("Upgrade to Pro ->", type="primary", key="pro_btn", use_container_width=True):
            _start_checkout(token, "STRIPE_PRO_PRICE_ID")

    with col_team:
        st.markdown("#### 🟢 Team")
        st.markdown("**$199/month**")
        st.markdown(
            "- 5,000 leads/month\n- Unlimited sources\n- Team collaboration\n- CRM integrations\n- Priority support"
        )
        if current_tier == "team":
            st.button("Current plan", disabled=True, key="team_btn", use_container_width=True)
        elif st.button("Upgrade to Team ->", key="team_btn", use_container_width=True):
            _start_checkout(token, "STRIPE_TEAM_PRICE_ID")

    if current_tier != "free":
        st.markdown("---")
        st.markdown("**Manage billing** - update payment method, view invoices, or cancel.")
        if st.button("Open billing portal", key="open_portal"):
            with st.spinner("Opening billing portal..."):
                try:
                    portal_url = api.create_portal_session(token)
                except api.APIError as exc:
                    if exc.status_code == 401:
                        raise
                    if exc.status_code == 400:
                        st.error("No active subscription found. Subscribe first.")
                    else:
                        st.error(f"Could not open portal: {exc.detail}")
                else:
                    st.markdown(f"[Click here to manage your subscription ->]({portal_url})")
                    st.caption("Opens Stripe's secure billing portal.")

    if os.getenv("ENV", "prod") == "dev":
        st.markdown("---")
        st.caption("Test mode - use card `4242 4242 4242 4242`, any future expiry, any CVC.")


def page_landing() -> None:
    st.markdown(
        """
# 🧬 Biotech Lead Generator

**AI-powered lead generation for biotech and pharma business development.**

Find researchers and decision-makers interested in 3D in-vitro models,
drug discovery tools, and toxicology research - automatically scored and enriched.

---

### How it works
1. Search PubMed for authors publishing on relevant topics
2. Score leads 0-100 based on role, publications, funding, and location
3. Export a prioritized prospect list to CSV or Excel

---
"""
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Data sources", "5+")
    with col2:
        st.metric("Scoring criteria", "15")
    with col3:
        st.metric("Free leads/month", "100")

    st.markdown("---")
    col_a, col_b, _ = st.columns([1, 1, 2])
    with col_a:
        if st.button("Get started free", type="primary", use_container_width=True):
            st.session_state["page"] = "register"
            st.rerun()
    with col_b:
        if st.button("Sign in", use_container_width=True):
            st.session_state["page"] = "login"
            st.rerun()


def main() -> None:
    render_sidebar()

    page = st.session_state.get("page", "landing" if not is_logged_in() else "dashboard")
    protected = {
        "dashboard",
        "search",
        "leads",
        "pipelines",
        "scoring",
        "export",
        "billing",
    }

    if page in protected and not is_logged_in():
        st.session_state["page"] = "login"
        page = "login"

    try:
        if page == "landing":
            page_landing()
        elif page == "login":
            page_login()
        elif page == "register":
            page_register()
        elif page == "dashboard":
            page_dashboard()
        elif page == "search":
            page_search()
        elif page == "leads":
            page_leads()
        elif page == "pipelines":
            page_pipelines()
        elif page == "scoring":
            page_scoring()
        elif page == "export":
            page_export()
        elif page == "billing":
            page_billing()
        else:
            page_dashboard()
    except api.APIError as exc:
        if exc.status_code == 401:
            if _try_refresh():
                st.rerun()
            else:
                for key in ("token", "refresh_token", "user"):
                    st.session_state.pop(key, None)
                st.session_state["page"] = "login"
                st.session_state["session_expired"] = True
                st.rerun()
        else:
            st.error(f"Unexpected API error: {exc.detail}")


if __name__ == "__main__":
    main()
