import gradio as gr
import ai_gradio


gr.load(
    name='groq:deepseek-r1-distill-llama-70b',
    src=ai_gradio.registry,
    coder=True
).launch()