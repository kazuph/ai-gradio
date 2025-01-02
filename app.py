import gradio as gr
import ai_gradio

gr.load(
    name='crewai:gpt-4-turbo',
    src=ai_gradio.registry
).launch()

