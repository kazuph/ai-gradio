from smolagents import CodeAgent, DuckDuckGoSearchTool, HfApiModel
from smolagents.agents import ActionStep
import gradio as gr
from typing import Generator, List, Dict

def create_agent(model_name: str = None):
    model = HfApiModel(model_name) if model_name else HfApiModel()
    return CodeAgent(tools=[DuckDuckGoSearchTool()], model=model)

def stream_agent_response(agent: CodeAgent, prompt: str) -> Generator[Dict, None, None]:
    # First yield the thinking message
    yield {
        "role": "assistant",
        "content": "Let me think about that...",
        "metadata": {"title": "🤔 Thinking"}
    }
    
    # Run the agent and capture its response
    try:
        # Get the agent's response
        for step in agent.run(prompt, stream=True):
            if isinstance(step, ActionStep):
                # Show LLM output if present (as collapsible thought)
                if step.llm_output:
                    yield {
                        "role": "assistant",
                        "content": step.llm_output,
                        "metadata": {"title": "🧠 Thought Process"}
                    }
                
                # Show tool call if present
                if step.tool_call:
                    content = step.tool_call.arguments
                    if step.tool_call.name == "python_interpreter":
                        content = f"```python\n{content}\n```"
                    yield {
                        "role": "assistant",
                        "content": str(content),
                        "metadata": {"title": f"🛠️ Using {step.tool_call.name}"}
                    }
                
                # Show observations if present
                if step.observations:
                    yield {
                        "role": "assistant",
                        "content": f"```\n{step.observations}\n```",
                        "metadata": {"title": "👁️ Observations"}
                    }
                
                # Show errors if present
                if step.error:
                    yield {
                        "role": "assistant",
                        "content": str(step.error),
                        "metadata": {"title": "❌ Error"}
                    }
                
                # Show final output if present (without metadata to keep it expanded)
                if step.action_output is not None and not step.error:
                    # Only show the final output if it's actually the last step
                    if step == step.action_output:
                        yield {
                            "role": "assistant",
                            "content": str(step.action_output)
                        }
            else:
                # For any other type of step output
                yield {
                    "role": "assistant",
                    "content": str(step),
                    "metadata": {"title": "🔄 Processing"}
                }
                
    except Exception as e:
        yield {
            "role": "assistant",
            "content": f"Error: {str(e)}",
            "metadata": {"title": "❌ Error"}
        }

async def interact_with_agent(message: str, history: List, model_name: str = None) -> Generator[List, None, None]:
    # Add user message
    history.append({"role": "user", "content": message})
    yield history
    
    # Create agent instance with specified model
    agent = create_agent(model_name)
    
    # Stream agent responses
    for response in stream_agent_response(agent, message):
        history.append(response)
        yield history

def registry(name: str, **kwargs):
    # Extract model name from the name parameter
    model_name = name.split(':')[-1] if ':' in name else None
    
    with gr.Blocks() as demo:
        gr.Markdown("# SmolagentsAI Assistant 🤖")
        
        chatbot = gr.Chatbot(
            type="messages",
            label="Agent",
            avatar_images=(None, "https://cdn-lfs.hf.co/repos/96/a2/96a2c8468c1546e660ac2609e49404b8588fcf5a748761fa72c154b2836b4c83/9cf16f4f32604eaf76dabbdf47701eea5a768ebcc7296acc1d1758181f71db73?response-content-disposition=inline%3B+filename*%3DUTF-8%27%27hf-logo.png%3B+filename%3D%22hf-logo.png%22%3B&response-content-type=image%2Fpng&Expires=1735927745&Policy=eyJTdGF0ZW1lbnQiOlt7IkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTczNTkyNzc0NX19LCJSZXNvdXJjZSI6Imh0dHBzOi8vY2RuLWxmcy5oZi5jby9yZXBvcy85Ni9hMi85NmEyYzg0NjhjMTU0NmU2NjBhYzI2MDllNDk0MDRiODU4OGZjZjVhNzQ4NzYxZmE3MmMxNTRiMjgzNmI0YzgzLzljZjE2ZjRmMzI2MDRlYWY3NmRhYmJkZjQ3NzAxZWVhNWE3NjhlYmNjNzI5NmFjYzFkMTc1ODE4MWY3MWRiNzM%7EcmVzcG9uc2UtY29udGVudC1kaXNwb3NpdGlvbj0qJnJlc3BvbnNlLWNvbnRlbnQtdHlwZT0qIn1dfQ__&Signature=a%7EGHhtB%7EWzd7pjl5F5wJHVxQPymZEQcgcAoc5FkJggZcWPDrcZ82CtDpIQafi0CultDPMy8SiZgHA0PDDk31c5a6wzdIbsbm7zZ5NvGTTlZpXskL3x7Gbr-f2E3yOA%7EHR%7E2heEJlpim78-xLqkWA92CYo-tKLg-yHKMx0acQcBvhptHOZtwlb9%7EyHlqlzNpcLo4iqEgEH39ADRNhpkf54-Zj6SQNBod7AkjFA3-iIzX5LVzW6EEYyFs03Ba0AfBUODgZIt8cjglULQ2a02rgiM%7EjKMBmB2eKNDFtvoe7YSGlFbVcLt21pWjhzA-z9MgQsw-U3ZDY539iHkMMkfoQzA__&Key-Pair-Id=K3RPWS32NSSJCE"),
            height=500
        )
        
        msg = gr.Textbox(
            label="Your message",
            placeholder="Type your message here...",
            lines=1
        )

        # Make the wrapper function async and await the generator
        async def handle_message(message, history):
            async for response in interact_with_agent(message, history, model_name=model_name):
                yield response

        msg.submit(
            fn=handle_message,
            inputs=[msg, chatbot],
            outputs=[chatbot],
            api_name="predict"
        )

    return demo