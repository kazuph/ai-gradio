import gradio as gr
import ai_gradio


gr.load(
    name='hyperbolic:deepseek-ai/DeepSeek-R1',
    src=ai_gradio.registry,
).launch()
