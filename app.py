import gradio as gr
import ai_gradio

# Load the Jupyter agent with a specific model
demo = gr.load(
    "groq:llama-3.3-70b-versatile",  # Format: "jupyter:{model_name}"
    src=ai_gradio.registry
)

# Launch the interface
demo.launch()