import gradio as gr
import ai_gradio

# Create a Gradio interface
interface = gr.load(
    name='anthropic:claude-3-opus-20240229',
    src=ai_gradio.registry,
).launch()
