import os
import base64
import gradio as gr
import json
import aiohttp
import re
import modelscope_studio.components.base as ms
import modelscope_studio.components.legacy as legacy
import modelscope_studio.components.antd as antd

__version__ = "0.0.1"

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

def get_image_base64(url: str, ext: str):
    with open(url, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return "data:image/" + ext + ";base64," + encoded_string

def handle_user_msg(message: str):
    if isinstance(message, str):
        return message
    elif isinstance(message, dict):
        if message.get("files") and len(message["files"]) > 0:
            ext = os.path.splitext(message["files"][-1])[1].strip(".")
            if ext.lower() in ["png", "jpg", "jpeg", "gif"]:
                encoded_str = get_image_base64(message["files"][-1], ext)
            else:
                raise NotImplementedError(f"Not supported file type {ext}")
            content = [{
                "type": "text",
                "text": message["text"]
            }, {
                "type": "image_url",
                "image_url": {
                    "url": encoded_str
                }
            }]
        else:
            content = message["text"]
        return content
    else:
        raise NotImplementedError

def remove_code_block(text):
    pattern = r'```html\n(.+?)\n```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()

def send_to_preview(code):
    encoded_html = base64.b64encode(code.encode('utf-8')).decode('utf-8')
    data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"
    return f'<iframe src="{data_uri}" width="100%" height="920px"></iframe>'

def registry(
    name: str, 
    token: str | None = None, 
    examples: list | None = None,
    enable_voice: bool = False,
    camera: bool = False,
    coder: bool = False,
    **kwargs
):
    api_key = token or os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise ValueError("MINIMAX_API_KEY environment variable is not set.")

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
                                        <h1>MiniMax Code Generator</h1>
                                    </div>
                                """)
                                
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
            async def demo_card_click(e: gr.EventData):
                index = e._data['component']['index']
                return DEMO_LIST[index]['description']

            async def generate_code(query, image, setting, history):
                messages = []
                messages.append({
                    "role": "system",
                    "content": setting["system"],
                    "name": "MM Intelligent Assistant"
                })
                
                # Add history
                for h in history:
                    messages.append({"role": "user", "content": h[0]})
                    messages.append({"role": "assistant", "content": h[1]})
                
                # Add current query with image if provided
                if image:
                    content = [{
                        "type": "text",
                        "text": query
                    }, {
                        "type": "image_url",
                        "image_url": {
                            "url": get_image_base64(image, os.path.splitext(image)[1].strip("."))
                        }
                    }]
                    messages.append({"role": "user", "content": content})
                else:
                    messages.append({"role": "user", "content": query})

                data = {
                    "model": "MiniMax-Text-01",
                    "messages": messages,
                    "stream": True
                }

                response_text = ""
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        'https://api.minimaxi.chat/v1/text/chatcompletion_v2',
                        headers={
                            'Content-Type': 'application/json',
                            'Authorization': f'Bearer {api_key}'
                        },
                        json=data
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise gr.Error(f'Request failed with status {response.status}: {error_text}')
                        
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data:'):
                                try:
                                    data = json.loads(line[5:])
                                    if 'choices' not in data:
                                        raise gr.Error('Request failed: Invalid response format')
                                    choice = data['choices'][0]
                                    if 'delta' in choice:
                                        response_text += choice['delta']['content']
                                        yield (
                                            response_text,
                                            history,
                                            None,
                                            gr.update(active_key="loading"),
                                            gr.update(open=True)
                                        )
                                    elif 'message' in choice:
                                        response_text = choice['message']['content']
                                except json.JSONDecodeError:
                                    continue

                clean_code = remove_code_block(response_text)
                new_history = history + [(query, response_text)]
                
                yield (
                    response_text,
                    new_history,
                    send_to_preview(clean_code),
                    gr.update(active_key="render"),
                    gr.update(open=False)
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

    model_version = 'MiniMax-Text-01'
    api_url = 'https://api.minimaxi.chat/v1/text/chatcompletion_v2'
    system_prompt = "MM Intelligent Assistant is a large language model that is self-developed by MiniMax and does not call the interface of other products."

    async def respond(message, history):
        messages = []
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt,
                "name": "MM Intelligent Assistant"
            })
            
        for h in history:
            messages.append({"role": "user", "content": handle_user_msg(h[0])})
            messages.append({"role": "assistant", "content": h[1]})
            
        messages.append({"role": "user", "content": handle_user_msg(message)})

        data = {
            "model": model_version,
            "messages": messages,
            "stream": True
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                },
                json=data
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise gr.Error(f'Request failed with status {response.status}: {error_text}')
                
                response_text = ""
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data:'):
                        try:
                            data = json.loads(line[5:])
                            if 'choices' not in data:
                                raise gr.Error('Request failed: Invalid response format')
                            choice = data['choices'][0]
                            if 'delta' in choice:
                                response_text += choice['delta']['content']
                                yield response_text
                            elif 'message' in choice:
                                yield choice['message']['content']
                        except json.JSONDecodeError:
                            continue

    interface = gr.ChatInterface(
        respond,
        title="MiniMax Chat",
        description="Chat with MiniMax AI models",
        examples=[
            ["How many Rs in strawberry?"],
        ]
    )

    return interface