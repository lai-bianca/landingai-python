"""This module contains common streamlit utilities that are used across the example Apps in this repo.
It's only intended for the example streamlit Apps. When using the SDK in your own project, you don't need to use this module.
"""
import logging
import os
from typing import Any, Optional, Tuple

_DEFAULT_API_KEY_ENV_VAR = "LANDINGAI_API_KEY"

_LOGGER = logging.getLogger(__name__)


def _import_st() -> Any:
    """Import streamlit and raise an error if it fails."""
    try:
        import streamlit as st

        return st
    except ImportError as e:
        raise ValueError(
            """Failed to import streamlit due to missing the `streamlit` dependency.
This is likely because you are trying to use a function in this module outside of the example Apps in this repo. But this function is only intended for example Apps of this repo.
If you are using this function in other environment, please install streamlit manually first, e.g. 'pip install streamlit'.
If you are running one of the example Apps of this repo, please follow the installation instructions of that App.
    """
        ) from e


def setup_page(page_title: str) -> None:
    """Common setup code for streamlit pages.
    This function should be called only once at the beginning of the page.
    """
    level = os.environ.get("LOGLEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(filename)s %(funcName)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    st = _import_st()
    st.set_page_config(
        page_title=page_title,
        page_icon="./examples/apps/assets/favicon.ico",
        layout="centered",
        initial_sidebar_state="auto",
    )
    # Hide the default menu button (on the top right corner) and the footer
    hide_footer_style = """
        <style>
        .reportview-container .main footer {visibility: hidden;}
        #MainMenu {
                visibility: hidden;
            }

        footer {
                visibility: hidden;
            }
        </style>
        """
    st.markdown(hide_footer_style, unsafe_allow_html=True)


def render_svg(svg: str, margin_bottom: int = 3) -> None:
    """Renders the given svg string.
    This is a workaround as st.image doesn't seem to work.
    See: https://github.com/streamlit/streamlit/issues/275
    """
    st = _import_st()
    import base64

    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    html = r'<img src="data:image/svg+xml;base64,%s"  height="50" />' % b64
    st.write(html, unsafe_allow_html=True)
    for _ in range(margin_bottom):
        st.write("\n")


def check_api_credentials_set() -> None:
    """Check if API credential is set in session state."""
    st = _import_st()
    api_key = st.session_state.get("api_key")
    if api_key:
        if api_key.startswith("land_sk_"):
            return  # non-empty v2 api key
        elif st.session_state.get("api_secret"):
            return  # non-empty v1 api key and secret

    st.error("Please open the sidebar and enter your API credential first.")
    st.stop()


def check_endpoint_id_set() -> None:
    """Check if endpoint ID is set in session state."""
    st = _import_st()
    if st.session_state.get("endpoint_id"):
        return
    st.error("Please open the sidebar and enter your CloudInference endpoint ID first.")
    st.stop()


def get_api_credential_or_use_default() -> Tuple[Optional[str], Optional[str]]:
    """Get API credential (api key and api secret) from the session state.
    If the API credential is not set in the session state, use the default API credential from environment variables.
    The output could be either a v1 API key and secret, or a v2 API key depends on what is set in the session state.
    """
    st = _import_st()
    key, secret = (st.session_state["api_key"], st.session_state["api_secret"])
    if not key:
        return get_default_api_key(), secret
    return key, secret


def get_default_api_key() -> Optional[str]:
    """Get the default (free trial) API key."""
    default_key = os.environ.get(_DEFAULT_API_KEY_ENV_VAR)
    if not default_key:
        _LOGGER.warning(
            "The default API key is not set in the application. Please set your API key in the environment variable. E.g. export LANDINGAI_API_KEY=......"
        )
        return None
    return default_key


def render_api_config_form(
    render_endpoint_id: bool = False,
    default_key: str = "",
    default_secret: str = "",
    default_endpoint_id: str = "",
) -> None:
    """Show API credential and endpoint ID (optionally) configuration form.
    The form provides a way for users to set the API credential and endpoint ID in the session state.
    The values saved in the session state can be accessed by `get_api_credential_or_use_default()`.
    This is the source of truth for the API credential and endpoint ID in the App.
    """

    st = _import_st()
    # Set a default value in session state for the first time
    if "api_key" not in st.session_state:
        st.session_state["api_key"] = default_key
    if "api_secret" not in st.session_state:
        st.session_state["api_secret"] = default_secret
    if "endpoint_id" not in st.session_state:
        st.session_state["endpoint_id"] = default_endpoint_id

    def _update_credential(
        api_key: str, api_secret: str, endpoint_id: Optional[str]
    ) -> None:
        st.session_state["api_key"] = api_key
        st.session_state["api_secret"] = api_secret
        if endpoint_id:
            st.session_state["endpoint_id"] = endpoint_id

    with st.form("api_credential_form"):
        api_key = st.text_input(
            "LandingLens API Key",
            key="lnd_api_key",
            value=st.session_state["api_key"],
            help="If left empty, the free trial API key is used. The default key is a free trial key with a rate limit, i.e. X times per day.",
            type="password",
        )
        api_secret = st.text_input(
            "LandingLens API Secret",
            key="lnd_api_secret",
            value=st.session_state["api_secret"],
            help="Leave it empty if you use a v2 API key. Only the legacy API key (i.e. v1) requires API secret. The v2 API key always starts with 'land_sk_'.",
        )
        endpoint_id = None
        if render_endpoint_id:
            endpoint_id = st.text_input(
                "Cloud Deployment endpoint ID",
                key="lnd_endpoint_id",
                value=st.session_state.get("endpoint_id", ""),
            )

        submitted = st.form_submit_button("Save")
        if submitted:
            _update_credential(api_key, api_secret, endpoint_id)
            st.info("API configuration is saved successfully")

    key, _ = get_api_credential_or_use_default()
    if key == get_default_api_key():
        st.info("The default API key (free trial) is used")