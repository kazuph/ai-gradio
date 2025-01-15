import os
import base64
import gradio as gr
import json
import aiohttp

__version__ = "0.0.1"

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

def registry(name: str, token: str | None = None, **kwargs):
    api_key = token or os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise ValueError("MINIMAX_API_KEY environment variable is not set.")

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