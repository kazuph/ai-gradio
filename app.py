import gradio as gr
import ai_gradio

gr.load(
    name='gemini:gemini-2.0-flash-exp',
    src=ai_gradio.registry,
    camera=True
).launch()
