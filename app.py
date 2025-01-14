import gradio as gr
import ai_gradio

demo = gr.load(
    "browser:gpt-4o-2024-11-20",  
    src=ai_gradio.registry,
)

demo.launch()