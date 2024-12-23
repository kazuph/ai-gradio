import gradio as gr
import ai_gradio

# Create a Gradio interface
interface = gr.load(
    name='xai:grok-beta',
    src=ai_gradio.registry,
).launch()
