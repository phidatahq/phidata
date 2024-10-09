from typing import Optional

from phi.assistant import Assistant
from phi.llm.openai import OpenAIChat

from ai.settings import ai_settings
from ai.storage import image_assistant_storage


def get_image_assistant(
    run_id: Optional[str] = None,
    user_id: Optional[str] = None,
    debug_mode: bool = False,
) -> Assistant:
    """Get an Image Assistant"""

    return Assistant(
        name="image_assistant",
        run_id=run_id,
        user_id=user_id,
        llm=OpenAIChat(
            model=ai_settings.gpt_4_vision,
            max_tokens=ai_settings.default_max_tokens,
            temperature=ai_settings.default_temperature,
        ),
        storage=image_assistant_storage,
        # Enable monitoring on phidata.app
        # monitoring=True,
        debug_mode=debug_mode,
        assistant_data={"assistant_type": "multimodal"},
    )
