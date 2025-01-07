import gradio as gr
import ai_gradio

# Create a chat interface with Swarms
gr.load(
    name='openai:gpt-4o-realtime-preview-2024-10-01',
    src=ai_gradio.registry,
    enable_voice=True
).launch()
