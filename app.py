import gradio as gr
import ai_gradio

demo = gr.load(
    name='nvidia:nvidia/llama3-chatqa-1.5-70b',
    src=ai_gradio.registry,
)
demo.launch()