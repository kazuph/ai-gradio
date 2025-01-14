import os
import base64
from mistralai import Mistral
import gradio as gr
from typing import Callable
from urllib.parse import urlparse
import modelscope_studio.components.base as ms
import modelscope_studio.components.legacy as legacy
import modelscope_studio.components.antd as antd
import re

__version__ = "0.0.1"

SystemPrompt = """You are an expert web developer specializing in creating clean, efficient, and modern web applications.
Your task is to write complete, self-contained HTML files that include all necessary CSS and JavaScript.
Focus on:
- Writing clear, maintainable code
- Following best practices
- Creating responsive designs
- Adding appropriate styling and interactivity
Return only the complete HTML code without any additional explanation."""


def encode_image_file(image_path):
    """Encode an image file to base64."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image: {str(e)}")
        return None


def process_image(image):
    """Process image input to the format expected by Mistral API."""
    if isinstance(image, str):
        # Check if it's a URL or base64 string
        if image.startswith('data:'):
            return image  # Already in base64 format
        elif urlparse(image).scheme in ('http', 'https'):
            return image  # It's a URL
        else:
            # Assume it's a local file path
            encoded = encode_image_file(image)
            return f"data:image/jpeg;base64,{encoded}" if encoded else None
    return None


def get_fn(model_name: str, preprocess: Callable, postprocess: Callable, api_key: str):
    def fn(message, history):
        inputs = preprocess(message, history)
        client = Mistral(api_key=api_key)
        try:
            # Check if the model is Codestral
            if model_name.startswith("codestral"):
                # Handle Codestral API calls
                response = client.chat.complete(
                    model=model_name,
                    messages=inputs["messages"]
                )
                yield postprocess(response.choices[0].message.content)
            else:
                # Create the streaming chat completion for other models
                stream_response = client.chat.stream(
                    model=model_name,
                    messages=inputs["messages"]
                )
                
                response_text = ""
                for chunk in stream_response:
                    if chunk.data.choices[0].delta.content is not None:
                        delta = chunk.data.choices[0].delta.content
                        response_text += delta
                        yield postprocess(response_text)

        except Exception as e:
            print(f"Error during chat completion: {str(e)}")
            yield "Sorry, there was an error processing your request."

    return fn


def get_interface_args(pipeline):
    if pipeline == "chat":
        inputs = None
        outputs = None

        def preprocess(message, history):
            messages = []
            # Process history
            for user_msg, assistant_msg in history:
                if isinstance(user_msg, dict):
                    # Handle multimodal history messages
                    content = []
                    if user_msg.get("text"):
                        content.append({"type": "text", "text": user_msg["text"]})
                    for file in user_msg.get("files", []):
                        processed_image = process_image(file)
                        if processed_image:
                            content.append({"type": "image_url", "image_url": processed_image})
                    messages.append({"role": "user", "content": content})
                else:
                    # Handle text-only history messages
                    messages.append({"role": "user", "content": user_msg})
                messages.append({"role": "assistant", "content": assistant_msg})
            
            # Process current message
            if isinstance(message, dict):
                # Handle multimodal input
                content = []
                if message.get("text"):
                    content.append({"type": "text", "text": message["text"]})
                for file in message.get("files", []):
                    processed_image = process_image(file)
                    if processed_image:
                        content.append({"type": "image_url", "image_url": processed_image})
                messages.append({"role": "user", "content": content})
            else:
                # Handle text-only input
                messages.append({"role": "user", "content": message})
            
            return {"messages": messages}

        postprocess = lambda x: x  # No post-processing needed
    else:
        raise ValueError(f"Unsupported pipeline type: {pipeline}")
    return inputs, outputs, preprocess, postprocess


def get_pipeline(model_name):
    # Determine the pipeline type based on the model name
    # For simplicity, assuming all models are chat models at the moment
    return "chat"


def generate_code(query, history, setting, api_key):
    """Generate code using Mistral API and handle UI updates."""
    client = Mistral(api_key=api_key)
    
    messages = []
    # Add system prompt
    messages.append({"role": "system", "content": setting["system"]})
    
    # Add history
    for h in history:
        messages.append({"role": "user", "content": h[0]})
        messages.append({"role": "assistant", "content": h[1]})
    
    # Add current query
    messages.append({"role": "user", "content": query})
    
    try:
        # Create the streaming chat completion
        stream_response = client.chat.stream(
            model="mistral-large-latest",
            messages=messages
        )
        
        response_text = ""
        for chunk in stream_response:
            if chunk.data.choices[0].delta.content is not None:
                delta = chunk.data.choices[0].delta.content
                response_text += delta
                # Yield intermediate updates
                yield (
                    response_text,          # code_output (for markdown display)
                    history,               # history state
                    None,                  # preview HTML
                    gr.update(active_key="loading"),  # state_tab
                    gr.update(open=True)   # code_drawer
                )
        
        # Clean the code and prepare final preview
        clean_code = remove_code_block(response_text)
        new_history = history + [(query, response_text)]
        
        # Final yield with complete response
        yield (
            response_text,          # code_output
            new_history,           # history state
            send_to_preview(clean_code),  # preview HTML
            gr.update(active_key="render"),  # state_tab
            gr.update(open=False)  # code_drawer
        )
        
    except Exception as e:
        print(f"Error generating code: {str(e)}")
        yield (
            f"Error: {str(e)}",
            history,
            None,
            gr.update(active_key="empty"),
            gr.update(open=True)
        )


def remove_code_block(text):
    """Extract code from markdown code blocks."""
    pattern = r'```html\n(.+?)\n```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def send_to_preview(code):
    """Convert code to base64 encoded iframe source."""
    encoded_html = base64.b64encode(code.encode('utf-8')).decode('utf-8')
    data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"
    return f'<iframe src="{data_uri}" width="100%" height="920px"></iframe>'


def registry(name: str, token: str | None = None, coder: bool = False, **kwargs):
    """
    Create a Gradio Interface for a model on Mistral AI.

    Parameters:
        - name (str): The name of the Mistral AI model.
        - token (str, optional): The API key for Mistral AI.
    """
    api_key = token or os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable is not set.")

    pipeline = get_pipeline(name)
    inputs, outputs, preprocess, postprocess = get_interface_args(pipeline)
    fn = get_fn(name, preprocess, postprocess, api_key)

    if pipeline == "chat":
        # Always enable multimodal support
        interface = gr.ChatInterface(
            fn=fn,
            multimodal=True,
            **kwargs
        )
    else:
        # For other pipelines, create a standard Interface (not implemented yet)
        interface = gr.Interface(fn=fn, inputs=inputs, outputs=outputs, **kwargs)

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
                                        <h1>Codestral Code Generator</h1>
                                    </div>
                                """)
                                
                                input = antd.InputTextarea(
                                    size="large",
                                    allow_clear=True,
                                    placeholder="Describe the code you want to generate"
                                )
                                btn = antd.Button("Generate", type="primary", size="large")
                                clear_btn = antd.Button("Clear History", type="default", size="large")

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

            # Wire up event handlers
            btn.click(
                generate_code,
                inputs=[input, history, setting, gr.State(api_key)],
                outputs=[code_output, history, preview, state_tab, code_drawer],
                api_name=False
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
            
            clear_btn.click(lambda: [], outputs=[history])

    return interface