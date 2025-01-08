import gradio as gr
import ai_gradio

gr.load(
    name='transformers:phi-4',
    src=ai_gradio.registry
).launch()
