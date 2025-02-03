![image](https://github.com/user-attachments/assets/fe3c7fcd-a343-46c7-8612-9b14bf9e4808)

# 🎨 AI Gradio Code Generator

A Gradio-based interface that enables the generation of web applications using multiple AI providers.

## ✨ Features

- 🤖 Support for multiple AI providers (OpenAI, Anthropic, Google Gemini)
- ⚡️ Real-time web application generation
- 👀 Live preview of generated applications
- 💻 Code view toggle functionality

## 🚀 Installation

```bash
git clone https://github.com/kazuph/ai-gradio.git
cd ai-gradio
uv sync
```

## 🔑 Environment Variables

Set the following environment variables in your `.env` file:

```bash
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_API_KEY=your_google_api_key
```

## 📝 Usage

```bash
uv run python ai_gradio
```

Open http://localhost:7860 in your browser and:

1. Enter the specifications for your desired web application
2. Select the AI models you want to use
3. Click the Generate button

## 🤖 Supported Models

- OpenAI
- Anthropic
- Google Gemini

## 📋 Requirements

- Python 3.10+
- gradio >= 5.9.1






