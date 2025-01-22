import gradio as gr
import ai_gradio


gr.load(
    name='gemini:gemini-2.0-flash-thinking-exp-01-21',
    src=ai_gradio.registry,
    coder=True
).launch()
