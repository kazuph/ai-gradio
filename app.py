import gradio as gr
import ai_gradio

# Launch the Jupyter agent interface
demo = gr.load(
    "langchain:gpt-4-turbo",  # or other supported models
    src=ai_gradio.registry
)

demo.launch()