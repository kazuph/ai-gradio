import gradio as gr
import ai_gradio


gr.load(
    name='qwen:qwen2.5-14b-instruct-1m',
    src=ai_gradio.registry
).launch()
