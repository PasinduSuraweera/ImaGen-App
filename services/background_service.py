import requests
from typing import Dict, Any
import streamlit as st

def remove_background(api_key: str, image_data: bytes, content_moderation: bool = False) -> Dict[str, Any]:
    url = "https://engine.prod.bria-api.com/v1/background/remove"
    headers = {
        'api_token': api_key,
        'Accept': 'application/json'
    }
    files = {
        'file': ('image.png', image_data, 'image/png'),
        'content_moderation': (None, str(content_moderation).lower())
    }
    try:
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        error_msg = f"Background removal failed: {e.response.status_code} - {e.response.text}"
        print(error_msg)
        st.error(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        error_msg = f"Background removal failed: {str(e)}"
        print(error_msg)
        st.error(error_msg)
        raise Exception(error_msg)