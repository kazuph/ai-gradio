import gradio as gr
import ai_gradio


gr.load(
    name='kokoro:kokoro-v0_19',
    src=ai_gradio.registry,
).launch()
