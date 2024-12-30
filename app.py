import gradio as gr
import ai_gradio

gr.load(
    name='gemini:gemini-1.5-flash',
    src=ai_gradio.registry,
).launch()
