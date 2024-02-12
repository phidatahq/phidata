Note: Fork and clone this repository if needed

Create a virtual environment
  python3 -m venv ~/.venvs/aienv
  source ~/.venvs/aienv/bin/activate

Install libraries
  pip install -U anyscale phidata

Test Anyscale Assistant
  Streaming
    python cookbook/anyscale/assistant.py
  Without Streaming
    python cookbook/anyscale/assistant_stream_off.py

Test Structured output
  python cookbook/anyscale/pydantic_output.py

Test function calling
python cookbook/anyscale/tool_call.py
