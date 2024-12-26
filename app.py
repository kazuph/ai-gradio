import gradio as gr
import ai_gradio

# Create a Gradio interface
interface = gr.load(
    name='deepseek:deepseek-chat',
    src=ai_gradio.registry,
).launch()
