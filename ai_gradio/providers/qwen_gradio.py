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

def get_fn(model_name: str, preprocess: Callable, postprocess: Callable, api_key: str | None = None, base_url: str | None = None, local: bool = False):
    if local:
        from vllm import LLM, SamplingParams
        from transformers import AutoTokenizer
        
        # Initialize tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        llm = LLM(
            model=model_name,
            tensor_parallel_size=1,  # Adjust based on available GPUs
            max_model_len=1010000,
            enable_chunked_prefill=True,
            max_num_batched_tokens=131072,
            enforce_eager=True,
        )
        
        # Default sampling parameters
        sampling_params = SamplingParams(
            temperature=0.7,
            top_p=0.8,
            repetition_penalty=1.05,
            max_tokens=512
        )
        
        def fn(message, history):
            inputs = preprocess(message, history)
            messages = inputs["messages"]
            
            # Convert messages to model input format
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            # Generate response
            outputs = llm.generate([text], sampling_params)
            response_text = outputs[0].outputs[0].text
            yield postprocess(response_text)
            
        return fn
    
    # Original cloud API implementation
    def fn(message, history):
        inputs = preprocess(message, history)
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
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


def get_interface_args(pipeline, model_name: str):
    if pipeline == "chat":
        inputs = None
        outputs = None

        def preprocess(message, history):
            messages = []
            # Add system prompt for qwq-32b-preview
            if model_name == "qwq-32b-preview":
                messages.append({
                    "role": "system",
                    "content": "You are a helpful and harmless assistant. You are Qwen developed by Alibaba. You should think step-by-step."
                })

            for user_msg, assistant_msg in history:
                messages.append({"role": "user", "content": user_msg})
                messages.append({"role": "assistant", "content": assistant_msg})
            
            # Handle multimodal input
            if isinstance(message, dict):
                content = []
                if message.get("files"):
                    # Convert local file path to data URL
                    with open(message["files"][0], "rb") as image_file:
                        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                        content.append({
                            "type": "image_url",
                            "image_url": f"data:image/jpeg;base64,{encoded_image}"
                        })
                content.append({
                    "type": "text",
                    "text": message["text"]
                })
                messages.append({"role": "user", "content": content})
            else:
                messages.append({"role": "user", "content": [{"type": "text", "text": message}]})
                
            return {"messages": messages}

        postprocess = lambda x: x  # No post-processing needed
    else:
        # Add other pipeline types when they will be needed
        raise ValueError(f"Unsupported pipeline type: {pipeline}")
    return inputs, outputs, preprocess, postprocess


def get_pipeline(model_name):
    # Determine the pipeline type based on the model name
    # For simplicity, assuming all models are chat models at the moment
    return "chat"


def registry(
    name: str, 
    token: str | None = None, 
    examples: list | None = None,
    coder: bool = False,
    local: bool = False,  # Add local parameter
    **kwargs
):
    api_key = None if local else (token or os.environ.get("DASHSCOPE_API_KEY"))
    if not local and not api_key:
        raise ValueError("API key not found in environment variables.")

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
                                        <h1>Qwen Code Generator</h1>
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
                encoded_html = base64.b64encode(code.encode('utf-8')).decode('utf-8')
                data_uri = f"data:text/html;charset=utf-8;base64,{encoded_html}"
                return f'<iframe src="{data_uri}" width="100%" height="920px"></iframe>'

            def remove_code_block(text):
                pattern = r'```html\n(.+?)\n```'
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    return match.group(1).strip()
                return text.strip()

            def generate_code(query, setting, history):
                client = OpenAI(
                    api_key=api_key,
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
                )
                
                messages = [
                    {"role": "system", "content": setting["system"]},
                    {"role": "assistant", "content": "I understand. I will help you write clean, efficient web code."}
                ]
                
                # Add history
                for h in history:
                    messages.append({"role": "user", "content": h[0]})
                    messages.append({"role": "assistant", "content": h[1]})
                
                messages.append({"role": "user", "content": query})
                
                completion = client.chat.completions.create(
                    model=name,
                    messages=messages,
                    stream=True,
                )
                
                response_text = ""
                for chunk in completion:
                    if chunk.choices[0].delta.content:
                        response_text += chunk.choices[0].delta.content
                        yield (
                            response_text,
                            history,
                            None,
                            gr.update(active_key="loading"),
                            gr.update(open=True)
                        )
                
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
                inputs=[input, setting, history],
                outputs=[code_output, history, preview, state_tab, code_drawer]
            )
            
            clear_btn.click(lambda: [], outputs=[history])

        return interface

    # Continue with existing chat interface code...
    pipeline = get_pipeline(name)
    inputs, outputs, preprocess, postprocess = get_interface_args(pipeline, name)
    fn = get_fn(name, preprocess, postprocess, api_key, local=local)

    if examples:
        formatted_examples = [[example, False] for example in examples]
        kwargs["examples"] = formatted_examples

    if pipeline == "chat":
        interface = gr.ChatInterface(
            fn=fn,
            additional_inputs=inputs,
            multimodal=True,
            **kwargs
        )
    else:
        interface = gr.Interface(fn=fn, inputs=inputs, outputs=outputs, **kwargs)

    return interface