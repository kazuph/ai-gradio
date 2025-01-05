import os
from typing import Callable
import gradio as gr
import google.generativeai as genai
import base64
import json
import numpy as np
import websockets.sync.client
from gradio_webrtc import StreamHandler, WebRTC, get_twilio_turn_credentials
import cv2
import PIL.Image
import io
import re
import modelscope_studio.components.base as ms
import modelscope_studio.components.legacy as legacy
import modelscope_studio.components.antd as antd


__version__ = "0.0.3"

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


class GeminiConfig:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.host = "generativelanguage.googleapis.com"
        self.model = "models/gemini-2.0-flash-exp"
        self.ws_url = f"wss://{self.host}/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={self.api_key}"


class AudioProcessor:
    @staticmethod
    def encode_audio(data, sample_rate):
        encoded = base64.b64encode(data.tobytes()).decode("UTF-8")
        return {
            "realtimeInput": {
                "mediaChunks": [
                    {
                        "mimeType": f"audio/pcm;rate={sample_rate}",
                        "data": encoded,
                    }
                ],
            },
        }

    @staticmethod
    def process_audio_response(data):
        audio_data = base64.b64decode(data)
        return np.frombuffer(audio_data, dtype=np.int16)


def detection(frame, conf_threshold=0.3):
    """Process video frame."""
    try:
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create PIL Image
        pil_image = PIL.Image.fromarray(image_rgb)
        pil_image.thumbnail([1024, 1024])
        
        # Convert back to numpy array
        processed_frame = np.array(pil_image)
        
        # Convert back to BGR for OpenCV
        processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_RGB2BGR)
        
        return processed_frame
    except Exception as e:
        print(f"Error processing frame: {e}")
        return frame


class GeminiHandler(StreamHandler):
    def __init__(self, expected_layout="mono", output_sample_rate=24000, output_frame_size=480) -> None:
        super().__init__(expected_layout, output_sample_rate, output_frame_size, input_sample_rate=24000)
        self.config = GeminiConfig()
        self.ws = None
        self.all_output_data = None
        self.audio_processor = AudioProcessor()
        self.current_frame = None

    def copy(self):
        handler = GeminiHandler(
            expected_layout=self.expected_layout,
            output_sample_rate=self.output_sample_rate,
            output_frame_size=self.output_frame_size,
        )
        return handler

    def _initialize_websocket(self):
        try:
            self.ws = websockets.sync.client.connect(self.config.ws_url, timeout=30)
            initial_request = {
                "setup": {
                    "model": self.config.model,
                }
            }
            self.ws.send(json.dumps(initial_request))
            setup_response = json.loads(self.ws.recv())
            print(f"Setup response: {setup_response}")
        except websockets.exceptions.WebSocketException as e:
            print(f"WebSocket connection failed: {str(e)}")
            self.ws = None
        except Exception as e:
            print(f"Setup failed: {str(e)}")
            self.ws = None

    def process_video_frame(self, frame):
        self.current_frame = frame
        _, buffer = cv2.imencode('.jpg', frame)
        image_data = base64.b64encode(buffer).decode('utf-8')
        return image_data

    def receive(self, frame: tuple[int, np.ndarray]) -> None:
        try:
            if not self.ws:
                self._initialize_websocket()

            _, array = frame
            array = array.squeeze()
            
            audio_data = self.audio_processor.encode_audio(array, self.output_sample_rate)
            
            message = {
                "realtimeInput": {
                    "mediaChunks": [
                        {
                            "mimeType": f"audio/pcm;rate={self.output_sample_rate}",
                            "data": audio_data["realtimeInput"]["mediaChunks"][0]["data"],
                        }
                    ],
                }
            }
            
            if self.current_frame is not None:
                image_data = self.process_video_frame(self.current_frame)
                message["realtimeInput"]["mediaChunks"].append({
                    "mimeType": "image/jpeg",
                    "data": image_data
                })

            self.ws.send(json.dumps(message))
        except Exception as e:
            print(f"Error in receive: {str(e)}")
            if self.ws:
                self.ws.close()
            self.ws = None

    def _process_server_content(self, content):
        for part in content.get("parts", []):
            data = part.get("inlineData", {}).get("data", "")
            if data:
                audio_array = self.audio_processor.process_audio_response(data)
                if self.all_output_data is None:
                    self.all_output_data = audio_array
                else:
                    self.all_output_data = np.concatenate((self.all_output_data, audio_array))

                while self.all_output_data.shape[-1] >= self.output_frame_size:
                    yield (self.output_sample_rate, self.all_output_data[: self.output_frame_size].reshape(1, -1))
                    self.all_output_data = self.all_output_data[self.output_frame_size :]

    def generator(self):
        while True:
            if not self.ws:
                print("WebSocket not connected")
                yield None
                continue

            try:
                message = self.ws.recv(timeout=5)
                msg = json.loads(message)

                if "serverContent" in msg:
                    content = msg["serverContent"].get("modelTurn", {})
                    yield from self._process_server_content(content)
            except TimeoutError:
                print("Timeout waiting for server response")
                yield None
            except Exception as e:
                print(f"Error in generator: {str(e)}")
                yield None

    def emit(self) -> tuple[int, np.ndarray] | None:
        if not self.ws:
            return None
        if not hasattr(self, "_generator"):
            self._generator = self.generator()
        try:
            return next(self._generator)
        except StopIteration:
            self.reset()
            return None

    def reset(self) -> None:
        if hasattr(self, "_generator"):
            delattr(self, "_generator")
        self.all_output_data = None

    def shutdown(self) -> None:
        if self.ws:
            self.ws.close()

    def check_connection(self):
        try:
            if not self.ws or self.ws.closed:
                self._initialize_websocket()
            return True
        except Exception as e:
            print(f"Connection check failed: {str(e)}")
            return False


def get_fn(model_name: str, preprocess: Callable, postprocess: Callable, api_key: str):
    def fn(message, history, enable_search):
        inputs = preprocess(message, history, enable_search)
        is_gemini = model_name.startswith("gemini-")
        
        if is_gemini:
            genai.configure(api_key=api_key)
            
            generation_config = {
                "temperature": 1,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
                "response_mime_type": "text/plain",
            }
            
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config
            )
            
            chat = model.start_chat(history=inputs.get("history", []))
            
            if inputs.get("enable_search"):
                response = chat.send_message(
                    inputs["message"],
                    stream=True,
                    tools='google_search_retrieval'
                )
            else:
                response = chat.send_message(inputs["message"], stream=True)
            
            response_text = ""
            for chunk in response:
                if chunk.text:
                    response_text += chunk.text
                    yield {"role": "assistant", "content": response_text}

    return fn


def get_interface_args(pipeline, model_name: str):
    if pipeline == "chat":
        inputs = [gr.Checkbox(label="Enable Search", value=False)]
        outputs = None

        def preprocess(message, history, enable_search):
            is_gemini = model_name.startswith("gemini-")
            if is_gemini:
                # Handle multimodal input
                if isinstance(message, dict):
                    parts = []
                    if message.get("text"):
                        parts.append({"text": message["text"]})
                    if message.get("files"):
                        for file in message["files"]:
                            # Determine file type and handle accordingly
                            if isinstance(file, str):  # If it's a file path
                                mime_type = None
                                if file.lower().endswith('.pdf'):
                                    mime_type = "application/pdf"
                                elif file.lower().endswith('.txt'):
                                    mime_type = "text/plain"
                                elif file.lower().endswith('.html'):
                                    mime_type = "text/html"
                                elif file.lower().endswith('.md'):
                                    mime_type = "text/md"
                                elif file.lower().endswith('.csv'):
                                    mime_type = "text/csv"
                                elif file.lower().endswith(('.js', '.javascript')):
                                    mime_type = "application/x-javascript"
                                elif file.lower().endswith('.py'):
                                    mime_type = "application/x-python"
                                
                                if mime_type:
                                    try:
                                        uploaded_file = genai.upload_file(file)
                                        parts.append(uploaded_file)
                                    except Exception as e:
                                        print(f"Error uploading file: {e}")
                                else:
                                    with open(file, "rb") as f:
                                        image_data = f.read()
                                        import base64
                                        image_data = base64.b64encode(image_data).decode()
                                        parts.append({
                                            "inline_data": {
                                                "mime_type": "image/jpeg",
                                                "data": image_data
                                            }
                                        })
                            else:  # If it's binary data, treat as image
                                import base64
                                image_data = base64.b64encode(file).decode()
                                parts.append({
                                    "inline_data": {
                                        "mime_type": "image/jpeg",
                                        "data": image_data
                                    }
                                })
                    message_parts = parts
                else:
                    message_parts = [{"text": message}]

                # Process history
                gemini_history = []
                for entry in history:
                    # Handle different history formats
                    if isinstance(entry, (list, tuple)):
                        user_msg, assistant_msg = entry
                    else:
                        # If it's a dict with role/content format
                        if entry.get("role") == "user":
                            user_msg = entry.get("content")
                            continue  # Skip to next iteration to get assistant message
                        elif entry.get("role") == "assistant":
                            assistant_msg = entry.get("content")
                            continue  # Skip to next iteration
                        else:
                            continue  # Skip unknown roles

                    # Process user message
                    if isinstance(user_msg, dict):
                        parts = []
                        if user_msg.get("text"):
                            parts.append({"text": user_msg["text"]})
                        if user_msg.get("files"):
                            for file in user_msg["files"]:
                                if isinstance(file, str):
                                    mime_type = None
                                    if file.lower().endswith('.pdf'):
                                        mime_type = "application/pdf"
                                    # ... (same mime type checks as before)
                                    
                                    if mime_type:
                                        try:
                                            uploaded_file = genai.upload_file(file)
                                            parts.append(uploaded_file)
                                        except Exception as e:
                                            print(f"Error uploading file in history: {e}")
                                    else:
                                        with open(file, "rb") as f:
                                            image_data = f.read()
                                            import base64
                                            image_data = base64.b64encode(image_data).decode()
                                            parts.append({
                                                "inline_data": {
                                                    "mime_type": "image/jpeg",
                                                    "data": image_data
                                                }
                                            })
                                else:
                                    import base64
                                    image_data = base64.b64encode(file).decode()
                                    parts.append({
                                        "inline_data": {
                                            "mime_type": "image/jpeg",
                                            "data": image_data
                                        }
                                    })
                        gemini_history.append({
                            "role": "user",
                            "parts": parts
                        })
                    else:
                        gemini_history.append({
                            "role": "user",
                            "parts": [{"text": str(user_msg)}]
                        })
                    
                    # Process assistant message
                    gemini_history.append({
                        "role": "model",
                        "parts": [{"text": str(assistant_msg)}]
                    })
                
                return {
                    "history": gemini_history,
                    "message": message_parts,
                    "enable_search": enable_search
                }
            else:
                messages = []
                for user_msg, assistant_msg in history:
                    messages.append({"role": "user", "content": user_msg})
                    messages.append({"role": "assistant", "content": assistant_msg})
                messages.append({"role": "user", "content": message})
                return {"messages": messages}

        postprocess = lambda x: x
    else:
        raise ValueError(f"Unsupported pipeline type: {pipeline}")
    return inputs, outputs, preprocess, postprocess


def get_pipeline(model_name):
    return "chat"


def registry(
    name: str, 
    token: str | None = None, 
    examples: list | None = None,
    enable_voice: bool = False,
    enable_video: bool = False,
    coder: bool = False,
    **kwargs
):
    env_key = "GEMINI_API_KEY"
    api_key = token or os.environ.get(env_key)
    if not api_key:
        raise ValueError(f"{env_key} environment variable is not set.")

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

            /* Add new CSS for image upload */
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
                                        <h1>Gemini Code Generator</h1>
                                    </div>
                                """)
                                
                                # Add image upload section
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
                messages = []
                messages.append({
                    "role": "user",
                    "parts": [{"text": setting["system"]}]
                })
                messages.append({
                    "role": "model",
                    "parts": [{"text": "I understand. I will help you write clean, efficient web code."}]
                })
                
                # Add history
                for h in history:
                    messages.append({
                        "role": "user",
                        "parts": [{"text": h[0]}]
                    })
                    messages.append({
                        "role": "model",
                        "parts": [{"text": h[1]}]
                    })
                
                # Add current query with image if provided
                current_message = []
                if image:
                    image_data = genai.upload_file(image)
                    current_message.append(image_data)
                current_message.append({"text": query})
                messages.append({
                    "role": "user",
                    "parts": current_message
                })
                
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(model_name=name)
                response = model.generate_content(messages, stream=True)
                
                response_text = ""
                for chunk in response:
                    if chunk.text:
                        response_text += chunk.text
                        # Return all 5 required outputs
                        yield (
                            response_text,  # code_output (modelscopemarkdown)
                            history,        # state
                            None,          # preview (html)
                            gr.update(active_key="loading"),  # state_tab (antdtabs)
                            gr.update(open=True)  # code_drawer (antddrawer)
                        )
                
                clean_code = remove_code_block(response_text)
                new_history = history + [(query, response_text)]
                
                # Final yield with all outputs
                yield (
                    response_text,  # code_output (modelscopemarkdown)
                    new_history,    # state
                    send_to_preview(clean_code),  # preview (html)
                    gr.update(active_key="render"),  # state_tab (antdtabs)
                    gr.update(open=False)  # code_drawer (antddrawer)
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

    # Regular chat interface code continues here...
    pipeline = get_pipeline(name)
    inputs, outputs, preprocess, postprocess = get_interface_args(pipeline, name)
    fn = get_fn(name, preprocess, postprocess, api_key)

    if examples:
        formatted_examples = [[example, False] for example in examples]
        kwargs["examples"] = formatted_examples

    if pipeline == "chat":
        if enable_voice or enable_video:
            interface = gr.Blocks()
            with interface:
                gr.HTML(
                    """
                    <div style='text-align: center'>
                        <h1>Gemini Chat</h1>
                    </div>
                    """
                )
                
                gemini_handler = GeminiHandler()
                
                with gr.Row():
                    with gr.Column(scale=1):
                        if enable_video:
                            video = WebRTC(
                                label="Stream",
                                mode="send-receive",
                                modality="video",
                                rtc_configuration=get_twilio_turn_credentials()
                            )

                        if enable_voice:
                            audio = WebRTC(
                                label="Voice Chat",
                                modality="audio",
                                mode="send-receive",
                                rtc_configuration=get_twilio_turn_credentials(),
                            )

                if enable_video:
                    video.stream(
                        fn=lambda frame: (frame, detection(frame)),
                        inputs=[video],
                        outputs=[video],
                        time_limit=90,
                        concurrency_limit=10
                    )

                if enable_voice:
                    audio.stream(
                        gemini_handler,
                        inputs=[audio], 
                        outputs=[audio], 
                        time_limit=90, 
                        concurrency_limit=10
                    )
        else:
            interface = gr.ChatInterface(
                fn=fn,
                additional_inputs=inputs,
                multimodal=True,
                type="messages",
                **kwargs
            )
    else:
        interface = gr.Interface(fn=fn, inputs=inputs, outputs=outputs, **kwargs)

    return interface