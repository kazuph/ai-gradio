import gradio as gr
import ai_gradio


gr.load(
    name='together:mistralai/Mistral-Small-24B-Instruct-2501',
    src=ai_gradio.registry,
).launch()
