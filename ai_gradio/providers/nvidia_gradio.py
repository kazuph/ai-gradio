import json
import os
import uuid
from collections.abc import Callable
from contextlib import suppress

import gradio as gr
import requests
from openai import OpenAI
import modelscope_studio.components.base as ms
import modelscope_studio.components.legacy as legacy
import modelscope_studio.components.antd as antd
import re
import base64

__version__ = "0.0.1"

# Constants for coder interface
SystemPrompt = """You are an expert web developer specializing in creating clean, efficient, and modern web applications.
Your task is to write complete, self-contained HTML files that include all necessary CSS and JavaScript.
Focus on:
- Writing clear, maintainable code
- Following best practices
- Creating responsive designs
- Adding appropriate styling and interactivity
Return only the complete HTML code without any additional explanation."""

DEMO_LIST = [
    {
        "card": {"index": 0},
        "title": "Simple Button",
        "description": "Create a button that changes color when clicked"
    },
    {
        "card": {"index": 1},
        "title": "Todo List",
        "description": "Create a simple todo list with add/remove functionality"
    },
    {
        "card": {"index": 2},
        "title": "Timer App",
        "description": "Create a countdown timer with start/pause/reset controls"
    }
]

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

        def postprocess(x):
            # Replace DeepSeek special tokens with brackets
            return (x.replace("<think>", "[think]")
                    .replace("</think>", "[/think]"))

        return inputs, outputs, preprocess, postprocess
    else:
        raise ValueError(f"Unsupported pipeline type: {pipeline}")


def get_pipeline(model_name):
    # Determine the pipeline type based on the model name
    # For simplicity, assuming all models are chat models at the moment
    return "chat"


def registry(
    name: str, 
    token: str | None = None, 
    examples: list | None = None,
    coder: bool = False,
    **kwargs
):
    if "cosmos-nemotron-34b" in name:
        api_key = token or os.environ.get("TEST_NVCF_API_KEY")
        if not api_key:
            raise ValueError("TEST_NVCF_API_KEY environment variable is not set.")
    else:
        api_key = token or os.environ.get("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("NVIDIA_API_KEY environment variable is not set.")

    if coder:
        interface = gr.Blocks(css="""
            .left_header {
                text-align: center;
                margin-bottom: 20px;
            }

            .right_panel {
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            }

            .render_header {
                background: #f5f5f5;
                padding: 8px;
                border-bottom: 1px solid #e8e8e8;
            }

            .header_btn {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
                background: #ff5f56;
            }

            .header_btn:nth-child(2) {
                background: #ffbd2e;
            }

            .header_btn:nth-child(3) {
                background: #27c93f;
            }

            .right_content {
                padding: 24px;
                height: 920px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .html_content {
                height: 920px;
                width: 100%;
            }

            .history_chatbot {
                height: 100%;
            }

            .image-upload-section {
                margin-bottom: 16px;
            }
            
            .image-upload-label {
                font-size: 14px;
                margin-bottom: 8px;
            }
        """)
        
        with interface:
            history = gr.State([])
            setting = gr.State({"system": SystemPrompt})

            with ms.Application() as app:
                with antd.ConfigProvider():
                    with antd.Row(gutter=[32, 12]) as layout:
                        # Left Column
                        with antd.Col(span=24, md=8):
                            with antd.Flex(vertical=True, gap="middle", wrap=True):
                                header = gr.HTML("""
                                    <div class="left_header">
                                        <h1>NVIDIA Code Generator</h1>
                                    </div>
                                """)
                                
                                # Image upload section
                                with gr.Group(elem_classes="image-upload-section"):
                                    image_input = gr.Image(
                                        label="Upload Reference Images",
                                        type="filepath",
                                        height=200
                                    )
                                
                                input = antd.InputTextarea(
                                    size="large",
                                    allow_clear=True,
                                    placeholder="Describe the web application you want to create"
                                )
                                btn = antd.Button("Generate", type="primary", size="large")
                                clear_btn = antd.Button("Clear History", type="default", size="large")

                                antd.Divider("Examples")
                                with antd.Flex(gap="small", wrap=True):
                                    with ms.Each(DEMO_LIST):
                                        with antd.Card(hoverable=True, as_item="card") as demoCard:
                                            antd.CardMeta()
                                
                                antd.Divider("Settings")
                                with antd.Flex(gap="small", wrap=True):
                                    settingPromptBtn = antd.Button("⚙️ System Prompt", type="default")
                                    codeBtn = antd.Button("🧑‍💻 View Code", type="default")
                                    historyBtn = antd.Button("📜 History", type="default")

                            # Modals and Drawers
                            with antd.Modal(open=False, title="System Prompt", width="800px") as system_prompt_modal:
                                systemPromptInput = antd.InputTextarea(SystemPrompt, auto_size=True)

                            with antd.Drawer(open=False, title="Code", placement="left", width="750px") as code_drawer:
                                code_output = legacy.Markdown()

                            with antd.Drawer(open=False, title="History", placement="left", width="900px") as history_drawer:
                                history_output = legacy.Chatbot(
                                    show_label=False,
                                    height=960,
                                    elem_classes="history_chatbot"
                                )

                        # Right Column
                        with antd.Col(span=24, md=16):
                            with ms.Div(elem_classes="right_panel"):
                                gr.HTML('''
                                    <div class="render_header">
                                        <span class="header_btn"></span>
                                        <span class="header_btn"></span>
                                        <span class="header_btn"></span>
                                    </div>
                                ''')
                                with antd.Tabs(active_key="empty", render_tab_bar="() => null") as state_tab:
                                    with antd.Tabs.Item(key="empty"):
                                        empty = antd.Empty(
                                            description="Enter your request to generate code",
                                            elem_classes="right_content"
                                        )
                                    with antd.Tabs.Item(key="loading"):
                                        loading = antd.Spin(
                                            True,
                                            tip="Generating code...",
                                            size="large",
                                            elem_classes="right_content"
                                        )
                                    with antd.Tabs.Item(key="render"):
                                        preview = gr.HTML(elem_classes="html_content")

            # Event Handlers
            def demo_card_click(e: gr.EventData):
                index = e._data['component']['index']
                return DEMO_LIST[index]['description']

            def send_to_preview(code):
                encoded_html = base64.b64encode(code.encode('utf-8')).decode('utf-8')
                data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"
                return f'<iframe src="{data_uri}" width="100%" height="920px"></iframe>'

            def remove_code_block(text):
                pattern = r'```html\n(.+?)\n```'
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    return match.group(1).strip()
                return text.strip()

            def generate_code(query, image, setting, history):
                messages = [
                    {"role": "system", "content": setting["system"]},
                    {"role": "assistant", "content": "I understand. I will help you write clean, efficient web code."}
                ]
                
                # Add history
                for h in history:
                    messages.append({"role": "user", "content": h[0]})
                    messages.append({"role": "assistant", "content": h[1]})
                
                # Add current query with image if provided
                if image:
                    media_content = f'<img src="data:image/jpeg;asset_id,{_upload_asset(image, api_key, "Reference image")}" />'
                    query = f"{query} {media_content}"
                
                messages.append({"role": "user", "content": query})
                
                response_text = ""
                try:
                    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
                    completion = client.chat.completions.create(
                        model=name,
                        messages=messages,
                        temperature=0.2,
                        top_p=0.7,
                        max_tokens=10000,
                        stream=True,
                    )

                    for chunk in completion:
                        if chunk.choices[0].delta.content is not None:
                            delta = chunk.choices[0].delta.content
                            response_text += delta
                            # Return all 5 required outputs
                            yield (
                                response_text,  # code_output
                                history,        # state
                                None,          # preview
                                gr.update(active_key="loading"),  # state_tab
                                gr.update(open=True)  # code_drawer
                            )
                    
                    clean_code = remove_code_block(response_text)
                    new_history = history + [(query, response_text)]
                    
                    # Final yield with all outputs
                    yield (
                        response_text,  # code_output
                        new_history,    # state
                        send_to_preview(clean_code),  # preview
                        gr.update(active_key="render"),  # state_tab
                        gr.update(open=False)  # code_drawer
                    )
                except Exception as e:
                    yield (
                        f"Error: {str(e)}",
                        history,
                        None,
                        gr.update(active_key="empty"),
                        gr.update(open=True)
                    )

            # Wire up event handlers
            demoCard.click(demo_card_click, outputs=[input])
            settingPromptBtn.click(lambda: gr.update(open=True), outputs=[system_prompt_modal])
            system_prompt_modal.ok(
                lambda input: ({"system": input}, gr.update(open=False)),
                inputs=[systemPromptInput],
                outputs=[setting, system_prompt_modal]
            )
            system_prompt_modal.cancel(lambda: gr.update(open=False), outputs=[system_prompt_modal])
            
            codeBtn.click(lambda: gr.update(open=True), outputs=[code_drawer])
            code_drawer.close(lambda: gr.update(open=False), outputs=[code_drawer])
            
            historyBtn.click(
                lambda h: (gr.update(open=True), h),
                inputs=[history],
                outputs=[history_drawer, history_output]
            )
            history_drawer.close(lambda: gr.update(open=False), outputs=[history_drawer])
            
            btn.click(
                generate_code,
                inputs=[input, image_input, setting, history],
                outputs=[code_output, history, preview, state_tab, code_drawer]
            )
            
            clear_btn.click(lambda: [], outputs=[history])

        return interface

    # Continue with existing chat interface code...
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
