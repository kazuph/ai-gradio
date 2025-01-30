import gradio as gr
import ai_gradio


gr.load(
    name='together:deepseek-ai/DeepSeek-V3',
    src=ai_gradio.registry,
).launch()
