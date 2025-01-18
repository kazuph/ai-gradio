import gradio as gr
import ai_gradio

gr.load(
    name='nvidia:nvidia/cosmos-nemotron-34b',
    src=ai_gradio.registry,
).launch()
