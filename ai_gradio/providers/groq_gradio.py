import os
from openai import OpenAI
import gradio as gr
from typing import Callable
import base64
import re
import modelscope_studio.components.base as ms
import modelscope_studio.components.legacy as legacy
import modelscope_studio.components.antd as antd

__version__ = "0.0.3"

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
    if type(message) is str:
        return message
    elif type(message) is dict:
        if message["files"] is not None and len(message["files"]) > 0:
            parts = []
            if message["text"]:
                parts.append({"type": "text", "text": message["text"]})
            
            for file in message["files"]:
                ext = os.path.splitext(file)[1].strip(".").lower()
                
                # Handle text-based files
                if ext in ["txt", "md", "py", "js", "html", "css", "json", "csv"]:
                    try:
                        with open(file, "r") as f:
                            content = f.read()
                            parts.append({"type": "text", "text": content})
                    except Exception as e:
                        print(f"Error reading text file: {e}")
                        continue
                
                # Handle images
                elif ext in ["png", "jpg", "jpeg", "gif"]:
                    try:
                        encoded_str = get_image_base64(file, ext)
                        parts.append({
                            "type": "image_url",
                            "image_url": {"url": encoded_str}
                        })
                    except Exception as e:
                        print(f"Error processing image: {e}")
                        continue
                
                # Handle PDFs
                elif ext == "pdf":
                    try:
                        # You might want to add PDF text extraction here
                        # For now, we'll just mention it's a PDF
                        parts.append({
                            "type": "text",
                            "text": f"[PDF file: {os.path.basename(file)}]"
                        })
                    except Exception as e:
                        print(f"Error processing PDF: {e}")
                        continue
                else:
                    print(f"Unsupported file type: {ext}")
                    continue
            
            return parts
        else:
            return message["text"]
    else:
        raise NotImplementedError(f"Unsupported message type: {type(message)}")

def get_fn(model_name: str, preprocess: Callable, postprocess: Callable, api_key: str, multimodal: bool = False):
    def fn(message, history):
        try:
            inputs = preprocess(message, history)
            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=api_key
            )
            
            completion = client.chat.completions.create(
                model=model_name,
                messages=inputs["messages"],
                temperature=0.6,
                max_tokens=4096,  # Changed from max_completion_tokens to max_tokens
                top_p=0.95,
                stream=True,
                n=1,  # Explicitly set to 1 as per Groq's requirements
            )
            
            # Stream response
            response_text = ""
            for chunk in completion:
                if hasattr(chunk.choices[0].delta, 'content'):
                    if chunk.choices[0].delta.content is not None:
                        response_text += chunk.choices[0].delta.content
                        yield postprocess(response_text)
            
            # If no response was generated, yield a default message
            if not response_text:
                yield postprocess("I apologize, but I wasn't able to generate a response. Please try again.")

        except Exception as e:
            print(f"Error in chat completion: {str(e)}")
            yield f"An error occurred: {str(e)}"

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
                    # Format user message
                    user_content = handle_user_msg(user_msg)
                    if isinstance(user_content, list):
                        # For multimodal content, extract text only
                        text_parts = [
                            part["text"] for part in user_content 
                            if part["type"] == "text"
                        ]
                        user_content = " ".join(text_parts)
                    messages.append({"role": "user", "content": user_content})
                    
                    # Format assistant message (always as string)
                    messages.append({"role": "assistant", "content": str(assistant_msg)})
                else:
                    files = user_msg
            
            # Handle current message
            if type(message) is str and files is not None:
                message = {"text": message, "files": files}
            elif type(message) is dict and files is not None:
                if message["files"] is None or len(message["files"]) == 0:
                    message["files"] = files
            
            # Format current user message
            current_content = handle_user_msg(message)
            if isinstance(current_content, list):
                # For multimodal content, extract text only
                text_parts = [
                    part["text"] for part in current_content 
                    if part["type"] == "text"
                ]
                current_content = " ".join(text_parts)
            messages.append({"role": "user", "content": current_content})
            
            return {"messages": messages}

        postprocess = lambda x: x
    else:
        raise ValueError(f"Unsupported pipeline type: {pipeline}")
    return inputs, outputs, preprocess, postprocess

def get_pipeline(model_name):
    return "chat"

def registry(name: str, token: str | None = None, multimodal: bool = True, coder: bool = False, **kwargs):
    api_key = token or os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set.")

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
            setting = gr.State({
                "system": SystemPrompt,
                "model": name
            })

            with ms.Application() as app:
                with antd.ConfigProvider():
                    with antd.Row(gutter=[32, 12]) as layout:
                        # Left Column
                        with antd.Col(span=24, md=8):
                            with antd.Flex(vertical=True, gap="middle", wrap=True):
                                header = gr.HTML("""
                                    <div class="left_header">
                                        <h1>Groq Code Generator</h1>
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

                            # Add modals and drawers
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

            # Wire up event handlers
            demoCard.click(
                update_demo,
                inputs=[history],
                outputs=[input, history, preview, state_tab, code_drawer]
            )
            
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

    # Regular chat interface (existing code)
    pipeline = get_pipeline(name)
    inputs, outputs, preprocess, postprocess = get_interface_args(pipeline)
    fn = get_fn(name, preprocess, postprocess, api_key, multimodal)

    if pipeline == "chat":
        interface = gr.ChatInterface(fn=fn, multimodal=multimodal, **kwargs)
    else:
        interface = gr.Interface(fn=fn, inputs=inputs, outputs=outputs, **kwargs)

    return interface

def remove_code_block(text: str) -> str:
    """Extract code from markdown code blocks"""
    # Find content between ```html and ``` tags
    pattern = r'```html\n(.*?)```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text

def send_to_preview(code: str) -> str:
    """Prepare code for preview iframe"""
    if not code:
        return "about:blank"
    
    # Create an iframe with the HTML code as a data URL
    encoded_html = base64.b64encode(code.encode('utf-8')).decode('utf-8')
    data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"
    return f'<iframe src="{data_uri}" width="100%" height="920px"></iframe>'

def update_demo(evt: dict, history: list) -> tuple:
    """Handle demo selection"""
    # Extract index from the card event data
    index = evt.get("index", 0) if isinstance(evt, dict) else 0
    demo = DEMO_LIST[index]
    return (
        f"{demo['title']}. {demo['description']}",
        history,
        None,
        gr.update(active_key="render"),
        gr.update(open=False)
    )

def generate_code(prompt: str, setting: dict, history: list) -> tuple:
    """Generate HTML code based on user prompt"""
    messages = [{"role": "system", "content": setting["system"]}]
    
    # Add history context - ensure history is a list
    history = history or []
    for h in history:
        messages.append({"role": "user", "content": h[0]})
        messages.append({"role": "assistant", "content": h[1]})
    
    # Add current prompt
    messages.append({"role": "user", "content": prompt})
    
    # Call Groq API
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY")
    )
    completion = client.chat.completions.create(
        model=setting["model"],
        messages=messages,
        temperature=0.6,
        max_tokens=4096,
        top_p=0.95,
        stream=True,
        n=1,
    )
    
    # Stream the response
    response_text = ""
    for chunk in completion:
        if chunk.choices[0].delta.content:
            response_text += chunk.choices[0].delta.content
            # Yield intermediate results
            yield (
                response_text,  # code_output (modelscopemarkdown)
                history,        # state
                None,          # preview (html)
                gr.update(active_key="loading"),  # state_tab
                gr.update(open=True)  # code_drawer
            )
    
    # Process final response
    code = remove_code_block(response_text)
    new_history = history + [(prompt, response_text)]
    preview_url = send_to_preview(code)
    
    # Final yield with complete outputs
    yield (
        response_text,  # code_output
        new_history,    # history
        preview_url,    # preview
        gr.update(active_key="render"),  # state_tab
        gr.update(open=False)  # code_drawer
    )