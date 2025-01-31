import gradio as gr
import ai_gradio


gr.load(
    name='replicate:deepseek-ai/deepseek-r1',
    src=ai_gradio.registry,
).launch()
