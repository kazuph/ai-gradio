import gradio as gr
from ai_gradio import registry

# Create a Gradio interface
interface = gr.load(
    name='gpt-4o-mini-realtime-preview-2024-12-17',  # or 'gemini-pro' for Gemini
    src=registry,
    title='openai chat',
    description='Chat with an AI model',
    enable_voice=True,
).launch()
