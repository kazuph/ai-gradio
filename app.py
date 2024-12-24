import gradio as gr
import ai_gradio

# Create a Gradio interface
interface = gr.load(
    name='hyperbolic:Qwen/QwQ-32B-Preview',
    src=ai_gradio.registry,
).launch()
