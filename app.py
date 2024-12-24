import gradio as gr
import ai_gradio

# Create a Gradio interface
interface = gr.load(
    name='cohere:command-r7b-12-2024',
    src=ai_gradio.registry,
).launch()
