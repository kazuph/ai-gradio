import gradio as gr
import ai_gradio

gr.load(
    name='groq:llama-3.2-11b-vision-preview',
    src=ai_gradio.registry
).launch()

