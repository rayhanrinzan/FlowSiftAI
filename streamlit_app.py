"""FlowSift AI Streamlit overview dashboard."""

from __future__ import annotations

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from src.config import get_settings
from src.services.opportunity_service import RankedOpportunity
from src.ui.components import (
    configure_page,
    empty_state,
    page_header,
    render_database_error,
    score_bar_html,
    section_header,
    status_badge_html,
)
from src.ui.data import DashboardSnapshot, EvidenceSummary, load_dashboard_snapshot
from src.ui.formatting import format_datetime, format_score
from src.ui.navigation import render_page_link


def _render_opportunities(opportunities: tuple[RankedOpportunity, ...]) -> None:
    """Render concise opportunity cards in a responsive grid."""

    if not opportunities:
        empty_state(
            "No ranked opportunities yet",
            "Add real problem evidence in Discover to create the first scored cluster.",
        )
        render_page_link(
            "pages/1_Discover.py",
            label="Add evidence",
            route="/Discover",
            use_container_width=True,
        )
        return

    for index in range(0, len(opportunities), 2):
        columns = st.columns(2)
        for column, opportunity in zip(columns, opportunities[index : index + 2]):
            with column:
                with st.container(border=True):
                    if st.button(
                        opportunity.title,
                        key=f"dashboard-open-{opportunity.cluster_id}",
                        use_container_width=True,
                    ):
                        st.session_state["selected_cluster_id"] = opportunity.cluster_id
                        st.switch_page("pages/3_Opportunity_Details.py")
                    target = (
                        opportunity.target_customer or "Target customer not established"
                    )
                    st.caption(
                        f"{target} | {opportunity.evidence_count} evidence | "
                        f"{opportunity.competitor_count} competitors"
                    )
                    st.markdown(
                        status_badge_html(
                            opportunity.research_status.replace("_", " ").title(),
                            "good"
                            if opportunity.research_status == "researched"
                            else "neutral",
                        ),
                        unsafe_allow_html=True,
                    )
                    left, right = st.columns(2)
                    left.markdown(
                        score_bar_html("Problem", opportunity.problem_score),
                        unsafe_allow_html=True,
                    )
                    right.markdown(
                        score_bar_html("Market gap", opportunity.whitespace_score),
                        unsafe_allow_html=True,
                    )
                    left.markdown(
                        score_bar_html("Opportunity", opportunity.opportunity_score),
                        unsafe_allow_html=True,
                    )
                    right.markdown(
                        score_bar_html("Confidence", opportunity.confidence_score),
                        unsafe_allow_html=True,
                    )


def _render_recent_evidence(evidence_items: tuple[EvidenceSummary, ...]) -> None:
    """Render recent evidence as a scan-friendly activity list."""

    if not evidence_items:
        empty_state(
            "No recent evidence",
            "Newly processed discussions will appear here with their extraction state.",
        )
        return

    for item in evidence_items:
        with st.container(border=True):
            title, source, state, collected = st.columns([3.7, 1.3, 1, 1.4])
            title.write(item.title or item.problem_statement or "Untitled discussion")
            title.caption((item.problem_statement or item.raw_text)[:150])
            source.caption("Source")
            source.write(item.community or item.platform)
            state.caption("State")
            state.markdown(
                status_badge_html(
                    "Accepted" if item.contains_problem else "Review",
                    "good" if item.contains_problem else "warn",
                ),
                unsafe_allow_html=True,
            )
            collected.caption("Collected")
            collected.write(format_datetime(item.collected_at))


def _render_metrics(snapshot: DashboardSnapshot) -> None:
    metrics = snapshot.metrics
    coverage = (
        (metrics.researched_opportunity_count / metrics.cluster_count) * 100
        if metrics.cluster_count
        else 0.0
    )
    evidence, clusters, researched, coverage_column = st.columns(4)
    evidence.metric("Evidence items", metrics.evidence_count)
    clusters.metric("Opportunity clusters", metrics.cluster_count)
    researched.metric("Researched opportunities", metrics.researched_opportunity_count)
    coverage_column.metric("Research coverage", f"{coverage:.0f}%")


def main() -> None:
    """Render the overview dashboard."""

    settings = get_settings()
    configure_page("Overview", settings)
    page_header(
        "FlowSift AI",
        "Turn real customer friction into ranked, explainable market opportunities.",
        eyebrow="Evidence intelligence",
    )

    if not settings.demo_mode and not settings.live_ready:
        st.warning(
            "Production mode is active, but one or more live providers still need "
            "credentials. Existing data remains available while setup is completed."
        )
        render_page_link(
            "pages/4_Settings.py",
            label="Complete live setup",
            route="/Settings",
            use_container_width=False,
        )

    try:
        with st.spinner("Loading the latest opportunity signals..."):
            snapshot = load_dashboard_snapshot(settings.database_url)
    except SQLAlchemyError:
        render_database_error("The overview", settings)
        return

    _render_metrics(snapshot)

    section_header(
        "Highest-ranked opportunities",
        "Problem strength, market whitespace, and confidence in one view.",
    )
    _render_opportunities(snapshot.opportunities)

    section_header(
        "Recent evidence",
        "The latest source discussions processed by FlowSift AI.",
    )
    _render_recent_evidence(snapshot.recent_evidence)


if __name__ == "__main__":
    main()
