import gradio as gr
import ai_gradio

# Create a Gradio interface
interface = gr.load(
    name='qwen:qvq-72b-preview',
    src=ai_gradio.registry,
).launch()
