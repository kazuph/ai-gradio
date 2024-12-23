import gradio as gr
import ai_gradio

# Create a Gradio interface
interface = gr.load(
    name='lumaai:dream-machine',
    src=ai_gradio.registry,
).launch()
