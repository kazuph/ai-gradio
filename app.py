import gradio as gr
import ai_gradio

gr.load(
    name='openai:gpt-4o-mini',
    src=ai_gradio.registry,
    coder=True
).launch()
