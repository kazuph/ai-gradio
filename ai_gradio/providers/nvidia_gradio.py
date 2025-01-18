import json
import os
import uuid
from collections.abc import Callable
from contextlib import suppress

import gradio as gr
import requests
from openai import OpenAI

__version__ = "0.0.1"

kNvcfAssetUrl = "https://api.nvcf.nvidia.com/v2/nvcf/assets"
kSupportedList = {
    "png": ["image/png", "img"],
    "jpg": ["image/jpg", "img"],
    "jpeg": ["image/jpeg", "img"],
    "mp4": ["video/mp4", "video"],
}


def get_extention(filename):
    _, ext = os.path.splitext(filename)
    ext = ext[1:].lower()
    return ext


def mime_type(ext):
    return kSupportedList[ext][0]


def media_type(ext):
    return kSupportedList[ext][1]


def _upload_asset(media_file, api_key, description):
    ext = get_extention(media_file)
    assert ext in kSupportedList
    data_input = open(media_file, "rb")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "accept": "application/json",
    }
    assert_url = kNvcfAssetUrl
    authorize = requests.post(
        assert_url,
        headers=headers,
        json={"contentType": f"{mime_type(ext)}", "description": description},
        timeout=30,
    )
    authorize.raise_for_status()

    authorize_res = authorize.json()
    response = requests.put(
        authorize_res["uploadUrl"],
        data=data_input,
        headers={
            "x-amz-meta-nvcf-asset-description": description,
            "content-type": mime_type(ext),
        },
        timeout=300,
    )

    response.raise_for_status()
    return uuid.UUID(authorize_res["assetId"])


def _delete_asset(asset_id, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    assert_url = f"{kNvcfAssetUrl}/{asset_id}"
    response = requests.delete(assert_url, headers=headers, timeout=30)
    response.raise_for_status()


def chat_with_media_nvcf(infer_url, media_files, query: str, stream: bool = False, api_key: str = None):
    asset_list = []
    ext_list = []
    media_content = ""

    # Handle case when media_files is None
    media_files = media_files or []
    if not isinstance(media_files, list):
        media_files = [media_files]

    has_video = False
    for media_file in media_files:
        if media_file is None:  # Skip if no file
            continue
        ext = get_extention(media_file)
        assert ext in kSupportedList, f"{media_file} format is not supported"
        if media_type(ext) == "video":
            has_video = True
        asset_id = _upload_asset(media_file, api_key, "Reference media file")
        asset_list.append(f"{asset_id}")
        ext_list.append(ext)
        media_content += f'<{media_type(ext)} src="data:{mime_type(ext)};asset_id,{asset_id}" />'

    if has_video:
        assert len(media_files) == 1, "Only single video supported."

    asset_seq = ",".join(asset_list)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "NVCF-INPUT-ASSET-REFERENCES": asset_seq,
        "NVCF-FUNCTION-ASSET-IDS": asset_seq,
        "Accept": "application/json",
    }
    if stream:
        headers["Accept"] = "text/event-stream"
    response = None

    messages = [
        {
            "role": "user",
            "content": f"{query} {media_content}",
        }
    ]
    payload = {
        "max_tokens": 1024,
        "temperature": 0.2,
        "top_p": 0.7,
        "seed": 50,
        "num_frames_per_inference": 8,
        "messages": messages,
        "stream": stream,
        "model": "nvidia/vila",
    }

    try:
        response = requests.post(infer_url, headers=headers, json=payload, stream=stream)
        response.raise_for_status()

        if stream:
            output = ""
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str == "data: [DONE]":
                        break
                    data = json.loads(line_str[6:])
                    content = data["choices"][0]["delta"]["content"]
                    if content:
                        output += content
                    yield output
        else:
            yield response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        yield f"Error: {e!s}"
    finally:
        # Clean up assets
        for asset_id in asset_list:
            with suppress(Exception):
                _delete_asset(asset_id, api_key)


def get_fn(model_name: str, preprocess: Callable, postprocess: Callable, api_key: str):
    if model_name == "nvidia/cosmos-nemotron-34b":  # VLM model

        def fn(message, history):
            if history:
                gr.Warning("This app does not support multi-turn conversation.")
                yield "Error"
                return
            if not message["files"]:
                gr.Warning("Please upload either one video or 1-16 images.")
                yield "Error"
                return

            yield from chat_with_media_nvcf(
                "https://ai.api.nvidia.com/v1/vlm/nvidia/cosmos-nemotron-34b",
                message["files"],
                message["text"],
                stream=True,
                api_key=api_key,
            )

        return fn

    else:  # Regular NIM model
        def fn(message, history):
            inputs = preprocess(message, history)
            client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
            completion = client.chat.completions.create(
                model=model_name,
                messages=inputs["messages"],
                temperature=0.2,
                top_p=0.7,
                max_tokens=1024,
                stream=True,
            )
            response_text = ""
            for chunk in completion:
                if chunk.choices[0].delta.content is not None:
                    delta = chunk.choices[0].delta.content
                    response_text += delta
                    yield postprocess(response_text)

        return fn


def get_interface_args(pipeline, model_name):
    if pipeline == "chat":
        inputs = None
        outputs = None

        def preprocess(message, history):
            messages = []
            for user_msg, assistant_msg in history:
                messages.append({"role": "user", "content": str(user_msg)})
                messages.append({"role": "assistant", "content": str(assistant_msg)})
            
            # Handle both string and dictionary message formats
            if isinstance(message, dict):
                message = message.get('text', '')
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
    """Create a Gradio Interface for a model on NVIDIA NIM or VLM.

    Parameters:
        - name (str): The name of the NVIDIA model (e.g. "nvidia/vila" for VLM).
        - token (str, optional): The API key for NVIDIA services.

    """
    if "cosmos-nemotron-34b" in name:  # VLM model
        api_key = token or os.environ.get("TEST_NVCF_API_KEY")
        if not api_key:
            raise ValueError("TEST_NVCF_API_KEY environment variable is not set.")
    else:
        api_key = token or os.environ.get("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("NVIDIA_API_KEY environment variable is not set.")

    pipeline = get_pipeline(name)
    inputs, outputs, preprocess, postprocess = get_interface_args(pipeline, name)
    fn = get_fn(name, preprocess, postprocess, api_key)

    if pipeline == "chat":
        if "cosmos-nemotron-34b" in name:
            kwargs["type"] = "messages"
            kwargs["textbox"] = gr.MultimodalTextbox(
                file_count="multiple", file_types=[".png", ".jpg", ".jpeg", ".mp4"]
            )
            interface = gr.ChatInterface(fn=fn, **kwargs)
        else:
            interface = gr.ChatInterface(fn=fn, multimodal=True, **kwargs)
    else:
        interface = gr.Interface(fn=fn, inputs=inputs, outputs=outputs, **kwargs)

    return interface
