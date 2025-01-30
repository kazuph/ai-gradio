import os
import base64
from huggingface_hub import InferenceClient
import gradio as gr
from typing import Callable

__version__ = "0.0.1"

def get_image_base64(url: str, ext: str):
    with open(url, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return "data:image/" + ext + ";base64," + encoded_string

def get_fn(model_name: str, preprocess: Callable, postprocess: Callable, api_key: str):
    def fn(message, history):
        inputs = preprocess(message, history)
        client = InferenceClient(
            provider="together",
            token=api_key
        )
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=inputs["messages"],
                stream=True,
                max_tokens=1000
            )
            
            partial_message = ""
            for chunk in completion:
                if chunk.choices:
                    delta = chunk.choices[0].delta.content or ""
                    delta = delta.replace("<think>", "[think]").replace("</think>", "[/think]")
                    partial_message += delta
                    yield postprocess(partial_message)
                        
        except Exception as e:
            error_message = f"Error: {str(e)}"
            yield error_message

    return fn

def handle_user_msg(message: str):
    if type(message) is str:
        return message
    elif type(message) is dict:
        if message["files"] is not None and len(message["files"]) > 0:
            ext = os.path.splitext(message["files"][-1])[1].strip(".")
            if ext.lower() in ["png", "jpg", "jpeg", "gif", "pdf"]:
                encoded_str = get_image_base64(message["files"][-1], ext)
            else:
                raise NotImplementedError(f"Not supported file type {ext}")
            content = [
                    {"type": "text", "text": message["text"]},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": encoded_str,
                        }
                    },
                ]
        else:
            content = message["text"]
        return content
    else:
        raise NotImplementedError

def get_interface_args(pipeline):
    if pipeline == "chat":
        inputs = None
        outputs = None

        def preprocess(message, history):           
            messages = []
            # Process history first
            for user_msg, assistant_msg in history:
                messages.append({"role": "user", "content": str(user_msg)})
                if assistant_msg is not None:
                    messages.append({"role": "assistant", "content": str(assistant_msg)})
            
            # Add current message
            messages.append({"role": "user", "content": str(message)})
            return {"messages": messages}

        postprocess = lambda x: x  # No post-processing needed
    else:
        raise ValueError(f"Unsupported pipeline type: {pipeline}")
    return inputs, outputs, preprocess, postprocess


def get_pipeline(model_name):
    # Determine the pipeline type based on the model name
    # For simplicity, assuming all models are chat models at the moment
    return "chat"


def registry(name: str, token: str | None = None, **kwargs):
    """
    Create a Gradio Interface for a model on Together.

    Parameters:
        - name (str): The name of the model on Together.
        - token (str, optional): The API key for Together.
    """
    api_key = token or os.environ.get("HF_TOKEN")
    if not api_key:
        raise ValueError("HF_TOKEN environment variable is not set.")

    pipeline = get_pipeline(name)
    inputs, outputs, preprocess, postprocess = get_interface_args(pipeline)
    fn = get_fn(name, preprocess, postprocess, api_key)

    if pipeline == "chat":
        interface = gr.ChatInterface(fn=fn, **kwargs)
    else:
        # For other pipelines, create a standard Interface (not implemented yet)
        interface = gr.Interface(fn=fn, inputs=inputs, outputs=outputs, **kwargs)

    return interface