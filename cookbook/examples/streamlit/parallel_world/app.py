from typing import Optional
import streamlit as st
from phi.tools.streamlit.components import reload_button_sidebar
from cookbook.examples.streamlit.parallel_world.parallel_world_builder import get_world_builder, World


st.set_page_config(
    page_title="World Building",
    page_icon=":ringed_planet:",
)
st.title("Parallel World Building")
st.markdown("##### :orange_heart: built using [phidata](https://github.com/phidatahq/phidata)")
with st.expander(":rainbow[:point_down: How to use]"):
    st.markdown("- Generate a new world by providing a brief description")
st.write("\n")


def restart_assistant():
    st.session_state["world_builder"] = None
    st.session_state["world"] = None
    st.rerun()


def main() -> None:
    # Get model
    model = st.sidebar.selectbox("Select Model", options=["gpt-4o-mini", "gpt-4o"])
    # Set assistant_type in session state
    if "model" not in st.session_state:
        st.session_state["model"] = model
    # Restart the assistant if assistant_type has changed
    elif st.session_state["model"] != model:
        st.session_state["model"] = model
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
                    world_response = world_builder.run(description)
                    response = world_response.content
                    # Save world in session state
                    st.session_state["world"] = world_response
                    world_description = ""
                    for key, value in response.model_dump(exclude_none=True).items():  # type: ignore
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

    st.sidebar.markdown("---")
    reload_button_sidebar(text="New World")


main()
