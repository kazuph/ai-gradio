import gradio as gr
import ai_gradio

demo = gr.load(
    name='minimax:MiniMax-Text-01',
    src=ai_gradio.registry,
)
demo.launch()