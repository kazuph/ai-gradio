import os
from groq import Groq
import gradio as gr
from typing import Callable
import base64

__version__ = "0.0.3"

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

def get_fn(model_name: str, preprocess: Callable, postprocess: Callable, api_key: str, multimodal: bool = False):
    def fn(message, history):
        inputs = preprocess(message, history)
        client = Groq(api_key=api_key)
        
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

def get_interface_args(pipeline):
    if pipeline == "chat":
        inputs = None
        outputs = None

        def preprocess(message, history):
            messages = []
            files = None
            for user_msg, assistant_msg in history:
                if assistant_msg is not None:
                    messages.append({"role": "user", "content": handle_user_msg(user_msg)})
                    messages.append({"role": "assistant", "content": assistant_msg})
                else:
                    files = user_msg
            if type(message) is str and files is not None:
                message = {"text": message, "files": files}
            elif type(message) is dict and files is not None:
                if message["files"] is None or len(message["files"]) == 0:
                    message["files"] = files
            messages.append({"role": "user", "content": handle_user_msg(message)})
            return {"messages": messages}

        postprocess = lambda x: x
    else:
        raise ValueError(f"Unsupported pipeline type: {pipeline}")
    return inputs, outputs, preprocess, postprocess

def get_pipeline(model_name):
    return "chat"

def registry(name: str, token: str | None = None, multimodal: bool = True, **kwargs):
    api_key = token or os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set.")

    pipeline = get_pipeline(name)
    inputs, outputs, preprocess, postprocess = get_interface_args(pipeline)
    fn = get_fn(name, preprocess, postprocess, api_key, multimodal)

    if pipeline == "chat":
        interface = gr.ChatInterface(fn=fn, multimodal=multimodal, **kwargs)
    else:
        interface = gr.Interface(fn=fn, inputs=inputs, outputs=outputs, **kwargs)

    return interface