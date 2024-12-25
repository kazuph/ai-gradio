import os
from openai import OpenAI
import gradio as gr
from typing import Callable

__version__ = "0.0.3"


def get_fn(model_name: str, preprocess: Callable, postprocess: Callable, api_key: str, base_url: str | None = None):
    def fn(message, history):
        inputs = preprocess(message, history)
        
        

        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        completion = client.chat.completions.create(
            model=model_name,
            messages=inputs["messages"],
            stream=True,
        )
        response_text = ""
        for chunk in completion:
            delta = chunk.choices[0].delta.content or ""
            response_text += delta
            yield postprocess(response_text)

    return fn


def get_interface_args(pipeline, model_name: str):
    if pipeline == "chat":
        inputs = None
        outputs = None

        def preprocess(message, history):
            messages = []
            # Add system prompt for qwq-32b-preview
            if model_name == "qwq-32b-preview":
                messages.append({
                    "role": "system",
                    "content": "You are a helpful and harmless assistant. You are Qwen developed by Alibaba. You should think step-by-step."
                })

            for user_msg, assistant_msg in history:
                messages.append({"role": "user", "content": user_msg})
                messages.append({"role": "assistant", "content": assistant_msg})
            
            # Handle multimodal input
            if isinstance(message, dict):
                content = []
                if message.get("files"):
                    # Convert local file path to data URL
                    import base64
                    with open(message["files"][0], "rb") as image_file:
                        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                        content.append({
                            "type": "image_url",
                            "image_url": f"data:image/jpeg;base64,{encoded_image}"
                        })
                content.append({
                    "type": "text",
                    "text": message["text"]
                })
                messages.append({"role": "user", "content": content})
            else:
                messages.append({"role": "user", "content": [{"type": "text", "text": message}]})
                
            return {"messages": messages}

        postprocess = lambda x: x  # No post-processing needed
    else:
        # Add other pipeline types when they will be needed
        raise ValueError(f"Unsupported pipeline type: {pipeline}")
    return inputs, outputs, preprocess, postprocess


def get_pipeline(model_name):
    # Determine the pipeline type based on the model name
    # For simplicity, assuming all models are chat models at the moment
    return "chat"


def registry(name: str, token: str | None = None, base_url: str | None = None, **kwargs):
    """
    Create a Gradio Interface for a model on OpenAI or DashScope.

    Parameters:
        - name (str): The name of the model (e.g. "qwen-turbo", "gpt-3.5-turbo")
        - token (str, optional): The API key
        - base_url (str, optional): The base URL for the API. Defaults to DashScope URL.
    """
    api_key = token or os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("API key not found in environment variables.")

    pipeline = get_pipeline(name)
    inputs, outputs, preprocess, postprocess = get_interface_args(pipeline, name)
    fn = get_fn(name, preprocess, postprocess, api_key, base_url)

    if pipeline == "chat":
        interface = gr.ChatInterface(fn=fn, multimodal=True, **kwargs)
    else:
        # For other pipelines, create a standard Interface (not implemented yet)
        interface = gr.Interface(fn=fn, inputs=inputs, outputs=outputs, **kwargs)

    return interface