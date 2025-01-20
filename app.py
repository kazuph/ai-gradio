import gradio as gr
import ai_gradio


gr.load(
    name='deepseek:deepseek-reasoner',
    src=ai_gradio.registry,
    coder=True
).launch()
