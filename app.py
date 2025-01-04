import gradio as gr
import ai_gradio

demo = gr.load(
    name='browser:gpt-4-turbo',
    src=ai_gradio.registry,
    title='Browser Agent',
    description='AI agent that can interact with web browsers'
).launch()