from typing import Any, Dict, List, Optional, Union

import streamlit as st
from agno.utils.log import logger
from agno.agent import Agent

from game_generator import GameOutput, get_game_generator_agent

def add_message(
    role: str, content: Union[str, GameOutput]
) -> None:
    """Safely add a message to the session state"""
    if "messages" not in st.session_state or not isinstance(
        st.session_state["messages"], list
    ):
        st.session_state["messages"] = []
    st.session_state["messages"].append(
        {"role": role, "content": content}
    )

def sidebar_widget() -> None:
    """Display a sidebar with sample user queries"""
    with st.sidebar:
        # Example Games
        st.markdown("#### 🎮 Example Games")
        if st.button("🐍 Snake Game"):
            add_message(
                "user",
                """Generate a classic Snake game with the following specifications:

                Core Mechanics:
                - Snake controlled by arrow keys
                - Green snake body with a slightly darker head
                - Red apple as collectible food
                - Dark gray background (#333333) for contrast
                - Smooth, responsive controls

                Gameplay Features:
                - Snake grows longer when eating apples
                - Score display in top-right corner
                - Gradually increasing speed as score grows
                - Game over on wall or self collision
                - Clean game over state management:
                * Show score and high score
                * Provide restart button that properly resets game state
                * Clear all previous game over messages
                * Reset snake position, length, and speed
                * Remove any lingering UI elements

                Visual Polish:
                - Subtle grid pattern on background
                - Smooth snake movement animation
                - Simple particle effect when eating
                - Clean, minimal UI elements
                - Game over screen:
                * Semi-transparent overlay
                * Centered game over message
                * Score display
                * Clear restart button
                * Fade in/out transitions

                State Management:
                - Proper cleanup of event listeners on game over
                - Complete state reset on restart
                - Separate game state from UI state
                - Clear separation of game logic and rendering
                - Proper handling of animation frames

                Additional Features:
                - High score persistence using localStorage
                - Quick restart with spacebar or click
                - Brief tutorial on first launch
                - Mobile-friendly touch controls

                Technical Implementation:
                - Use HTML5 Canvas for rendering
                - Implement requestAnimationFrame for smooth animation
                - Proper event listener cleanup
                - Modular code structure with separate game state management
                - Clean initialization and reset functions

                Please generate this game using HTML5 Canvas and JavaScript, ensuring proper state cleanup and reset functionality."""
            )
            st.session_state["generate_game"] = True
        if st.button("🧱 Breakout Clone"):
            add_message(
                "user",
                """Generate a polished Breakout clone with the following specifications:

                Core Mechanics:
                - Smooth paddle movement using arrow keys or mouse
                - Physics-based ball movement with realistic bouncing
                - Multiple colored block types with different properties
                - Responsive and precise collision detection
                - Power-up system with special effects

                Gameplay Features:
                - Multiple levels with increasing difficulty
                - Score system with multipliers for combos
                - Lives system with visual indicators
                - Progressive block patterns per level
                - Game state management:
                * Proper level transitions
                * Clean game over handling
                * Score and lives display
                * Pause functionality
                * Level completion celebrations

                Visual Polish:
                - Smooth animations for block destruction
                - Particle effects for collisions
                - Dynamic background patterns
                - Clean, modern UI elements
                - Visual feedback:
                * Ball trail effects
                * Paddle hit animations
                * Power-up indicators
                * Score popups

                State Management:
                - Proper game state transitions
                - Clean event listener handling
                - Separate game logic and rendering
                - Efficient collision detection system
                - Save/load system for progress

                Additional Features:
                - High score leaderboard using localStorage
                - Quick restart option
                - Level select after completion
                - Mobile touch controls
                - Adaptive difficulty system

                Technical Implementation:
                - HTML5 Canvas for rendering
                - RequestAnimationFrame for smooth animation
                - Efficient collision detection algorithms
                - Modular code architecture
                - Clean state management system

                Please implement using HTML5 Canvas and JavaScript with proper state management."""
            )
            st.session_state["generate_game"] = True
        if st.button("👾 Space Invaders"):
            add_message(
                "user",
                """Generate a retro-style Space Invaders game with these specifications:

                Core Mechanics:
                - Precise spaceship control with arrow keys
                - Multiple enemy types with different behaviors
                - Shooting mechanics with space bar
                - Shield/bunker system with degradation
                - Enemy formation movement patterns

                Gameplay Features:
                - Wave-based progression system
                - Score multiplier for higher enemies
                - Special mystery ship appearances
                - Shield damage visualization
                - Game state handling:
                * Wave transitions
                * Game over conditions
                * Score tracking
                * Lives system
                * Power-up management

                Visual Polish:
                - Retro pixel art style
                - Explosion animations
                - Laser beam effects
                - Enemy animation cycles
                - UI Elements:
                * Score display
                * Lives counter
                * Wave indicator
                * High score table
                * Power-up indicators

                State Management:
                - Enemy formation tracking
                - Projectile management
                - Collision detection system
                - Power-up state handling
                - Clean game reset functionality

                Additional Features:
                - High score persistence
                - Difficulty progression
                - Two-player mode option
                - Mobile-friendly controls
                - Achievement system

                Technical Implementation:
                - HTML5 Canvas rendering
                - Efficient sprite management
                - Collision optimization
                - State machine architecture
- Clean code organization

        Please create using HTML5 Canvas and JavaScript with proper state handling."""
            )
            st.session_state["generate_game"] = True
        if st.button("🦘 Simple Platformer"):
            add_message(
                "user",
                """Generate a charming platformer game with these specifications:

            Core Mechanics:
            - Smooth character movement physics
            - Jump mechanics with variable height
            - Platform collision detection
            - Collectible items system
            - Enemy interaction mechanics

            Gameplay Features:
            - Multiple level designs
            - Checkpoint system
            - Score tracking
            - Health/lives system
            - Game state management:
            * Level progression
            * Death/respawn handling
            * Checkpoint saving
            * Score calculation
            * Power-up duration

            Visual Polish:
            - Cheerful art style
            - Character animations:
            * Running
            * Jumping
            * Landing
            * Collecting items
            - Background parallax effects
            - Environmental animations
            - UI Elements:
            * Health/lives display
            * Score counter
            * Level indicator
            * Collectibles count
            * Power-up status
            
            State Management:
            - Character state tracking
            - Level progression system
            - Collision handling
            - Power-up management
            - Clean reset functionality

            Additional Features:
            - Progress saving
            - Level select menu
            - Tutorial system
            - Mobile touch controls
            - Achievement tracking

            Technical Implementation:
            - HTML5 Canvas rendering
            - Efficient sprite animation
            - Collision optimization
            - State machine design
            - Modular level loading

            Please implement using HTML5 Canvas and JavaScript with proper state management."""
            )
            st.session_state["generate_game"] = True

def session_management_widget(agent: Agent, model_id: str) -> None:
    """Display a session selector and rename option in the sidebar"""

    if agent.storage:
        agent_sessions = agent.storage.get_all_sessions()
        # Get session names if available, otherwise use IDs
        session_options = []
        for session in agent_sessions:
            session_id = session.session_id
            session_name = (
                session.session_data.get("session_name", None)
                if session.session_data
                else None
            )
            display_name = session_name if session_name else session_id
            session_options.append({"id": session_id, "display": display_name})

        # Display session selector
        selected_session_display = st.sidebar.selectbox(
            "Session",
            options=[s["display"] for s in session_options],
            key="session_selector",
        )
        # Find the selected session object
        selected_session = next(
            session for session in agent_sessions if session_options[agent_sessions.index(session)]["display"] == selected_session_display
        )

        # Initialize session_edit_mode if needed
        if "session_edit_mode" not in st.session_state:
            st.session_state.session_edit_mode = False

        container = st.sidebar.container()
        session_row = container.columns([3, 1], vertical_alignment="center")

        with session_row[0]:
            if st.session_state.session_edit_mode:
                new_session_name = st.text_input(
                    "Session Name",
                    value=agent.session_name,
                    key="session_name_input",
                    label_visibility="collapsed",
                )
            else:
                st.markdown(f"Session Name: **{agent.session_name}**")

        with session_row[1]:
            if st.session_state.session_edit_mode:
                if st.button("✓", key="save_session_name", type="primary"):
                    if new_session_name:
                        agent.rename_session(new_session_name)
                        st.session_state.session_edit_mode = False
                        st.success("Renamed!")
                        st.rerun()  # Reload the session selector to update
            else:
                if st.button("✎", key="edit_session_name"):
                    st.session_state.session_edit_mode = True
                    st.rerun()  # Reload the session selector to update

        # Only reload the agent if a different session is selected
        if st.session_state.get("game_generator_agent_session_id") != selected_session.session_id:
            logger.info(
                f"---*--- Loading {model_id} run: {selected_session.session_id} ---*---"
            )
            agent.load_agent_session(selected_session)
            st.session_state["game_generator_agent_session_id"] = selected_session.session_id

            # Load messages from memory and ensure they are correctly validated
            st.session_state["messages"] = []
            for message in agent.memory.messages:
                st.session_state["messages"].append({"role": message.role, "content": message.content})

            st.rerun()

def about_widget() -> None:
    """Display an about section in the Streamlit app."""
    st.sidebar.markdown("## About")
    st.sidebar.info(
        """
        **Game Generator** is a tool for creating simple HTML5 games.
        Built using [Agno](https://github.com/agno-agi/agno).
        
        - **Author**: Your Name
        - **Version**: 1.0.0
        - **License**: MIT
        """
    )

CUSTOM_CSS = """
    <style>
    /* Main Styles */
    .main-title {
        text-align: center;
        background: linear-gradient(45deg, #FF4B2B, #FF416C);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3em;
        font-weight: bold;
        padding: 1em 0;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2em;
    }
    .stButton button {
        width: 100%;
        border-radius: 20px;
        margin: 0.2em 0;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .chat-container {
        border-radius: 15px;
        padding: 1em;
        margin: 1em 0;
        background-color: #f5f5f5;
    }
    .sql-result {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1em;
        margin: 1em 0;
        border-left: 4px solid #FF4B2B;
    }
    .status-message {
        padding: 1em;
        border-radius: 10px;
        margin: 1em 0;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
    }
    /* Dark mode adjustments */
    @media (prefers-color-scheme: dark) {
        .chat-container {
            background-color: #2b2b2b;
        }
        .sql-result {
            background-color: #1e1e1e;
        }
    }
    </style>
""" 