import gradio as gr
import ai_gradio

demo = gr.load(
    name='gemini:gemini-2.0-flash-thinking-exp-1219',
    src=ai_gradio.registry,
).launch()