import gradio as gr
import ai_gradio

# Create a Gradio interface
interface = gr.load(
    name='sambanova:Meta-Llama-3.3-70B-Instruct',
    src=ai_gradio.registry,
).launch()
