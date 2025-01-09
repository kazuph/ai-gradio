import gradio as gr
import ai_gradio

gr.load(
    name='transformers:moondream',
    src=ai_gradio.registry
).launch()
