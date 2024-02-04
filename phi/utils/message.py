from typing import Dict, List, Union


def get_text_from_message(message: Union[List, Dict, str]) -> str:
    """Return the user texts from the message"""

    if isinstance(message, str):
        return message
    if isinstance(message, list):
        text_messages = []
        for m in message:
            m_type = m.get("type")
            if m_type is not None and isinstance(m_type, str):
                m_value = m.get(m_type)
                if m_value is not None and isinstance(m_value, str):
                    if m_type == "text":
                        text_messages.append(m_value)
                    # if m_type == "image_url":
                    #     text_messages.append(f"Image: {m_value}")
                    # else:
                    #     text_messages.append(f"{m_type}: {m_value}")
        if len(text_messages) > 0:
            return "\n".join(text_messages)
    return ""
