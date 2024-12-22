import gradio as gr
import ai_gradio

# For CrewAI
interface = gr.load(
    name='crewai:gpt-4-turbo',  # Explicitly use CrewAI provider
    src=ai_gradio.registry,
    crew_type="support"
).launch()