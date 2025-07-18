import streamlit as st
import os
from dotenv import load_dotenv
from services import (
    add_shadow,
    create_packshot,
)
from PIL import Image
import io
import requests
import time

# Configure Streamlit page
st.set_page_config(
    page_title="ImaGen App",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv(verbose=True)

# Debug: Print environment variable status
api_key = os.getenv("BRIA_API_KEY")
print(f"API Key present: {bool(api_key)}")
print(f"API Key value: {api_key if api_key else 'Not found'}")
print(f"Current working directory: {os.getcwd()}")
print(f".env file exists: {os.path.exists('.env')}")

def initialize_session_state():
    if 'api_key' not in st.session_state:
        st.session_state.api_key = os.getenv('BRIA_API_KEY')
    if 'generated_images' not in st.session_state:
        st.session_state.generated_images = []
    if 'current_image' not in st.session_state:
        st.session_state.current_image = None
    if 'pending_urls' not in st.session_state:
        st.session_state.pending_urls = []
    if 'edited_image' not in st.session_state:
        st.session_state.edited_image = None
    if 'original_prompt' not in st.session_state:
        st.session_state.original_prompt = ""

def download_image(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except Exception as e:
        st.error(f"Error downloading image: {str(e)}")
        return None

def check_generated_images():
    if st.session_state.pending_urls:
        ready_images = []
        still_pending = []
        for url in st.session_state.pending_urls:
            try:
                response = requests.head(url)
                if response.status_code == 200:
                    ready_images.append(url)
                else:
                    still_pending.append(url)
            except Exception:
                still_pending.append(url)
        st.session_state.pending_urls = still_pending
        if ready_images:
            st.session_state.edited_image = ready_images[0]
            return True
    return False

def auto_check_images(status_container):
    max_attempts = 3
    attempt = 0
    while attempt < max_attempts and st.session_state.pending_urls:
        time.sleep(2)
        if check_generated_images():
            status_container.success("✨ Image ready!")
            return True
        attempt += 1
    return False

def main():
    st.title("ImaGen Editor")
    initialize_session_state()

    # Sidebar for API key
    with st.sidebar:
        st.header("Settings")
        api_key = st.text_input("Enter your API key:", value=st.session_state.api_key if st.session_state.api_key else "", type="password")
        if api_key:
            st.session_state.api_key = api_key

    # Main tabs
    tabs = st.tabs(["Background Editor", "Shadow Editor"])

    # Create Packshot Tab
    with tabs[0]:
        uploaded_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])
        if uploaded_file:
            col1, col2 = st.columns(2)
            with col1:
                st.image(uploaded_file, caption="Original Image", use_container_width=True)
                force_rmbg = st.checkbox("Transparent Background", False)
                bg_color = st.color_picker("Background Color", "#FFFFFF", disabled=force_rmbg)
                sku = st.text_input("SKU (optional)", "")
                content_moderation = st.checkbox("Enable Content Moderation", False)
                if st.button("Generate Background"):
                    with st.spinner("Creating Image..."):
                        try:
                            img = Image.open(io.BytesIO(uploaded_file.getvalue()))
                            img_byte_arr = io.BytesIO()
                            img.save(img_byte_arr, format='PNG')
                            image_data = img_byte_arr.getvalue()
                            if force_rmbg:
                                from services.background_service import remove_background
                                bg_result = remove_background(
                                    st.session_state.api_key, image_data, content_moderation=content_moderation
                                )
                                if bg_result and "result_url" in bg_result:
                                    response = requests.get(bg_result["result_url"])
                                    if response.status_code == 200:
                                        image_data = response.content
                            result = create_packshot(
                                st.session_state.api_key, image_data,
                                background_color='transparent' if force_rmbg else bg_color,
                                sku=sku if sku else None, force_rmbg=force_rmbg,
                                content_moderation=content_moderation
                            )
                            if result and "result_url" in result:
                                st.success("✨ Image generated successfully!")
                                st.session_state.edited_image = result["result_url"]
                            else:
                                st.error("No result URL in the API response.")
                        except Exception as e:
                            st.error(f"Error creating packshot: {str(e)}")
                            if "422" in str(e):
                                st.warning("Content moderation failed.")

            with col2:
                if st.session_state.edited_image:
                    st.image(st.session_state.edited_image, caption="Edited Image", use_container_width=True)
                    image_data = download_image(st.session_state.edited_image)
                    if image_data:
                        st.download_button("⬇️ Download Result", image_data, "edited-image.png", "image/png")

    # Add Shadow Tab
    with tabs[1]:
        uploaded_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"], key="shadow_upload")
        if uploaded_file:
            col1, col2 = st.columns(2)
            with col1:
                st.image(uploaded_file, caption="Original Image", use_container_width=True)
                shadow_type = st.selectbox("Shadow Type", ["Natural", "Drop"])
                bg_color = st.color_picker("Background Color (optional)", "#FFFFFF")
                use_transparent_bg = st.checkbox("Use Transparent Background", True)
                shadow_color = st.color_picker("Shadow Color", "#000000")
                sku = st.text_input("SKU (optional)", "")
                offset_x = st.slider("X Offset", -50, 50, 0)
                offset_y = st.slider("Y Offset", -50, 50, 15)
                shadow_intensity = st.slider("Shadow Intensity", 0, 100, 60)
                shadow_blur = st.slider("Shadow Blur", 0, 50, 15 if shadow_type.lower() == "natural" else 20)
                force_rmbg = st.checkbox("Force Background Removal", False)
                content_moderation = st.checkbox("Enable Content Moderation", False)
                if st.button("Add Shadow"):
                    with st.spinner("Adding shadow effect..."):
                        try:
                            result = add_shadow(
                                api_key=st.session_state.api_key, image_data=uploaded_file.getvalue(),
                                shadow_type=shadow_type.lower(), background_color=None if use_transparent_bg else bg_color,
                                shadow_color=shadow_color, shadow_offset=[offset_x, offset_y],
                                shadow_intensity=shadow_intensity, shadow_blur=shadow_blur,
                                sku=sku if sku else None, force_rmbg=force_rmbg,
                                content_moderation=content_moderation
                            )
                            if result and "result_url" in result:
                                st.success("✨ Shadow added successfully!")
                                st.session_state.edited_image = result["result_url"]
                            else:
                                st.error("No result URL in the API response.")
                        except Exception as e:
                            st.error(f"Error adding shadow: {str(e)}")
                            if "422" in str(e):
                                st.warning("Content moderation failed.")

            with col2:
                if st.session_state.edited_image:
                    st.image(st.session_state.edited_image, caption="Edited Image", use_container_width=True)
                    image_data = download_image(st.session_state.edited_image)
                    if image_data:
                        st.download_button("⬇️ Download Result", image_data, "edited_image.png", "image/png")

if __name__ == "__main__":
    main()