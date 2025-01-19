# Getting Started with Agno 🚀

This folder contains introductory recipes for building Agents with Agno. Each recipe builds on the previous one, introducing new concepts and capabilities. Each recipe contains detailed comments, example prompts and required dependencies.

## Setup

Create a virtual environment and install the required dependencies:

```bash
python -m venv .venv
source .venv/bin/activate

pip install openai duckduckgo-search yfinance lancedb tantivy pypdf requests agno
```

Export your OpenAI API key:

```bash
export OPENAI_API_KEY=your_api_key
```

## Examples Overview

### 1. Basic Agent (`01_basic_agent.py`)
- Creates a simple news reporter agent with personality
- Demonstrates basic agent configuration and responses
- Shows how to customize agent instructions and style

Run this recipe using:
```bash
python cookbook/getting_started/01_basic_agent.py
```

### 2. Agent with Tools (`02_agent_with_tools.py`)
- Enhances news reporter with web searching capabilities
- Shows how to integrate DuckDuckGo search tool
- Demonstrates real-time information gathering

Run this recipe using:
```bash
python cookbook/getting_started/02_agent_with_tools.py
```

### 3. Agent with Knowledge (`03_agent_with_knowledge.py`)
- Creates a Thai cooking expert with recipe knowledge base
- Combines local knowledge with web searches
- Shows vector database integration for information retrieval

Run this recipe using:
```bash
python cookbook/getting_started/03_agent_with_knowledge.py
```

### 4. Agent Team (`04_agent_team.py`)
- Implements a financial analysis team with web and finance agents
- Shows agent collaboration and role specialization
- Combines market research with financial data analysis

Run this recipe using:
```bash
python cookbook/getting_started/04_agent_team.py
```

### 5. Structured Output (`05_structured_output.py`)
- Creates a movie script generator with structured outputs
- Shows how to use Pydantic models for response validation
- Demonstrates both JSON mode and structured output formats

Run this recipe using:
```bash
python cookbook/getting_started/05_structured_output.py
```

### 6. Custom Tools (`06_write_your_own_tool.py`)
- Shows how to create custom tools using Hacker News API

Run this recipe using:
```bash
python cookbook/getting_started/06_write_your_own_tool.py
```

### 7. Image Agent (`07_image_agent.py`)
- Creates a visual journalist for image analysis
- Combines image understanding with web searches
- Shows how to process and analyze images

Run this recipe using:
```bash
python cookbook/getting_started/07_image_agent.py
```

### 8. Image Generation (`08_generate_image.py`)
- Implements an AI artist using DALL-E
- Shows prompt engineering for image generation
- Demonstrates handling generated image outputs

Run this recipe using:
```bash
python cookbook/getting_started/08_generate_image.py
```

### 9. Video Generation (`09_generate_video.py`)
- Creates an AI video director using ModelsLabs
- Shows video prompt engineering techniques
- Demonstrates video generation and handling

Run this recipe using:
```bash
python cookbook/getting_started/09_generate_video.py
```

### 10. Audio Input/Output (`10_audio_input_output.py`)
- Creates a voice interaction specialist
- Shows how to process audio input and generate responses
- Demonstrates audio file handling capabilities

Run this recipe using:
```bash
python cookbook/getting_started/10_audio_input_output.py
```

### 11. Human-in-the-Loop (`11_human_in_the_loop.py`)
- Adds user confirmation to tool execution
- Shows how to implement safety checks
- Demonstrates interactive agent control

Run this recipe using:
```bash
python cookbook/getting_started/11_human_in_the_loop.py
```
