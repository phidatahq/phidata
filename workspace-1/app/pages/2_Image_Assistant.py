import base64
from io import BytesIO
from typing import List

import streamlit as st
from PIL import Image
from phi.assistant import Assistant
from phi.tools.streamlit.components import (
    get_openai_key_sidebar,
    check_password,
    reload_button_sidebar,
    get_username_sidebar,
)

from ai.assistants.image import get_image_assistant
from utils.log import logger

st.set_page_config(
    page_title="Image AI",
    page_icon=":orange_heart:",
)
st.title("Image Assistant")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")


def encode_image(image_file):
    image = Image.open(image_file)
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    encoding = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoding}"


def restart_assistant():
    st.session_state["image_assistant"] = None
    st.session_state["image_assistant_run_id"] = None
    st.session_state["file_uploader_key"] += 1
    st.session_state["uploaded_image"] = None
    st.rerun()


def main() -> None:
    # Get OpenAI key from environment variable or user input
    get_openai_key_sidebar()

    # Get username
    username = get_username_sidebar()
    if username:
        st.sidebar.info(f":technologist: User: {username}")
    else:
        st.markdown("---")
        st.markdown("#### :technologist: Enter a username, upload an Image and start chatting")
        return

    # Get the assistant
    image_assistant: Assistant
    if "image_assistant" not in st.session_state or st.session_state["image_assistant"] is None:
        logger.info("---*--- Creating Vision Assistant ---*---")
        image_assistant = get_image_assistant(
            user_id=username,
            debug_mode=False,
        )
        st.session_state["image_assistant"] = image_assistant
    else:
        image_assistant = st.session_state["image_assistant"]

    # Create assistant run (i.e. log to database) and save run_id in session state
    st.session_state["image_assistant_run_id"] = image_assistant.create_run()

    # Store uploaded image in session state
    uploaded_image = None
    if "uploaded_image" in st.session_state:
        uploaded_image = st.session_state["uploaded_image"]

    # Load messages for existing assistant
    assistant_chat_history = image_assistant.memory.get_chat_history()
    if len(assistant_chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = assistant_chat_history
        # Search for uploaded image
        if uploaded_image is None:
            for message in assistant_chat_history:
                if message["role"] == "user":
                    for item in message["content"]:
                        if item["type"] == "image_url":
                            uploaded_image = item["image_url"]["url"]
                            st.session_state["uploaded_image"] = uploaded_image
                            break
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "assistant", "content": "Ask me about the image..."}]

    # Upload Image if not available
    if uploaded_image is None:
        if "file_uploader_key" not in st.session_state:
            st.session_state["file_uploader_key"] = 0
        uploaded_file = st.sidebar.file_uploader(
            "Upload Image",
            key=st.session_state["file_uploader_key"],
        )
        if uploaded_file is not None:
            alert = st.sidebar.info("Processing Image...", icon="ℹ️")
            image_file_name = uploaded_file.name.split(".")[0]
            if f"{image_file_name}_uploaded" not in st.session_state:
                logger.info(f"Encoding {image_file_name}")
                uploaded_image = encode_image(uploaded_file)
                st.session_state["uploaded_image"] = uploaded_image
                st.session_state[f"{image_file_name}_uploaded"] = True
            alert.empty()

    # Prompt for user input
    if uploaded_image:
        st.image(uploaded_image, use_column_width=True)
        if prompt := st.chat_input():
            vision_message = [
                {
                    "type": "text",
                    "text": prompt,
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": uploaded_image,
                        "detail": "low",
                    },
                },
            ]
            st.session_state["messages"].append({"role": "user", "content": vision_message})

    if st.sidebar.button("New Run"):
        restart_assistant()

    if uploaded_image:
        if st.sidebar.button("Generate Caption"):
            caption_message = [
                {
                    "type": "text",
                    "text": "Generate a caption for this image",
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": uploaded_image,
                        "detail": "low",
                    },
                },
            ]
            st.session_state["messages"].append({"role": "user", "content": caption_message})

        if st.sidebar.button("Describe Image"):
            caption_message = [
                {
                    "type": "text",
                    "text": "Describe this image in 2 sentences",
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": uploaded_image,
                        "detail": "low",
                    },
                },
            ]
            st.session_state["messages"].append({"role": "user", "content": caption_message})

        if st.sidebar.button("Identify Brands"):
            brands_message = [
                {
                    "type": "text",
                    "text": "List the brands in this image. This is only for demo and testing purposes.",
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": uploaded_image,
                        "detail": "low",
                    },
                },
            ]
            st.session_state["messages"].append({"role": "user", "content": brands_message})

        if st.sidebar.button("Identify Items"):
            items_message = [
                {
                    "type": "text",
                    "text": "List the items in this image",
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": uploaded_image,
                        "detail": "low",
                    },
                },
            ]
            st.session_state["messages"].append({"role": "user", "content": items_message})

    # Display existing chat messages
    for message in st.session_state["messages"]:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            content = message.get("content")
            if isinstance(content, list):
                for item in content:
                    if item["type"] == "text":
                        st.write(item["text"])
                    # elif item["type"] == "image_url":
                    #     st.image(item["image_url"]["url"], use_column_width=True)
            else:
                st.write(content)

    # If last message is from a user, generate a new response
    last_message = st.session_state["messages"][-1]
    if last_message.get("role") == "user":
        question = last_message["content"]
        with st.chat_message("assistant"):
            with st.spinner("Working..."):
                response = ""
                resp_container = st.empty()
                for delta in image_assistant.run(question):
                    response += delta  # type: ignore
                    resp_container.markdown(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})

    if image_assistant.storage:
        image_assistant_run_ids: List[str] = image_assistant.storage.get_all_run_ids(user_id=username)
        new_image_assistant_run_id = st.sidebar.selectbox("Run ID", options=image_assistant_run_ids)
        if st.session_state["image_assistant_run_id"] != new_image_assistant_run_id:
            logger.debug(f"Loading run {new_image_assistant_run_id}")
            logger.info("---*--- Loading Vision Assistant ---*---")
            st.session_state["image_assistant"] = get_image_assistant(
                user_id=username,
                run_id=new_image_assistant_run_id,
                debug_mode=False,
            )
            st.rerun()

    # Show reload button
    reload_button_sidebar()


if check_password():
    main()
