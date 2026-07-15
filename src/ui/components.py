"""Reusable Streamlit components and layout helpers."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from math import ceil
from typing import Generic, Optional, Sequence, TypeVar

import streamlit as st

from src.config import Settings, redacted_database_url
from src.ui.formatting import format_score


T = TypeVar("T")


GLOBAL_STYLES = """
<style>
    :root {
        --flowsift-ink: #18181b;
        --flowsift-muted: #71717a;
        --flowsift-line: #e4e4e7;
        --flowsift-line-strong: #d4d4d8;
        --flowsift-panel: #ffffff;
        --flowsift-canvas: #f7f7f5;
        --flowsift-soft: #f4f4f5;
        --flowsift-accent: #6d5dfb;
        --flowsift-accent-hover: #5b4be7;
        --flowsift-accent-soft: #f0eeff;
        --flowsift-green: #0f7a5d;
        --flowsift-green-soft: #e9f7f1;
        --flowsift-amber: #a56212;
        --flowsift-amber-soft: #fff6df;
        --flowsift-red: #b73333;
        --flowsift-red-soft: #fff0f0;
    }
    html, body, [class*="css"] {
        font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
            "Segoe UI", sans-serif;
    }
    [data-testid="stAppViewContainer"] {
        background: var(--flowsift-canvas);
    }
    [data-testid="stHeader"] {
        background: rgba(247, 247, 245, 0.92);
        backdrop-filter: blur(10px);
    }
    [data-testid="stSidebarNav"] {
        display: none;
    }
    [data-testid="stSidebar"] {
        background: #fbfbfa;
        border-right: 1px solid var(--flowsift-line);
        min-width: 16rem;
    }
    [data-testid="stSidebarContent"] {
        padding-top: 1.25rem;
    }
    .block-container {
        max-width: 1360px;
        padding-top: 3.65rem;
        padding-bottom: 4rem;
    }
    h1, h2, h3, p, label, button, input, textarea {
        letter-spacing: 0 !important;
    }
    h1 {
        color: var(--flowsift-ink);
        font-size: 2.35rem !important;
        font-weight: 730 !important;
        line-height: 1.12 !important;
    }
    h2, h3 {
        color: var(--flowsift-ink);
        font-weight: 690 !important;
    }
    h2 {
        font-size: 1.28rem !important;
        line-height: 1.3 !important;
    }
    h3 {
        font-size: 1.05rem !important;
    }
    .flowsift-brand-wrap {
        align-items: center;
        display: flex;
        gap: 0.7rem;
        margin: 0.1rem 0 0.25rem;
    }
    .flowsift-brand-mark {
        align-items: center;
        background: var(--flowsift-accent);
        border-radius: 7px;
        color: #ffffff;
        display: flex;
        font-size: 0.72rem;
        font-weight: 800;
        height: 2rem;
        justify-content: center;
        width: 2rem;
    }
    .flowsift-brand {
        color: var(--flowsift-ink);
        font-size: 1.12rem;
        font-weight: 760;
        line-height: 1.15;
    }
    .flowsift-brand-note, .flowsift-eyebrow {
        color: var(--flowsift-muted);
        font-size: 0.72rem;
        font-weight: 680;
        text-transform: uppercase;
        letter-spacing: 0.06rem !important;
    }
    .flowsift-page-note {
        color: var(--flowsift-muted);
        font-size: 0.98rem;
        line-height: 1.6;
        margin-top: -0.55rem;
        margin-bottom: 1.55rem;
        max-width: 50rem;
    }
    .flowsift-section {
        align-items: end;
        display: flex;
        justify-content: space-between;
        margin: 2rem 0 0.8rem;
    }
    .flowsift-section-title {
        color: var(--flowsift-ink);
        font-size: 1.08rem;
        font-weight: 700;
    }
    .flowsift-section-note {
        color: var(--flowsift-muted);
        font-size: 0.82rem;
        margin-top: 0.16rem;
    }
    .flowsift-badge {
        border: 1px solid var(--flowsift-line);
        border-radius: 999px;
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 680;
        line-height: 1;
        padding: 0.32rem 0.5rem;
        white-space: nowrap;
    }
    .flowsift-badge[data-tone="good"] {
        background: var(--flowsift-green-soft);
        border-color: #b8dfd0;
        color: var(--flowsift-green);
    }
    .flowsift-badge[data-tone="warn"] {
        background: var(--flowsift-amber-soft);
        border-color: #ead399;
        color: var(--flowsift-amber);
    }
    .flowsift-badge[data-tone="risk"] {
        background: var(--flowsift-red-soft);
        border-color: #e9bcbc;
        color: var(--flowsift-red);
    }
    .flowsift-badge[data-tone="neutral"] {
        background: var(--flowsift-soft);
        color: #52525b;
    }
    .flowsift-empty {
        background: var(--flowsift-panel);
        border: 1px dashed var(--flowsift-line-strong);
        border-radius: 8px;
        padding: 2.4rem 1.4rem;
        text-align: center;
    }
    .flowsift-empty-mark {
        align-items: center;
        background: var(--flowsift-accent-soft);
        border-radius: 7px;
        color: var(--flowsift-accent);
        display: inline-flex;
        font-size: 0.78rem;
        font-weight: 800;
        height: 2.2rem;
        justify-content: center;
        margin-bottom: 0.8rem;
        width: 2.2rem;
    }
    .flowsift-empty-title {
        color: var(--flowsift-ink);
        font-size: 1rem;
        font-weight: 700;
    }
    .flowsift-empty-note {
        color: var(--flowsift-muted);
        font-size: 0.85rem;
        line-height: 1.5;
        margin: 0.35rem auto 0;
        max-width: 32rem;
    }
    .flowsift-score {
        margin-top: 0.6rem;
    }
    .flowsift-score-head {
        align-items: baseline;
        display: flex;
        justify-content: space-between;
        margin-bottom: 0.28rem;
    }
    .flowsift-score-label {
        color: var(--flowsift-muted);
        font-size: 0.72rem;
        font-weight: 620;
    }
    .flowsift-score-value {
        color: var(--flowsift-ink);
        font-size: 0.78rem;
        font-weight: 740;
    }
    .flowsift-score-track {
        background: #ebebee;
        border-radius: 999px;
        height: 0.3rem;
        overflow: hidden;
    }
    .flowsift-score-fill {
        background: var(--flowsift-accent);
        border-radius: inherit;
        height: 100%;
    }
    .flowsift-score[data-tone="good"] .flowsift-score-fill {
        background: var(--flowsift-green);
    }
    .flowsift-score[data-tone="warn"] .flowsift-score-fill {
        background: var(--flowsift-amber);
    }
    .flowsift-score[data-tone="risk"] .flowsift-score-fill {
        background: var(--flowsift-red);
    }
    .flowsift-fact {
        border-left: 2px solid var(--flowsift-line-strong);
        min-height: 5.2rem;
        padding: 0.2rem 0.9rem;
    }
    .flowsift-fact-label {
        color: var(--flowsift-muted);
        font-size: 0.72rem;
        font-weight: 680;
        margin-bottom: 0.35rem;
        text-transform: uppercase;
    }
    .flowsift-fact-value {
        color: var(--flowsift-ink);
        font-size: 0.9rem;
        line-height: 1.5;
    }
    [data-testid="stMetric"] {
        background: var(--flowsift-panel);
        border: 1px solid var(--flowsift-line);
        border-radius: 8px;
        min-height: 6.7rem;
        padding: 1rem 1.1rem;
    }
    [data-testid="stMetricLabel"] {
        color: var(--flowsift-muted);
        font-size: 0.78rem;
    }
    [data-testid="stMetricValue"] {
        color: var(--flowsift-ink);
        font-size: 1.65rem;
        font-weight: 720;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--flowsift-panel);
        border-color: var(--flowsift-line) !important;
        border-radius: 8px !important;
        transition: border-color 160ms ease, box-shadow 160ms ease,
            transform 160ms ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: var(--flowsift-line-strong) !important;
        box-shadow: 0 8px 24px rgba(24, 24, 27, 0.05);
        transform: translateY(-1px);
    }
    [data-testid="stForm"], [data-testid="stExpander"] {
        background: var(--flowsift-panel);
        border-color: var(--flowsift-line) !important;
        border-radius: 8px !important;
    }
    .stButton > button, .stLinkButton > a, [data-testid="stFormSubmitButton"] button {
        border-radius: 6px !important;
        font-weight: 650;
        min-height: 2.5rem;
        transition: background 150ms ease, border-color 150ms ease,
            color 150ms ease, transform 150ms ease;
    }
    .stButton > button[kind="primary"],
    [data-testid="stFormSubmitButton"] button[kind="primary"] {
        background: var(--flowsift-accent);
        border-color: var(--flowsift-accent);
    }
    .stButton > button[kind="primary"]:hover,
    [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
        background: var(--flowsift-accent-hover);
        border-color: var(--flowsift-accent-hover);
    }
    button:focus-visible, a:focus-visible, input:focus-visible,
    textarea:focus-visible, [role="tab"]:focus-visible {
        outline: 3px solid rgba(109, 93, 251, 0.22) !important;
        outline-offset: 2px;
    }
    [data-testid="stPageLink"] a {
        border-radius: 6px;
        color: #52525b;
        font-size: 0.88rem;
        min-height: 2.45rem;
        padding-left: 0.65rem;
    }
    [data-testid="stPageLink"] a:hover {
        background: var(--flowsift-soft);
        color: var(--flowsift-ink);
    }
    [data-baseweb="tab-list"] {
        gap: 1rem;
        border-bottom: 1px solid var(--flowsift-line);
    }
    [data-baseweb="tab"] {
        background: transparent;
        border-radius: 0;
        color: var(--flowsift-muted);
        padding-left: 0.1rem;
        padding-right: 0.1rem;
    }
    [data-baseweb="tab-highlight"] {
        background-color: var(--flowsift-accent);
    }
    [data-baseweb="input"], [data-baseweb="textarea"],
    [data-baseweb="select"] > div {
        border-color: var(--flowsift-line-strong) !important;
        border-radius: 6px !important;
    }
    [data-testid="stAlert"] {
        border-radius: 8px;
    }
    hr {
        border-color: var(--flowsift-line) !important;
    }
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            scroll-behavior: auto !important;
            transition: none !important;
        }
    }
    @media (max-width: 760px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 3.2rem;
        }
        [data-testid="stMetric"] {
            min-height: 5.6rem;
        }
        h1 {
            font-size: 1.9rem !important;
        }
        .flowsift-section {
            align-items: start;
            flex-direction: column;
        }
        .flowsift-page-note {
            margin-bottom: 1.2rem;
        }
    }
</style>
"""


@dataclass(frozen=True)
class PageSlice(Generic[T]):
    """A bounded slice of a larger result set."""

    items: tuple[T, ...]
    page: int
    page_size: int
    total_items: int
    total_pages: int
    first_item: int
    last_item: int


def configure_page(title: str, settings: Settings) -> None:
    """Apply shared page metadata, styling, navigation, and runtime context."""

    page_title = "FlowSift AI" if title == "Overview" else f"{title} | FlowSift AI"
    st.set_page_config(
        page_title=page_title,
        page_icon="FS",
        layout="wide",
        initial_sidebar_state="auto",
    )
    st.markdown(GLOBAL_STYLES, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown(
            '<div class="flowsift-brand-wrap">'
            '<div class="flowsift-brand-mark">FS</div>'
            '<div><div class="flowsift-brand">FlowSift AI</div>'
            '<div class="flowsift-brand-note">Evidence intelligence</div></div>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.divider()
        _render_navigation()
        st.divider()
        if settings.demo_mode:
            mode, tone = "Demo data", "neutral"
        elif settings.live_ready:
            mode, tone = "Live providers", "good"
        else:
            mode, tone = "Setup required", "warn"
        st.markdown(status_badge_html(mode, tone), unsafe_allow_html=True)
        st.caption(redacted_database_url(settings.database_url))


def _render_navigation() -> None:
    """Render multipage links with a direct-page test fallback."""

    pages = [
        ("streamlit_app.py", "Overview", "/", ":material/home:"),
        ("pages/1_Discover.py", "Discover", "/Discover", ":material/explore:"),
        (
            "pages/2_Opportunities.py",
            "Opportunities",
            "/Opportunities",
            ":material/stacked_line_chart:",
        ),
        (
            "pages/3_Opportunity_Details.py",
            "Opportunity details",
            "/Opportunity_Details",
            ":material/manage_search:",
        ),
        ("pages/4_Settings.py", "Settings", "/Settings", ":material/settings:"),
    ]
    try:
        for page, label, _, icon in pages:
            st.page_link(page, label=label, icon=icon, use_container_width=True)
    except KeyError:
        for _, label, route, _ in pages:
            st.markdown(f"[{label}]({route})")


def page_header(title: str, note: str, *, eyebrow: str = "FlowSift AI") -> None:
    """Render a compact page heading with stable spacing."""

    st.markdown(
        f'<div class="flowsift-eyebrow">{escape(eyebrow)}</div>',
        unsafe_allow_html=True,
    )
    st.title(title)
    st.markdown(
        f'<div class="flowsift-page-note">{escape(note)}</div>',
        unsafe_allow_html=True,
    )


def section_header(title: str, note: str = "") -> None:
    """Render a compact section heading outside of a card."""

    note_html = (
        f'<div class="flowsift-section-note">{escape(note)}</div>' if note else ""
    )
    st.markdown(
        '<div class="flowsift-section">'
        f'<div><div class="flowsift-section-title">{escape(title)}</div>'
        f"{note_html}</div></div>",
        unsafe_allow_html=True,
    )


def empty_state(title: str, note: str) -> None:
    """Render a calm empty state; callers can place an action immediately after it."""

    st.markdown(
        '<div class="flowsift-empty">'
        '<div class="flowsift-empty-mark">FS</div>'
        f'<div class="flowsift-empty-title">{escape(title)}</div>'
        f'<div class="flowsift-empty-note">{escape(note)}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def score_bar_html(label: str, score: Optional[float]) -> str:
    """Return an escaped score label, value, and bounded progress bar."""

    value = 0.0 if score is None else min(100.0, max(0.0, float(score)))
    display = format_score(score)
    return (
        f'<div class="flowsift-score" data-tone="{score_tone(score)}">'
        '<div class="flowsift-score-head">'
        f'<span class="flowsift-score-label">{escape(label)}</span>'
        f'<span class="flowsift-score-value">{escape(display)}</span>'
        "</div>"
        '<div class="flowsift-score-track">'
        f'<div class="flowsift-score-fill" style="width:{value:.1f}%"></div>'
        "</div></div>"
    )


def fact_block_html(label: str, value: str | None, fallback: str) -> str:
    """Return a compact escaped fact block for opportunity context."""

    rendered = value.strip() if value and value.strip() else fallback
    return (
        '<div class="flowsift-fact">'
        f'<div class="flowsift-fact-label">{escape(label)}</div>'
        f'<div class="flowsift-fact-value">{escape(rendered)}</div>'
        "</div>"
    )


def score_metric(label: str, score: Optional[float]) -> None:
    """Render a score metric with a consistent empty state."""

    st.metric(label, format_score(score))


def status_badge_html(label: str, tone: str = "neutral") -> str:
    """Return a small escaped status badge for use in Streamlit markdown."""

    valid_tone = tone if tone in {"good", "warn", "risk", "neutral"} else "neutral"
    return (
        f'<span class="flowsift-badge" data-tone="{valid_tone}">'
        f"{escape(label)}</span>"
    )


def score_tone(score: Optional[float]) -> str:
    """Map a score to a restrained visual tone."""

    if score is None:
        return "neutral"
    if score >= 70:
        return "good"
    if score >= 45:
        return "warn"
    return "risk"


def paginate_items(
    items: Sequence[T],
    *,
    page: int,
    page_size: int,
) -> PageSlice[T]:
    """Return a clamped page without mutating the source collection."""

    if page_size < 1:
        raise ValueError("page_size must be at least 1")
    total_items = len(items)
    total_pages = max(1, ceil(total_items / page_size))
    safe_page = min(max(1, page), total_pages)
    start = (safe_page - 1) * page_size
    end = min(start + page_size, total_items)
    return PageSlice(
        items=tuple(items[start:end]),
        page=safe_page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        first_item=start + 1 if total_items else 0,
        last_item=end,
    )


def page_size_control(key: str, *, default: int = 10) -> int:
    """Render a compact page-size selector."""

    options = [5, 10, 25, 50]
    default_index = options.index(default) if default in options else 1
    return int(
        st.selectbox(
            "Rows per page",
            options,
            index=default_index,
            key=f"{key}-page-size",
        )
    )


def render_pagination(page_slice: PageSlice[object], key: str) -> None:
    """Render previous/next controls for an already calculated page."""

    state_key = f"{key}-page"
    st.session_state[state_key] = page_slice.page
    previous, summary, next_column = st.columns([1, 3, 1])
    if previous.button(
        "Previous",
        key=f"{key}-previous",
        disabled=page_slice.page <= 1,
        use_container_width=True,
    ):
        st.session_state[state_key] = page_slice.page - 1
        st.rerun()
    summary.caption(
        f"{page_slice.first_item}-{page_slice.last_item} of {page_slice.total_items} "
        f"| Page {page_slice.page} of {page_slice.total_pages}"
    )
    if next_column.button(
        "Next",
        key=f"{key}-next",
        disabled=page_slice.page >= page_slice.total_pages,
        use_container_width=True,
    ):
        st.session_state[state_key] = page_slice.page + 1
        st.rerun()


def render_database_error(context: str, settings: Settings) -> None:
    """Show a safe, actionable database error without exposing credentials."""

    st.error(
        f"{context} is unavailable because FlowSift AI could not reach its database."
    )
    command = "python scripts/initialize_database.py"
    if settings.demo_mode:
        command += "\npython scripts/seed_demo_data.py"
    st.code(command, language="bash")
    st.caption(f"Configured database: {redacted_database_url(settings.database_url)}")


def set_flash(message: str, tone: str = "success") -> None:
    """Store one message that survives a Streamlit rerun."""

    st.session_state["flowsift-flash"] = {"message": message, "tone": tone}


def render_flash() -> None:
    """Render and clear a previously stored message."""

    payload = st.session_state.pop("flowsift-flash", None)
    if not payload:
        return
    renderer = {
        "success": st.success,
        "warning": st.warning,
        "error": st.error,
        "info": st.info,
    }.get(payload.get("tone"), st.info)
    renderer(payload.get("message", "Update complete."))
