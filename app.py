import gradio as gr
import ai_gradio


gr.load(
    name='openai:gpt-4o',
    src=ai_gradio.registry,
).launch()
