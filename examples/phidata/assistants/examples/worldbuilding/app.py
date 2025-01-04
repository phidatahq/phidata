from typing import Optional

import streamlit as st
from phi.tools.streamlit.components import reload_button_sidebar

from assistant import get_world_builder, get_world_explorer, World  # type: ignore
from logging import getLogger

logger = getLogger(__name__)

st.set_page_config(
    page_title="World Building",
    page_icon=":ringed_planet:",
)
st.title("World Building using OpenHermes and Ollama")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")
with st.expander(":rainbow[:point_down: How to use]"):
    st.markdown("- Generate a new world by providing a brief description")
    st.markdown("- Ask questions about the world and explore it")
st.write("\n")


def restart_assistant():
    st.session_state["world_builder"] = None
    st.session_state["world_explorer"] = None
    st.session_state["world_explorer_run_id"] = None
    st.rerun()


def main() -> None:
    # Get model
    model = st.sidebar.selectbox("Select Model", options=["openhermes", "llama2"])
    # Set assistant_type in session state
    if "model" not in st.session_state:
        st.session_state["model"] = model
    # Restart the assistant if assistant_type has changed
    elif st.session_state["model"] != model:
        st.session_state["model"] = model
        restart_assistant()

    # Get temperature
    temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.0, value=0.1, step=0.1)
    # Set temperature in session state
    if "temperature" not in st.session_state:
        st.session_state["temperature"] = temperature
    # Restart the assistant if temperature has changed
    elif st.session_state["temperature"] != temperature:
        st.session_state["temperature"] = temperature
        restart_assistant()

    # Get the world builder
    world: Optional[World] = st.session_state["world"] if "world" in st.session_state else None
    world_builder = get_world_builder(debug_mode=True)
    description = st.text_input(
        label="World description",
        value="An advanced futuristic city on distant planet with only 1 island. Dark history. Population 1 trillion.",
        help="Provide a description for your world.",
    )

    if world is None:
        if st.button("Generate World"):
            with st.status(":orange[Building World]", expanded=True) as status:
                with st.container():
                    world_container = st.empty()
                    world = world_builder.run(description)  # type: ignore
                    # Save world in session state
                    st.session_state["world"] = world
                    world_description = ""
                    for key, value in world.model_dump(exclude_none=True).items():
                        _k = key.title()
                        _v = ", ".join(value) if isinstance(value, list) else value
                        world_description += f"- **{_k}**: {_v}\n\n"
                        world_container.markdown(world_description)
                status.update(label=":orange[World generated!]", state="complete", expanded=True)
    else:
        world_name = world.name
        with st.expander(f":orange[{world_name}]", expanded=False):
            world_container = st.empty()
            world_description = ""
            for key, value in world.model_dump(exclude_none=True).items():
                _k = key.title()
                _v = ", ".join(value) if isinstance(value, list) else value
                world_description += f"- **{_k}**: {_v}\n\n"
                world_container.markdown(world_description)

    if world is None:
        return

    # Get the world_explorer
    if "world_explorer" not in st.session_state or st.session_state["world_explorer"] is None:
        logger.info("---*--- Creating World Explorer ---*---")
        world_explorer = get_world_explorer(
            model=model,
            temperature=temperature,
            world=world,
            debug_mode=True,
        )
        st.session_state["world_explorer"] = world_explorer
    else:
        world_explorer = st.session_state["world_explorer"]

    # Load existing messages
    chat_history = world_explorer.memory.get_chat_history()
    if len(chat_history) > 0:
        logger.debug("Loading chat history")
        st.session_state["messages"] = chat_history
    else:
        logger.debug("No chat history found")
        st.session_state["messages"] = [{"role": "assistant", "content": "Lets explore this world together..."}]

    # Prompt for user input
    if prompt := st.chat_input():
        st.session_state["messages"].append({"role": "user", "content": prompt})

    # Display existing chat messages
    for message in st.session_state["messages"]:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # If last message is from a user, generate a new response
    last_message = st.session_state["messages"][-1]
    if last_message.get("role") == "user":
        question = last_message["content"]
        with st.chat_message("assistant"):
            response = ""
            resp_container = st.empty()
            for delta in world_explorer.run(question):
                response += delta  # type: ignore
                resp_container.markdown(response)

            st.session_state["messages"].append({"role": "assistant", "content": response})

    st.sidebar.markdown("---")
    reload_button_sidebar(text="New World")


main()
