import gradio as gr
import ai_gradio

gr.load(
    name='transformers:facebook/opt-350m',
    src=ai_gradio.registry
).launch()

