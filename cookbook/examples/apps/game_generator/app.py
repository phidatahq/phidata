import nest_asyncio
import streamlit as st
from pathlib import Path
from agno.agent import Agent
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.run.response import RunResponse
from agno.utils.log import logger
from game_generator import get_game_generator_agent, GameOutput
from utils import (
    CUSTOM_CSS,
    add_message,
    session_management_widget,
    sidebar_widget,
    about_widget,
)
import logging

nest_asyncio.apply()

# Initialize the storage
storage = PostgresAgentStorage(
    db_url="postgresql+psycopg://ai:ai@localhost:5532/ai",
    table_name="game_generator_sessions",
    schema="ai",
)

st.set_page_config(
    page_title="HTML5 Game Generator",
    page_icon="🎮",
    layout="wide",
)

# Apply custom CSS
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.title("Game Generator")
st.markdown("##### 🎮 built using [Agno](https://github.com/agno-agi/agno)")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('game_generator.log')
    ]
)

def main() -> None:
    try:
        ####################################################################
        # Initialize Game Generator Agent
        ####################################################################
        game_generator_agent: Agent
        model_id = "google:gemini-2.0-flash-exp"
        
        if (
            "game_generator_agent" not in st.session_state
            or st.session_state["game_generator_agent"] is None
            or st.session_state.get("current_model") != model_id
        ):
            game_generator_agent = get_game_generator_agent(
                model_id=model_id
            )
            st.session_state["game_generator_agent"] = game_generator_agent
            st.session_state["current_model"] = model_id
        else:
            game_generator_agent = st.session_state["game_generator_agent"]

        ####################################################################
        # Load Agent Session from the database
        ####################################################################
        try:
            st.session_state["game_generator_agent_session_id"] = game_generator_agent.load_session()
        except Exception:
            st.warning("Could not create Agent session, is the database running?")
            return
        
        ####################################################################
        # Load runs from memory
        ####################################################################
        agent_runs = game_generator_agent.memory.runs
        if len(agent_runs) > 0:
            logger.debug("Loading run history")
            st.session_state["messages"] = []
            for _run in agent_runs:
                if _run.message is not None:
                    add_message(_run.message.role, _run.message.content)
                if _run.response is not None:
                    add_message("assistant", _run.response.content)
        else:
            logger.debug("No run history found")
            st.session_state["messages"] = []

        ####################################################################
        # Sidebar
        ####################################################################
        sidebar_widget()

        ####################################################################
        # Game Description Input
        ####################################################################
        if prompt := st.chat_input("🎮 Describe your game"):
            add_message("user", prompt)
            st.session_state["generate_game"] = True

        ####################################################################
        # Display chat history and render games
        ####################################################################
        for message in st.session_state.get("messages", []):
            if message["role"] in ["user", "assistant"]:
                _content = message["content"]
                if _content is not None:
                    print(f"Message content: {_content}")
                    if isinstance(_content, GameOutput):
                        with st.chat_message(message["role"]):
                            st.subheader("Play the Game")
                            st.components.v1.html(_content.code, height=700, scrolling=False)

                            st.subheader("Game Instructions")
                            st.write(_content.instructions)

                            st.download_button(
                                label="Download Game HTML",
                                data=_content.code,
                                file_name="game.html",
                                mime="text/html",
                            )
                    else:
                        with st.chat_message(message["role"]):
                            st.markdown(_content)

        ####################################################################
        # Generate Game
        ####################################################################
        last_message = (
            st.session_state["messages"][-1] if st.session_state["messages"] else None
        )
        if st.session_state.get("generate_game", False):
            with st.spinner("Generating your game... This might take a minute..."):
                try:
                    logger.info(f"Generating game with message: {last_message}")
                    game_output = game_generator_agent.run({"role": "user", "content": last_message["content"]})
                    
                    logger.debug(f"Game output received: {type(game_output)}")

                    if game_output:
                        response_dict = game_output.to_dict().get("content")
                        print(response_dict)
                        game_content = GameOutput(
                            code=response_dict["code"],
                            instructions=response_dict["instructions"]
                        )
                        logger.debug("Successfully extracted game code")

                        # Store the resulting code
                        game_output_path = Path(__file__).parent.joinpath(f"games/{st.session_state['game_generator_agent_session_id']}.html")
                        game_output_path.write_text(game_content.code)
                        logger.info(f"Game code written to {game_output_path}")

                        add_message("assistant", game_content)
                        st.rerun()
                    else:
                        error_msg = f"Invalid game output format: {type(game_output)}"
                        print(game_output.content)
                        logger.error(error_msg)
                        st.error("Sorry, could not generate a game.")
                except Exception as e:
                    logger.error(f"Failed to generate game", exc_info=True)
                    st.error(f"Failed to generate game: {str(e)}")

        ####################################################################
        # Session selector
        ####################################################################
        session_management_widget(game_generator_agent, model_id)

        ####################################################################
        # About section
        ####################################################################
        about_widget()

    except Exception as e:
        logger.error("Main app error", exc_info=True)
        st.error(f"Application error: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error("Fatal application error", exc_info=True)
        st.error("A fatal error occurred. Please check the logs.")
