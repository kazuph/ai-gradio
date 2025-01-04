import gradio as gr
import ai_gradio

gr.load(
    name='deepseek:deepseek-chat',
    src=ai_gradio.registry,
).launch()

