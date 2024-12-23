import gradio as gr
from ai_gradio import registry

# Create a Gradio interface
interface = gr.load(
    name='gpt-4-turbo',  # or 'gemini-pro' for Gemini
    src=registry,
    title='openai chat',
    description='Chat with an AI model'
).launch()