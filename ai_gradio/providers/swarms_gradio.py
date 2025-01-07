from swarms import Agent
from swarm_models import OpenAIChat
import gradio as gr
from typing import Generator, List, Dict, Callable
import base64
import os

__version__ = "0.0.1"

def get_fn(model_name: str, preprocess: Callable, postprocess: Callable, api_key: str, agent_name: str = "Assistant"):
    def fn(message, history):
        inputs = preprocess(message, history)
        agent = create_agent(model_name, agent_name)
        
        try:
            for response in stream_agent_response(agent, inputs["message"]):
                yield postprocess(response)
        except Exception as e:
            yield postprocess({
                "role": "assistant",
                "content": f"Error: {str(e)}",
                "metadata": {"title": "❌ Error"}
            })
    
    return fn

def get_interface_args(pipeline):
    if pipeline == "chat":
        def preprocess(message, history):
            messages = []
            for user_msg, assistant_msg in history:
                if assistant_msg is not None:
                    messages.append({"role": "user", "content": user_msg})
                    messages.append({"role": "assistant", "content": assistant_msg})
            messages.append({"role": "user", "content": message})
            return {"message": message, "history": messages}

        def postprocess(response):
            return response

        return None, None, preprocess, postprocess
    else:
        raise ValueError(f"Unsupported pipeline type: {pipeline}")

def create_agent(model_name: str = None, agent_name: str = "Assistant", system_prompt: str = None):
    """Create a Swarms Agent with the specified model and configuration"""
    model = OpenAIChat(model_name=model_name) if model_name else OpenAIChat()
    
    return Agent(
        agent_name=agent_name,
        system_prompt=system_prompt or "You are a helpful AI assistant.",
        llm=model,
        max_loops=1,
        autosave=False,
        dashboard=False,
        verbose=True,
        dynamic_temperature_enabled=True,
        streaming_on=True,
        saved_state_path=f"{agent_name.lower()}_state.json",
        user_name="gradio_user",
        retry_attempts=1,
        context_length=200000,
        return_step_meta=False,
        output_type="string"
    )

def stream_agent_response(agent: Agent, prompt: str) -> Generator[Dict, None, None]:
    # Initial thinking message
    yield {
        "role": "assistant", 
        "content": "Let me think about that...",
        "metadata": {"title": "🤔 Thinking"}
    }
    
    try:
        # Get response from agent
        response = agent.run(prompt)
        
        # Stream final response
        yield {
            "role": "assistant",
            "content": response,
            "metadata": {"title": "💬 Response"}
        }
        
    except Exception as e:
        yield {
            "role": "assistant",
            "content": f"Error: {str(e)}",
            "metadata": {"title": "❌ Error"}
        }

def registry(name: str, token: str | None = None, agent_name: str = "Assistant", **kwargs):
    api_key = token or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("API key is not set. Please provide a token or set OPENAI_API_KEY environment variable.")

    pipeline = "chat"  # Swarms only supports chat for now
    inputs, outputs, preprocess, postprocess = get_interface_args(pipeline)
    fn = get_fn(name, preprocess, postprocess, api_key, agent_name)

    interface = gr.ChatInterface(fn=fn, **kwargs)
    return interface