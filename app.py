import gradio as gr
import ai_gradio

gr.load(
    name='hyperbolic:deepseek-ai/DeepSeek-V3',
    src=ai_gradio.registry,
    coder=True
).launch()
