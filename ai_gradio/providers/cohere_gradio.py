import os
import cohere
import gradio as gr
from typing import Callable
import base64

__version__ = "0.0.3"


def get_fn(model_name: str, preprocess: Callable, postprocess: Callable, api_key: str):
    def fn(message, history):
        inputs = preprocess(message, history)
        client = cohere.Client(api_key=api_key)
        stream = client.chat_stream(
            model=model_name,
            message=inputs["message"],
            chat_history=inputs["chat_history"],
        )
        response_text = ""
        for chunk in stream:
            if chunk.event_type == "text-generation":
                delta = chunk.text
                response_text += delta
                yield postprocess(response_text)

    return fn


def get_image_base64(url: str, ext: str):
    with open(url, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return "data:image/" + ext + ";base64," + encoded_string


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
            return {
                "message": message["text"],
                "attachments": [
                    {
                        "source": encoded_str,
                        "type": "image",
                    }
                ]
            }
        else:
            return message["text"]
    else:
        raise NotImplementedError


def get_interface_args(pipeline):
    if pipeline == "chat":
        inputs = None
        outputs = None

        def preprocess(message, history):
            chat_history = []
            files = None
            for user_msg, assistant_msg in history:
                if assistant_msg is not None:
                    chat_history.append({"role": "USER", "message": handle_user_msg(user_msg)})
                    chat_history.append({"role": "ASSISTANT", "message": assistant_msg})
                else:
                    files = user_msg
            if type(message) is str and files is not None:
                message = {"text": message, "files": files}
            elif type(message) is dict and files is not None:
                if message["files"] is None or len(message["files"]) == 0:
                    message["files"] = files
            
            return {
                "message": handle_user_msg(message),
                "chat_history": chat_history
            }

        postprocess = lambda x: x
    else:
        # Add other pipeline types when they will be needed
        raise ValueError(f"Unsupported pipeline type: {pipeline}")
    return inputs, outputs, preprocess, postprocess


def get_pipeline(model_name):
    # Determine the pipeline type based on the model name
    # For simplicity, assuming all models are chat models at the moment
    return "chat"


def registry(name: str, token: str | None = None, **kwargs):
    """
    Create a Gradio Interface for a model on Cohere.

    Parameters:
        - name (str): The name of the Cohere model.
        - token (str, optional): The API key for Cohere.
    """
    api_key = token or os.environ.get("COHERE_API_KEY")
    if not api_key:
        raise ValueError("COHERE_API_KEY environment variable is not set.")

    pipeline = get_pipeline(name)
    inputs, outputs, preprocess, postprocess = get_interface_args(pipeline)
    fn = get_fn(name, preprocess, postprocess, api_key)

    if pipeline == "chat":
        interface = gr.ChatInterface(fn=fn, multimodal=True, **kwargs)
    else:
        # For other pipelines, create a standard Interface (not implemented yet)
        interface = gr.Interface(fn=fn, inputs=inputs, outputs=outputs, **kwargs)

    return interface