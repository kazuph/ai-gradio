import os
import base64
from openai import OpenAI
import gradio as gr
from typing import Callable
import modelscope_studio.components.base as ms
import modelscope_studio.components.legacy as legacy
import modelscope_studio.components.antd as antd

__version__ = "0.0.1"

# Add these constants at the top of the file
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

def get_fn(model_name: str, preprocess: Callable, postprocess: Callable, api_key: str):
    def fn(message, history):
        inputs = preprocess(message, history)
        client = OpenAI(
            base_url="https://api.deepseek.com",
            api_key=api_key,
        )
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=inputs["messages"],
                stream=True,
            )
            response_text = ""
            reasoning_text = ""
            for chunk in completion:
                if chunk.choices[0].delta.reasoning_content:
                    reasoning_text += chunk.choices[0].delta.reasoning_content
                else:
                    delta = chunk.choices[0].delta.content or ""
                    response_text += delta
                yield postprocess(response_text, reasoning_text)
        except Exception as e:
            error_message = f"Error: {str(e)}"
            return error_message

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
        outputs = [
            gr.Textbox(label="Chain of Thought", lines=10, visible=True),
            gr.Textbox(label="Response")
        ]

        def preprocess(message, history):           
            messages = []
            files = None
            for user_msg, assistant_msg in history:
                if assistant_msg is not None:
                    if isinstance(assistant_msg, dict):
                        assistant_msg = assistant_msg["visible"][1]  # Get the response text
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

        def postprocess(response, reasoning=None):
            # Update both textboxes but return only the response for the chat history
            return response
    else:
        # Add other pipeline types when they will be needed
        raise ValueError(f"Unsupported pipeline type: {pipeline}")
    return inputs, outputs, preprocess, postprocess


def get_pipeline(model_name):
    if model_name == "deepseek-reasoner":
        return "chat"
    # For other models, assume chat pipeline
    return "chat"


def registry(
    name: str, 
    token: str | None = None, 
    examples: list | None = None,
    coder: bool = False,
    **kwargs
):
    api_key = token or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable is not set.")

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
                                        <h1>DeepSeek R1 Code Generator</h1>
                                    </div>
                                """)
                                
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
                # Clean the code and escape special characters for HTML
                clean_code = code.replace("```html", "").replace("```", "").strip()
                escaped_code = clean_code.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
                return f'''
                    <iframe 
                        srcdoc="<!DOCTYPE html><html><body>{escaped_code}</body></html>"
                        width="100%" 
                        height="920px"
                        sandbox="allow-scripts allow-same-origin"
                    ></iframe>
                '''

            def generate_code(query, setting, history):
                messages = [{"role": "system", "content": setting["system"]}]
                
                # Add history in alternating user/assistant pattern
                for user_msg, assistant_msg in history:
                    messages.append({"role": "user", "content": user_msg})
                    messages.append({"role": "assistant", "content": assistant_msg})
                
                # Add current query
                messages.append({"role": "user", "content": query})
                
                try:
                    client = OpenAI(
                        base_url="https://api.deepseek.com",
                        api_key=api_key,
                    )
                    
                    response = client.chat.completions.create(
                        model=name,
                        messages=messages,
                        stream=True,
                    )
                    
                    code = ""
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            code += chunk.choices[0].delta.content
                            # Return all 5 required outputs
                            yield (
                                f"```html\n{code}\n```",  # code_output (modelscopemarkdown)
                                history,        # state
                                None,          # preview (html)
                                gr.update(active_key="loading"),  # state_tab (antdtabs)
                                gr.update(open=True)  # code_drawer (antddrawer)
                            )
                    
                    new_history = history + [(query, code)]
                    
                    # Final yield with all outputs
                    yield (
                        f"```html\n{code}\n```",  # code_output (modelscopemarkdown)
                        new_history,    # state
                        send_to_preview(code),  # preview (html)
                        gr.update(active_key="render"),  # state_tab (antdtabs)
                        gr.update(open=False)  # code_drawer (antddrawer)
                    )
                
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    yield (
                        error_msg,
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
                inputs=[input, setting, history],
                outputs=[code_output, history, preview, state_tab, code_drawer]
            )
            
            clear_btn.click(lambda: [], outputs=[history])

        return interface

    # Continue with existing chat interface code...
    pipeline = get_pipeline(name)
    inputs, outputs, preprocess, postprocess = get_interface_args(pipeline)
    fn = get_fn(name, preprocess, postprocess, api_key)

    if examples:
        kwargs["examples"] = examples

    if pipeline == "chat":
        interface = gr.ChatInterface(fn=fn, **kwargs)
    else:
        interface = gr.Interface(fn=fn, inputs=inputs, outputs=outputs, **kwargs)

    return interface