import gradio as gr
from ai_gradio import registry

# Create a Gradio interface
interface = gr.load(
    name='crewai:gpt-4-turbo',
    src=registry,
    crew_type='article',  # or 'support'
    title='AI Writing Team',
    description='Create articles with a team of AI agents'
).launch()
