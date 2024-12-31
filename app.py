import gradio as gr
import ai_gradio

gr.load(
    name='smolagents:meta-llama/Llama-3.1-8B-Instruct',
    src=ai_gradio.registry
).launch()

