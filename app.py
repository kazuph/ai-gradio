import gradio as gr
import ai_gradio

# Create a Gradio interface
interface = gr.load(
    name='hyperbolic:deepseek-ai/DeepSeek-V3',
    src=ai_gradio.registry,
).launch()
