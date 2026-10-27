import requests
import streamlit as st

API_URL = "http://localhost:8000/api"


@st.cache_data(ttl=60, show_spinner=False)
def fetch_data(endpoint: str, params: dict | None = None):
    url = f"{API_URL}{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        body = error.response.text[:500] if error.response is not None else str(error)
        status = error.response.status_code if error.response is not None else "unavailable"
        request_url = error.response.request.url if error.response is not None else url
        st.error(f"API request failed: {request_url} | status={status} | body={body}")
    except ValueError as error:
        st.error(f"API returned invalid JSON: {url} | params={params} | error={error}")
    return None


def post_data(endpoint: str, payload: dict):
    url = f"{API_URL}{endpoint}"
    try:
        response = requests.post(url, json=payload, timeout=35)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        detail = error.response.json().get("detail") if error.response is not None else str(error)
        st.error(f"AI request failed: {detail}")
    except ValueError:
        st.error("The AI service returned an invalid response.")
    return None


def download_data(endpoint: str, params: dict | None = None) -> bytes | None:
    """Fetch a downloadable artifact through the existing API boundary."""
    try:
        response = requests.get(f"{API_URL}{endpoint}", params=params, timeout=30)
        response.raise_for_status()
        return response.content
    except requests.RequestException as error:
        status = error.response.status_code if error.response is not None else "unavailable"
        st.error(f"Export request failed: {status}")
        return None
