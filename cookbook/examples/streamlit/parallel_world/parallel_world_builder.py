import os
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from phi.agent import Agent
from phi.model.openai import OpenAIChat

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class World(BaseModel):
    name: str = Field(
        ...,
        description=(
            "The name of this world. Be exceptionally creative and unique. "
            "Avoid using simple names like Futura, Earth, or other common names."
        ),
    )
    characteristics: List[str] = Field(
        ...,
        description=(
            "Key attributes of the world. Examples: Ethereal, Arcane, Quantum-Fueled, "
            "Dreamlike, Mechanized, Harmonious. Think outside the box."
        ),
    )
    currency: str = Field(
        ...,
        description=(
            "The monetary system or trade medium in the world. "
            "Consider unusual or symbolic currencies (e.g., Memory Crystals, Void Shards)."
        ),
    )
    languages: List[str] = Field(
        ...,
        description=(
            "The languages spoken in the world. Invent languages with unique phonetics, "
            "scripts, or origins. Examples: Elurian, Syneth, Aeon's Glyph."
        ),
    )
    history: str = Field(
        ...,
        description=(
            "The detailed history of the world spanning at least 100,000 years. "
            "Include pivotal events, revolutions, cataclysms, golden ages, and more. "
            "Make it immersive and richly detailed."
        ),
    )
    wars: List[str] = Field(
        ...,
        description=(
            "List of major wars or conflicts that shaped the world. Each should have unique "
            "motivations, participants, and consequences."
        ),
    )
    drugs: List[str] = Field(
        ...,
        description=(
            "Substances used in the world, either recreationally, medically, or spiritually. "
            "Invent intriguing names and effects (e.g., Lunar Nectar, Dreamweaver Elixir)."
        ),
    )


def get_world_builder(
    model: str = "gpt-4o-mini",
    debug_mode: bool = False,
) -> Agent:
    return Agent(
        name="world_builder",
        model=OpenAIChat(id=model),
        description="An expert world creator focused on crafting intricate, imaginative worlds.",
        instructions=[
            "You are tasked with creating an entirely unique and intricate world.",
            "Your world must captivate and enthrall anyone who hears about it.",
            "Push the boundaries of creativity to design something truly unforgettable.",
            "Think of extraordinary characteristics, histories, and features to bring the world to life.",
            "Use rich, vivid language to describe your ideas and inspire exploration.",
        ],
        response_model=World,
        debug_mode=debug_mode,
    )
