import os
import soundfile as sf
from kokoro_onnx import Kokoro
import gradio as gr
from typing import Callable
from huggingface_hub import hf_hub_download

__version__ = "0.0.1"

def get_fn(model_name: str, preprocess: Callable, postprocess: Callable):
    # Download model and voices.json from HuggingFace Hub
    model_path = hf_hub_download(
        repo_id="hexgrad/Kokoro-82M",
        filename="kokoro-v0_19.onnx",
        repo_type="model"
    )
    
    voices_path = hf_hub_download(
        repo_id="akhaliq/Kokoro-82M",
        filename="voices.json",
        repo_type="model"
    )

    def chat_response(message, history, voice="af_sarah", speed=1.0, lang="en-us"):
        try:
            kokoro = Kokoro(model_path, voices_path)
            samples, sample_rate = kokoro.create(
                text=message,
                voice=voice,
                speed=speed,
                lang=lang
            )
            
            # Save to temporary file with unique name based on history length
            output_path = f"response_{len(history)}.wav"
            sf.write(output_path, samples, sample_rate)
            
            return {
                "role": "assistant",
                "content": {
                    "path": output_path
                }
            }
            
        except Exception as e:
            return f"Error generating audio: {str(e)}"
            
    return chat_response

def registry(name: str, **kwargs):
    """Register kokoro TTS interface"""
    
    interface = gr.ChatInterface(
        fn=get_fn(name, lambda x: x, lambda x: x),
        additional_inputs=[
            gr.Dropdown(
                choices=["af_sarah", "en_jenny", "en_ryan"],
                value="af_sarah",
                label="Voice"
            ),
            gr.Slider(
                minimum=0.5,
                maximum=2.0,
                value=1.0,
                step=0.1,
                label="Speed"
            ),
            gr.Dropdown(
                choices=["en-us", "en-gb"],
                value="en-us", 
                label="Language"
            )
        ],
        title="Kokoro Text-to-Speech",
        description="Generate speech from text using Kokoro TTS",
        **kwargs
    )
    
    return interface 