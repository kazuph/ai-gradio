import gradio as gr
import ai_gradio


gr.load(
    name='qwen:qwen-max-0125',
    src=ai_gradio.registry,
).launch()