import gradio as gr
import replicate
import asyncio
import os
from typing import Callable, Dict, Any, List, Tuple
import httpx
from PIL import Image
import io
import base64
import numpy as np
import tempfile
import time

def resize_image_if_needed(image, max_size=1024):
    """Resize image if either dimension exceeds max_size while maintaining aspect ratio"""
    if isinstance(image, str) and image.startswith('data:image'):
        return image  # Already a data URI, skip processing
    
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    elif not isinstance(image, Image.Image):
        image = Image.open(image)
    
    # Get original dimensions
    width, height = image.size
    
    # Calculate new dimensions if needed
    if width > max_size or height > max_size:
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Convert to RGB if necessary
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Convert to base64
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=85)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/jpeg;base64,{img_str}"

def bytes_to_image(byte_data):
    """Convert bytes to PIL Image and ensure we get fresh data"""
    if isinstance(byte_data, bytes):
        return Image.open(io.BytesIO(byte_data))
    # For file-like objects
    if hasattr(byte_data, 'seek'):
        byte_data.seek(0)
    return Image.open(io.BytesIO(byte_data.read()))

def save_bytes_to_video(video_bytes):
    """Save video bytes to a temporary file and return the path"""
    if not isinstance(video_bytes, bytes):
        raise ValueError(f"Expected bytes input, got {type(video_bytes)}")
        
    # Create a temporary file with .mp4 extension
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"temp_{int(time.time())}_{os.urandom(4).hex()}.mp4")
    
    try:
        # Write the bytes to the temporary file
        with open(temp_path, "wb") as f:
            f.write(video_bytes)
        
        # Ensure the file exists and has content
        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            raise ValueError("Failed to save video file or file is empty")
        
        return str(temp_path)  # Return string path as expected by Gradio
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

PIPELINE_REGISTRY = {
    "text-to-image": {
        "inputs": [
            ("prompt", gr.Textbox, {"label": "Prompt"}),
            ("negative_prompt", gr.Textbox, {"label": "Negative Prompt", "optional": True}),
            ("width", gr.Number, {"label": "Width", "value": 1024, "minimum": 512, "maximum": 2048, "step": 64, "optional": True}),
            ("height", gr.Number, {"label": "Height", "value": 1024, "minimum": 512, "maximum": 2048, "step": 64, "optional": True}),
            ("num_outputs", gr.Number, {"label": "Number of Images", "value": 1, "minimum": 1, "maximum": 4, "step": 1, "optional": True}),
            ("scheduler", gr.Dropdown, {"label": "Scheduler", "choices": ["DPM++ 2M", "DPM++ 2M Karras", "DPM++ 2M SDE", "DPM++ 2M SDE Karras"], "optional": True}),
            ("num_inference_steps", gr.Slider, {"label": "Steps", "minimum": 1, "maximum": 100, "value": 30, "optional": True}),
            ("guidance_scale", gr.Slider, {"label": "Guidance Scale", "minimum": 1, "maximum": 20, "value": 7.5, "optional": True}),
            ("seed", gr.Number, {"label": "Seed", "optional": True})
        ],
        "outputs": [("images", gr.Gallery, {})],
        "preprocess": lambda *args: {
            k: v for k, v in zip([
                "prompt", "negative_prompt", "width", "height", "num_outputs",
                "scheduler", "num_inference_steps", "guidance_scale", "seed"
            ], args) if v is not None and v != ""
        },
        "postprocess": lambda x: [bytes_to_image(img) for img in x] if isinstance(x, list) else [bytes_to_image(x)]
    },

    "image-to-image": {
        "inputs": [
            ("prompt", gr.Textbox, {"label": "Prompt"}),
            ("image", gr.Image, {"label": "Input Image", "type": "pil"}),
            ("negative_prompt", gr.Textbox, {"label": "Negative Prompt", "optional": True}),
            ("strength", gr.Slider, {"label": "Strength", "minimum": 0, "maximum": 1, "value": 0.7, "optional": True}),
            ("num_inference_steps", gr.Slider, {"label": "Steps", "minimum": 1, "maximum": 100, "value": 30, "optional": True}),
            ("guidance_scale", gr.Slider, {"label": "Guidance Scale", "minimum": 1, "maximum": 20, "value": 7.5, "optional": True}),
            ("seed", gr.Number, {"label": "Seed", "optional": True})
        ],
        "outputs": [("images", gr.Gallery, {})],
        "preprocess": lambda *args: {
            k: (resize_image_if_needed(v) if k == "image" else v)
            for k, v in zip([
                "prompt", "image", "negative_prompt", "strength",
                "num_inference_steps", "guidance_scale", "seed"
            ], args) if v is not None and v != ""
        },
        "postprocess": lambda x: [bytes_to_image(img) for img in x] if isinstance(x, list) else [bytes_to_image(x)]
    },

    "control-net": {
        "inputs": [
            ("prompt", gr.Textbox, {"label": "Prompt"}),
            ("control_image", gr.Image, {"label": "Control Image", "type": "pil"}),
            ("negative_prompt", gr.Textbox, {"label": "Negative Prompt", "optional": True}),
            ("guidance_scale", gr.Slider, {"label": "Guidance Scale", "minimum": 1, "maximum": 20, "value": 7.5, "optional": True}),
            ("control_guidance_scale", gr.Slider, {"label": "Control Guidance Scale", "minimum": 1, "maximum": 20, "value": 1.5, "optional": True}),
            ("num_inference_steps", gr.Slider, {"label": "Steps", "minimum": 1, "maximum": 100, "value": 30, "optional": True}),
            ("seed", gr.Number, {"label": "Seed", "optional": True})
        ],
        "outputs": [("images", gr.Gallery, {})],
        "preprocess": lambda *args: {
            k: (resize_image_if_needed(v) if k == "control_image" else v)
            for k, v in zip([
                "prompt", "control_image", "negative_prompt", "guidance_scale",
                "control_guidance_scale", "num_inference_steps", "seed"
            ], args) if v is not None and v != ""
        },
        "postprocess": lambda x: [bytes_to_image(img) for img in x] if isinstance(x, list) else [bytes_to_image(x)]
    },

    "inpainting": {
        "inputs": [
            ("prompt", gr.Textbox, {"label": "Prompt"}),
            ("image", gr.Image, {"label": "Original Image", "type": "pil"}),
            ("mask", gr.Image, {"label": "Mask Image", "type": "pil"}),
            ("negative_prompt", gr.Textbox, {"label": "Negative Prompt", "optional": True}),
            ("num_inference_steps", gr.Slider, {"label": "Steps", "minimum": 1, "maximum": 100, "value": 30, "optional": True}),
            ("guidance_scale", gr.Slider, {"label": "Guidance Scale", "minimum": 1, "maximum": 20, "value": 7.5, "optional": True}),
            ("seed", gr.Number, {"label": "Seed", "optional": True})
        ],
        "outputs": [("images", gr.Gallery, {})],
        "preprocess": lambda *args: {
            k: (resize_image_if_needed(v) if k in ["image", "mask"] else v)
            for k, v in zip([
                "prompt", "image", "mask", "negative_prompt",
                "num_inference_steps", "guidance_scale", "seed"
            ], args) if v is not None and v != ""
        },
        "postprocess": lambda x: [bytes_to_image(img) for img in x] if isinstance(x, list) else [bytes_to_image(x)]
    },

    "text-to-video": {
        "inputs": [
            ("prompt", gr.Textbox, {
                "label": "Prompt",
                "value": "A cat walks on the grass, realistic style.",
                "info": "Text prompt to generate video."
            }),
            ("height", gr.Number, {
                "label": "Height",
                "value": 480,
                "minimum": 1,
                "info": "Height of the video in pixels."
            }),
            ("width", gr.Number, {
                "label": "Width",
                "value": 854,
                "minimum": 1,
                "info": "Width of the video in pixels."
            }),
            ("video_length", gr.Number, {
                "label": "Video Length",
                "value": 129,
                "minimum": 1,
                "info": "Length of the video in frames."
            }),
            ("infer_steps", gr.Number, {
                "label": "Infer Steps",
                "value": 30,
                "minimum": 1,
                "maximum": 50,
                "info": "Number of inference steps."
            }),
            ("flow_shift", gr.Number, {
                "label": "Flow Shift",
                "value": 7,
                "info": "Flow-shift parameter."
            }),
            ("embedded_guidance_scale", gr.Slider, {
                "label": "Embedded Guidance Scale",
                "value": 6,
                "minimum": 1,
                "maximum": 6,
                "info": "Embedded guidance scale for generation."
            }),
            ("seed", gr.Number, {
                "label": "Seed",
                "optional": True,
                "info": "Random seed for reproducibility."
            })
        ],
        "outputs": [
            ("video", gr.Video, {
                "format": "mp4",
                "autoplay": True,
                "show_label": True,
                "label": "Generated Video",
                "height": 480,
                "width": 854,
                "interactive": False,
                "show_download_button": True
            })
        ],
        "preprocess": lambda *args: {
            k: (int(v) if k in ["height", "width", "video_length", "infer_steps", "seed"] else 
                float(v) if k in ["flow_shift", "embedded_guidance_scale"] else v)
            for k, v in zip([
                "prompt", "height", "width", "video_length", 
                "infer_steps", "flow_shift", "embedded_guidance_scale", "seed"
            ], args) if v is not None and v != ""
        },
        "postprocess": lambda x: (
            x.url if hasattr(x, 'url') 
            else (lambda p: os.remove(p) or p)(x)  # Delete file after getting path
        ),
    },

    "text-generation": {
        "inputs": [
            ("message", gr.Textbox, {
                "label": "Message",
                "lines": 3,
                "placeholder": "Enter your message here..."
            }),
        ],
        "outputs": [
            ("response", gr.Textbox, {
                "label": "Assistant",
                "lines": 10,
                "show_copy_button": True
            })
        ],
        "preprocess": lambda *args: {
            "prompt": args[0] if args[0] is not None and args[0] != "" else ""
        },
        "postprocess": lambda x: x,
        "is_chat": True  # New flag to indicate this is a chat interface
    },
}

MODEL_TO_PIPELINE = {
    "stability-ai/sdxl": "text-to-image",
    "black-forest-labs/flux-pro": "text-to-image",
    "stability-ai/stable-diffusion": "text-to-image",
    
    "black-forest-labs/flux-depth-pro": "control-net",
    "black-forest-labs/flux-canny-pro": "control-net",
    "black-forest-labs/flux-depth-dev": "control-net",
    
    "black-forest-labs/flux-fill-pro": "inpainting",
    "stability-ai/stable-diffusion-inpainting": "inpainting",
    "tencent/hunyuan-video:140176772be3b423d14fdaf5403e6d4e38b85646ccad0c3fd2ed07c211f0cad1": "text-to-video",
    "deepseek-ai/deepseek-r1": "text-generation",
}

def create_component(comp_type: type, name: str, config: Dict[str, Any]) -> gr.components.Component:
    # Remove 'optional' from config as it's not a valid Gradio parameter
    config = config.copy()
    is_optional = config.pop('optional', False)
    
    # Add "(Optional)" to label if the field is optional
    if is_optional:
        label = config.get('label', name)
        config['label'] = f"{label} (Optional)"
    
    return comp_type(label=config.get("label", name), **{k:v for k,v in config.items() if k != "label"})

def get_pipeline(model: str) -> str:
    return MODEL_TO_PIPELINE.get(model, "text-to-image")

def get_interface_args(pipeline: str) -> Tuple[List, List, Callable, Callable]:
    if pipeline not in PIPELINE_REGISTRY:
        raise ValueError(f"Unsupported pipeline: {pipeline}")
    
    config = PIPELINE_REGISTRY[pipeline]
    
    inputs = [create_component(comp_type, name, conf) 
             for name, comp_type, conf in config["inputs"]]
    
    outputs = [create_component(comp_type, name, conf) 
              for name, comp_type, conf in config["outputs"]]
    
    return inputs, outputs, config["preprocess"], config["postprocess"]

async def async_run_with_timeout(model_name: str, args: dict):
    try:
        stream = await replicate.async_stream(
            model_name,
            input=args
        )
        async for output in stream:
            yield output
    except Exception as e:
        print(f"Error during model prediction: {str(e)}")
        raise gr.Error(f"Model prediction failed: {str(e)}")

def get_fn(model_name: str, preprocess: Callable, postprocess: Callable):
    async def fn(*args):
        try:
            args = preprocess(*args)
            if model_name == "deepseek-ai/deepseek-r1":
                response = ""
                async for chunk in async_run_with_timeout(model_name, args):
                    chunk = str(chunk)
                    # Replace XML-like tags with square bracket versions
                    chunk = (chunk.replace("<think>", "[think]")
                                .replace("</think>", "[/think]")
                                .replace("<Answer>", "[Answer]")
                                .replace("</Answer>", "[/Answer]"))
                    response += chunk
                return response.strip()
            output = await async_run_with_timeout(model_name, args)
            return postprocess(output)
        except Exception as e:
            raise gr.Error(f"Error: {str(e)}")
    return fn

def registry(name: str | Dict, token: str | None = None, inputs=None, outputs=None, src=None, accept_token: bool = False, **kwargs) -> gr.Interface:
    """
    Create a Gradio Interface for a model on Replicate.
    Parameters:
        - name (str | Dict): The name of the model on Replicate, or a dict with model info.
        - token (str, optional): The API token for the model on Replicate.
        - inputs (List[gr.Component], optional): The input components to use instead of the default.
        - outputs (List[gr.Component], optional): The output components to use instead of the default.
        - src (callable, optional): Ignored, used by gr.load for routing.
        - accept_token (bool, optional): Whether to accept a token input field.
    Returns:
        gr.Interface or gr.ChatInterface: A Gradio interface for the model.
    """
    # Handle both string names and dict configurations
    if isinstance(name, dict):
        model_name = name.get('name', name.get('model_name', ''))
    else:
        model_name = name

    if token:
        os.environ["REPLICATE_API_TOKEN"] = token
        
    pipeline = get_pipeline(model_name)
    inputs_, outputs_, preprocess, postprocess = get_interface_args(pipeline)
    
    # Add token input if accept_token is True
    if accept_token:
        token_input = gr.Textbox(label="API Token", type="password")
        inputs_ = [token_input] + inputs_
        
        # Modify preprocess function to handle token
        original_preprocess = preprocess
        def new_preprocess(token, *args):
            if token:
                os.environ["REPLICATE_API_TOKEN"] = token
            return original_preprocess(*args)
        preprocess = new_preprocess
    
    inputs, outputs = inputs or inputs_, outputs or outputs_
    fn = get_fn(model_name, preprocess, postprocess)

    # Use ChatInterface for text-generation models
    if pipeline == "text-generation":
        return gr.ChatInterface(
            fn=fn,
            **kwargs
        )
    
    return gr.Interface(fn=fn, inputs=inputs, outputs=outputs, **kwargs)


__version__ = "0.1.0"