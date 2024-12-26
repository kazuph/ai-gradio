import gradio as gr
import ai_gradio

# Create a Gradio interface
interface = gr.load(
    name='together:meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo',
    src=ai_gradio.registry,
).launch()
