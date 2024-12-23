import os
from lumaai import LumaAI
import gradio as gr
from typing import Callable
import base64
import time

__version__ = "0.0.3"


def get_fn(preprocess: Callable, postprocess: Callable, api_key: str, pipeline: str):
    def fn(message, history, generation_type):
        try:
            inputs = preprocess(message, history)
            # Create a fresh client instance for each generation
            client = LumaAI(auth_token=api_key)
            
            # Validate generation type
            if generation_type not in ["video", "image"]:
                raise ValueError(f"Invalid generation type: {generation_type}")
            
            try:
                if generation_type == "video":
                    generation = client.generations.create(
                        prompt=inputs["prompt"],
                        **inputs.get("additional_params", {})
                    )
                else:  # image
                    generation = client.generations.image.create(
                        prompt=inputs["prompt"],
                        **inputs.get("additional_params", {})
                    )
            except Exception as e:
                raise RuntimeError(f"Failed to create generation: {str(e)}")
            
            # Poll for completion with timeout
            start_time = time.time()
            timeout = 300  # 5 minutes timeout
            
            while True:
                if time.time() - start_time > timeout:
                    raise RuntimeError("Generation timed out after 5 minutes")
                
                try:
                    generation = client.generations.get(id=generation.id)
                    if generation.state == "completed":
                        asset_url = generation.assets.video if generation_type == "video" else generation.assets.image
                        break
                    elif generation.state == "failed":
                        raise RuntimeError(f"Generation failed: {generation.failure_reason}")
                    time.sleep(3)
                    yield f"Generating {generation_type}... (Status: {generation.state})"
                except Exception as e:
                    raise RuntimeError(f"Error checking generation status: {str(e)}")
            
            # Return asset URL wrapped in appropriate format for display
            yield postprocess(asset_url, generation_type)
            
        except Exception as e:
            yield f"Error: {str(e)}"
            raise

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
    generation_type = gr.Dropdown(
        choices=["video", "image"], 
        label="Generation Type", 
        value="video" if pipeline == "video" else "image"
    )
    outputs = None

    def preprocess(message, history):
        if isinstance(message, str):
            return {"prompt": message}
        elif isinstance(message, dict):
            prompt = message.get("text", "")
            additional_params = {}
            
            # Handle optional parameters
            if message.get("aspect_ratio"):
                additional_params["aspect_ratio"] = message["aspect_ratio"]
            if message.get("model"):
                additional_params["model"] = message["model"]
            
            return {
                "prompt": prompt,
                "additional_params": additional_params
            }

    def postprocess(url, generation_type):
        if generation_type == "video":
            return f'<video width="100%" controls><source src="{url}" type="video/mp4">Your browser does not support the video tag.</video>'
        else:
            return f"![Generated Image]({url})"

    return generation_type, outputs, preprocess, postprocess


def get_pipeline(model_name):
    # Support both video and image pipelines
    return "video" if model_name == "dream-machine" else "image"


def registry(name: str = "dream-machine", token: str = None, **kwargs):
    """
    Create a Gradio Interface for LumaAI generation.

    Parameters:
        - name (str): Model name (defaults to 'dream-machine' for video, use 'photon-1' or 'photon-flash-1' for images)
        - token (str, optional): The API key for LumaAI
        - **kwargs: Additional keyword arguments passed to gr.Interface
    """
    api_key = token or kwargs.pop('api_key', None) or os.environ.get("LUMAAI_API_KEY")
    if not api_key:
        raise ValueError("API key must be provided either through token parameter, kwargs, or LUMAAI_API_KEY environment variable.")

    pipeline = get_pipeline(name)
    generation_type, outputs, preprocess, postprocess = get_interface_args(pipeline)
    fn = get_fn(preprocess, postprocess, api_key, pipeline)

    interface = gr.ChatInterface(
        fn=fn,
        additional_inputs=[generation_type],
        type="messages",
        title="LumaAI Generation",
        description="Generate videos or images from text prompts using LumaAI",
        **kwargs
    )

    return interface