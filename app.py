import gradio as gr
import ai_gradio

# Create a chat interface with Swarms
gr.load(
    name='swarms:gpt-4o-mini',
    src=ai_gradio.registry,
    agent_name="Stock-Analysis-Agent",
    title='Swarms Chat'
).launch()