# `ai-gradio`

A Python package that makes it easy for developers to create machine learning apps powered by OpenAI, Google's Gemini models, and CrewAI.

## Installation

You can install `ai-gradio` with different providers:

```bash
# Install with OpenAI support
pip install 'ai-gradio[openai]'

# Install with Gemini support  
pip install 'ai-gradio[gemini]'

# Install with CrewAI support
pip install 'ai-gradio[crewai]'

# Install with all providers
pip install 'ai-gradio[all]'
```

## Basic Usage

First, set your API key in the environment:

For OpenAI:
```bash
export OPENAI_API_KEY=<your token>
```

For Gemini:
```bash
export GEMINI_API_KEY=<your token>
```

Then in a Python file:

```python
import gradio as gr
from ai_gradio import registry

# Create a Gradio interface
interface = gr.load(
    name='gpt-4-turbo',  # or 'gemini-pro' for Gemini
    src=registry,
    title='AI Chat',
    description='Chat with an AI model'
).launch()
```

## Features

### Text Chat
Basic text chat is supported for all models. The interface provides a chat-like experience where you can have conversations with the AI model.

### Voice Chat (OpenAI only)
Voice chat is supported for OpenAI models. You can enable it by setting `enable_voice=True`:

```python
interface = gr.load(
    name='gpt-4-turbo',
    src=registry,
    enable_voice=True
).launch()
```

### Video Chat (Gemini only)
Video chat is supported for Gemini models. You can enable it by setting `enable_video=True`:

```python
interface = gr.load(
    name='gemini-pro',
    src=registry,
    enable_video=True
).launch()
```

### AI Agent Teams with CrewAI
CrewAI support allows you to create teams of AI agents that work together to solve complex tasks. Enable it by using the CrewAI provider:

```python
interface = gr.load(
    name='crewai:gpt-4-turbo',
    src=registry,
    title='AI Team Chat',
    description='Chat with a team of specialized AI agents'
).launch()
```

### CrewAI Types
The CrewAI integration supports different specialized agent teams:

- `support`: A team of support agents that help answer questions, including:
  - Senior Support Representative
  - Support Quality Assurance Specialist

- `article`: A team of content creation agents, including:
  - Content Planner
  - Content Writer
  - Editor

You can specify the crew type when creating the interface:

```python
interface = gr.load(
    name='crewai:gpt-4-turbo',
    src=registry,
    crew_type='article',  # or 'support'
    title='AI Writing Team',
    description='Create articles with a team of AI agents'
).launch()
```

When using the `support` crew type, you can provide a documentation URL that the agents will reference when answering questions. The interface will automatically show a URL input field.

### Customization

You can customize the interface by adding examples, changing the title, or adding a description:

```python
interface = gr.load(
    name='gpt-4-turbo',
    src=registry,
    title='Custom AI Chat',
    description='Chat with an AI assistant',
    examples=[
        "Explain quantum computing to a 5-year old",
        "What's the difference between machine learning and AI?"
    ]
).launch()
```

### Composition

You can combine multiple models in a single interface using Gradio's Blocks:

```python
import gradio as gr
from ai_gradio import registry

with gr.Blocks() as demo:
    with gr.Tab("GPT-4"):
        gr.load('gpt-4-turbo', src=registry)
    with gr.Tab("Gemini"):
        gr.load('gemini-pro', src=registry)
    with gr.Tab("CrewAI"):
        gr.load('crewai:gpt-4-turbo', src=registry)

demo.launch()
```

## Supported Models

### OpenAI Models
- gpt-4-turbo
- gpt-4
- gpt-3.5-turbo

### Gemini Models
- gemini-pro
- gemini-pro-vision

### CrewAI Models
- crewai:gpt-4-turbo
- crewai:gpt-4
- crewai:gpt-3.5-turbo

## Requirements

- Python 3.10 or higher
- gradio >= 5.9.1

Additional dependencies are installed based on your chosen provider:
- OpenAI: `openai>=1.58.1`
- Gemini: `google-generativeai`
- CrewAI: `crewai>=0.1.0`, `langchain>=0.1.0`, `langchain-openai>=0.0.2`

## Troubleshooting

If you get a 401 authentication error, make sure your API key is properly set. You can set it manually in your Python session:

```python
import os

# For OpenAI
os.environ["OPENAI_API_KEY"] = "your-api-key"

# For Gemini
os.environ["GEMINI_API_KEY"] = "your-api-key"
```

### No Providers Error
If you see an error about no providers being installed, make sure you've installed the package with the desired provider:

```bash
# Install with OpenAI support
pip install 'ai-gradio[openai]'

# Install with Gemini support
pip install 'ai-gradio[gemini]'

# Install with CrewAI support
pip install 'ai-gradio[crewai]'

# Install all providers
pip install 'ai-gradio[all]'
```

## Optional Dependencies

For voice chat functionality:
- gradio-webrtc
- numba==0.60.0
- pydub
- librosa
- websockets
- twilio

For video chat functionality:
- opencv-python
- Pillow
