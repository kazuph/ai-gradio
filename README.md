# ai-gradio

A Python package that makes it easy for developers to create machine learning apps powered by various AI providers.

## Table of Contents
- [Installation](#installation)
- [Supported Providers](#supported-providers)
- [Basic Usage](#basic-usage)
- [Features](#features)
- [Model Support](#model-support)
- [Requirements](#requirements)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)

## Installation

Install with specific provider support:

```bash
# Core providers
pip install 'ai-gradio[openai]'     # OpenAI support
pip install 'ai-gradio[gemini]'     # Google Gemini support
pip install 'ai-gradio[anthropic]'  # Anthropic Claude support
pip install 'ai-gradio[groq]'       # Groq support

# Additional providers
pip install 'ai-gradio[crewai]'     # CrewAI support
pip install 'ai-gradio[lumaai]'     # LumaAI support
pip install 'ai-gradio[xai]'        # XAI/Grok support
pip install 'ai-gradio[cohere]'     # Cohere support
pip install 'ai-gradio[sambanova]'  # SambaNova support
pip install 'ai-gradio[hyperbolic]' # Hyperbolic support
pip install 'ai-gradio[deepseek]'   # DeepSeek support
pip install 'ai-gradio[smolagents]' # SmolagentsAI support
pip install 'ai-gradio[fireworks]'  # Fireworks support
pip install 'ai-gradio[together]'   # Together support
pip install 'ai-gradio[qwen]'       # Qwen support

# Install all providers
pip install 'ai-gradio[all]'
```

## Basic Usage

### API Key Configuration
```bash
# Core Providers
export OPENAI_API_KEY=<your token>
export GEMINI_API_KEY=<your token>
export ANTHROPIC_API_KEY=<your token>
export GROQ_API_KEY=<your token>

# Additional Providers
export LUMAAI_API_KEY=<your token>
export XAI_API_KEY=<your token>
export COHERE_API_KEY=<your token>
export SAMBANOVA_API_KEY=<your token>
export HYPERBOLIC_API_KEY=<your token>
export DEEPSEEK_API_KEY=<your token>
export FIREWORKS_API_KEY=<your token>
export TOGETHER_API_KEY=<your token>
export QWEN_API_KEY=<your token>
```

### Quick Start
```python
import gradio as gr
import ai_gradio

# Create a Gradio interface
gr.load(
    name='openai:gpt-4-turbo',  # or 'gemini:gemini-1.5-flash', 'groq:llama-3.2-70b-chat'
    src=ai_gradio.registry,
    title='AI Chat',
    description='Chat with an AI model'
).launch()
```

## Features

### Core Features
- Text Chat: Supported across all text models
- Voice Chat: Available for OpenAI realtime models
- Video Chat: Available for Gemini models
- Code Generation: Specialized interfaces for coding assistance
- Multi-Modal: Support for text, image, and video inputs
- Agent Teams: CrewAI integration for collaborative AI tasks

### Voice Chat Configuration
```python
# Using a realtime model
gr.load(
    name='openai:gpt-4o-realtime-preview',
    src=ai_gradio.registry,
    enable_voice=True,
    title='Voice Chat'
).launch()
```

Required credentials for voice chat:
```bash
# Required
export OPENAI_API_KEY=<your OpenAI token>

# Optional (recommended for better WebRTC)
export TWILIO_ACCOUNT_SID=<your Twilio account SID>
export TWILIO_AUTH_TOKEN=<your Twilio auth token>
```

### Model-Specific Features

#### Gemini Code Generator
```python
gr.load(
    name='gemini:gemini-pro',
    src=ai_gradio.registry,
    coder=True,
    title='Gemini Code Generator'
).launch()
```

#### CrewAI Teams
```python
# Article Creation Team
gr.load(
    name='crewai:gpt-4-turbo',
    src=ai_gradio.registry,
    crew_type='article',
    title='AI Writing Team'
).launch()

# Support Team
gr.load(
    name='crewai:gpt-4-turbo',
    src=ai_gradio.registry,
    crew_type='support',
    title='AI Support Team'
).launch()
```

## Model Support

### Language Models
| Provider | Models |
|----------|---------|
| OpenAI | gpt-4-turbo, gpt-4, gpt-3.5-turbo |
| Anthropic | claude-3-opus, claude-3-sonnet, claude-3-haiku |
| Gemini | gemini-pro, gemini-pro-vision, gemini-2.0-flash-exp |
| Groq | llama-3.2-70b-chat, mixtral-8x7b-chat |

### Specialized Models
| Provider | Type | Models |
|----------|------|---------|
| LumaAI | Generation | dream-machine, photon-1 |
| DeepSeek | Multi-purpose | deepseek-chat, deepseek-coder, deepseek-vision |
| CrewAI | Agent Teams | Support Team, Article Team |
| Qwen | Language | qwen-turbo, qwen-plus, qwen-max |

## Requirements

### Core Requirements
- Python 3.10+
- gradio >= 5.9.1

### Optional Features
- Voice Chat: gradio-webrtc, numba==0.60.0, pydub, librosa
- Video Chat: opencv-python, Pillow
- Agent Teams: crewai>=0.1.0, langchain>=0.1.0

## Troubleshooting

### Authentication Issues
If you encounter 401 errors, verify your API keys:

```python
import os

# Set API keys manually if needed
os.environ["OPENAI_API_KEY"] = "your-api-key"
os.environ["GEMINI_API_KEY"] = "your-api-key"
# ... other provider keys as needed
```

### Provider Installation
If you see "no providers installed" errors:
```bash
# Install specific provider
pip install 'ai-gradio[provider_name]'

# Or install all providers
pip install 'ai-gradio[all]'
```

## Examples

### Multi-Provider Interface
```python
import gradio as gr
import ai_gradio

with gr.Blocks() as demo:
    with gr.Tab("Text"):
        gr.load('openai:gpt-4-turbo', src=ai_gradio.registry)
    with gr.Tab("Vision"):
        gr.load('gemini:gemini-pro-vision', src=ai_gradio.registry)
    with gr.Tab("Code"):
        gr.load('deepseek:deepseek-coder', src=ai_gradio.registry)

demo.launch()
```

### Voice-Enabled Assistant
```python
gr.load(
    name='openai:gpt-4-turbo',
    src=ai_gradio.registry,
    enable_voice=True,
    title='AI Voice Assistant'
).launch()
```






