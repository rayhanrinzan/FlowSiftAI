"""Streamlit navigation helpers kept independent from the component module."""

from __future__ import annotations

from html import escape

import streamlit as st


def render_page_link(
    page: str,
    *,
    label: str,
    route: str,
    use_container_width: bool = False,
) -> None:
    """Render an internal page link with a direct-page execution fallback."""

    try:
        st.page_link(
            page,
            label=label,
            use_container_width=use_container_width,
        )
    except KeyError:
        st.markdown(f"[{escape(label)}]({route})")
