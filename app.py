import gradio as gr
import ai_gradio

demo = gr.load(
    "mistral:codestral-latest",  
    src=ai_gradio.registry,
    coder=True
)

demo.launch()