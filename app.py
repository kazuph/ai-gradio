import gradio as gr
import ai_gradio


gr.load(
    name='hyperbolic:deepseek-ai/DeepSeek-R1-Zero',
    src=ai_gradio.registry,
    coder=True
).launch()