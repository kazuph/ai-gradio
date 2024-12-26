import os
from openai import OpenAI
import gradio as gr
from typing import Callable
from fireworks.client.audio import AudioInference

__version__ = "0.0.3"

LANGUAGES = {
    "en": "english", "zh": "chinese", "de": "german", "es": "spanish",
    "ru": "russian", "ko": "korean", "fr": "french", "ja": "japanese",
    "pt": "portuguese", "tr": "turkish", "pl": "polish", "ca": "catalan",
    "nl": "dutch", "ar": "arabic", "sv": "swedish", "it": "italian",
    "id": "indonesian", "hi": "hindi", "fi": "finnish", "vi": "vietnamese",
    "he": "hebrew", "uk": "ukrainian", "el": "greek", "ms": "malay",
    "cs": "czech", "ro": "romanian", "da": "danish", "hu": "hungarian",
    "ta": "tamil", "no": "norwegian", "th": "thai", "ur": "urdu",
    "hr": "croatian", "bg": "bulgarian", "lt": "lithuanian", "la": "latin",
    "mi": "maori", "ml": "malayalam", "cy": "welsh", "sk": "slovak",
    "te": "telugu", "fa": "persian", "lv": "latvian", "bn": "bengali",
    "sr": "serbian", "az": "azerbaijani", "sl": "slovenian", "kn": "kannada",
    "et": "estonian", "mk": "macedonian", "br": "breton", "eu": "basque",
    "is": "icelandic", "hy": "armenian", "ne": "nepali", "mn": "mongolian",
    "bs": "bosnian", "kk": "kazakh", "sq": "albanian", "sw": "swahili",
    "gl": "galician", "mr": "marathi", "pa": "punjabi", "si": "sinhala",
    "km": "khmer", "sn": "shona", "yo": "yoruba", "so": "somali",
    "af": "afrikaans", "oc": "occitan", "ka": "georgian", "be": "belarusian",
    "tg": "tajik", "sd": "sindhi", "gu": "gujarati", "am": "amharic",
    "yi": "yiddish", "lo": "lao", "uz": "uzbek", "fo": "faroese",
    "ht": "haitian creole", "ps": "pashto", "tk": "turkmen", "nn": "nynorsk",
    "mt": "maltese", "sa": "sanskrit", "lb": "luxembourgish", "my": "myanmar",
    "bo": "tibetan", "tl": "tagalog", "mg": "malagasy", "as": "assamese",
    "tt": "tatar", "haw": "hawaiian", "ln": "lingala", "ha": "hausa",
    "ba": "bashkir", "jw": "javanese", "su": "sundanese", "yue": "cantonese"
}

# Language code lookup by name, with additional aliases
TO_LANGUAGE_CODE = {
    **{language: code for code, language in LANGUAGES.items()},
    "burmese": "my",
    "valencian": "ca",
    "flemish": "nl",
    "haitian": "ht",
    "letzeburgesch": "lb",
    "pushto": "ps",
    "panjabi": "pa",
    "moldavian": "ro",
    "moldovan": "ro",
    "sinhalese": "si",
    "castilian": "es",
    "mandarin": "zh"
}


def get_fn(model_name: str, preprocess: Callable, postprocess: Callable, api_key: str):
    if "whisper" in model_name:
        def fn(message, history, audio_input=None):
            # Handle audio input if provided
            if audio_input:
                if not audio_input.endswith('.wav'):
                    new_path = audio_input + '.wav'
                    os.rename(audio_input, new_path)
                    audio_input = new_path
                
                base_url = (
                    "https://audio-turbo.us-virginia-1.direct.fireworks.ai" 
                    if model_name == "whisper-v3-turbo" 
                    else "https://audio-prod.us-virginia-1.direct.fireworks.ai"
                )
                
                client = AudioInference(
                    model=model_name,
                    base_url=base_url,
                    api_key=api_key
                )
                
                with open(audio_input, "rb") as f:
                    audio_data = f.read()
                response = client.transcribe(audio=audio_data)
                return {"role": "assistant", "content": response.text}
            
            # Handle text message
            if isinstance(message, dict):  # Multimodal input
                audio_path = message.get("files", [None])[0] or message.get("audio")
                text = message.get("text", "")
                if audio_path:
                    # Process audio file
                    return fn(None, history, audio_path)
                return {"role": "assistant", "content": "No audio input provided."}
            else:  # String input
                return {"role": "assistant", "content": "Please upload an audio file or use the microphone to record audio."}

    else:
        def fn(message, history, audio_input=None):
            # Ignore audio_input for non-whisper models
            inputs = preprocess(message, history)
            client = OpenAI(
                base_url="https://api.fireworks.ai/inference/v1",
                api_key=api_key
            )
            
            model_path = (
                "accounts/fireworks/agents/f1-preview" if model_name == "f1-preview"
                else "accounts/fireworks/agents/f1-mini-preview" if model_name == "f1-mini"
                else f"accounts/fireworks/models/{model_name}"
            )
            
            completion = client.chat.completions.create(
                model=model_path,
                messages=[{"role": "user", "content": inputs["prompt"]}],
                stream=True,
                max_tokens=1024,
                temperature=0.7,
                top_p=1,
            )
            
            response_text = ""
            for chunk in completion:
                delta = chunk.choices[0].delta.content or ""
                response_text += delta
                yield {"role": "assistant", "content": response_text}

    return fn


def get_interface_args(pipeline):
    if pipeline == "audio":
        inputs = [
            gr.Audio(sources=["microphone"], type="filepath"),
            gr.Radio(["transcribe"], label="Task", value="transcribe"),
        ]
        outputs = "text"

        def preprocess(audio_path, task, text, history):
            if audio_path and not audio_path.endswith('.wav'):
                new_path = audio_path + '.wav'
                os.rename(audio_path, new_path)
                audio_path = new_path
            return {"role": "user", "content": {"audio_path": audio_path, "task": task}}

        def postprocess(text):
            return {"role": "assistant", "content": text}

    elif pipeline == "chat":
        inputs = gr.Textbox(label="Message")
        outputs = "text"

        def preprocess(message, history):
            return {"prompt": message}

        def postprocess(response):
            return response

    else:
        raise ValueError(f"Unsupported pipeline type: {pipeline}")
    
    return inputs, outputs, preprocess, postprocess


def get_pipeline(model_name):
    if "whisper" in model_name:
        return "audio"
    return "chat"


def registry(name: str, token: str | None = None, **kwargs):
    """
    Create a Gradio Interface for a model on Fireworks.
    Can be used directly or with gr.load:

    Example:
        # Direct usage
        interface = fireworks_gradio.registry("whisper-v3", token="your-api-key")
        interface.launch()

        # With gr.load
        gr.load(
            name='whisper-v3',
            src=fireworks_gradio.registry,
        ).launch()

    Parameters:
        name (str): The name of the OpenAI model.
        token (str, optional): The API key for OpenAI.
    """
    # Make the function compatible with gr.load by accepting name as a positional argument
    if not isinstance(name, str):
        raise ValueError("Model name must be a string")

    api_key = token or os.environ.get("FIREWORKS_API_KEY")
    if not api_key:
        raise ValueError("FIREWORKS_API_KEY environment variable is not set.")

    pipeline = get_pipeline(name)
    _, _, preprocess, postprocess = get_interface_args(pipeline)
    fn = get_fn(name, preprocess, postprocess, api_key)

    description = kwargs.pop("description", None)
    if "whisper" in name:
        description = (description or "") + """
        \n\nSupported inputs:
        - Upload audio files using the textbox
        - Record audio using the microphone
        """

        with gr.Blocks() as interface:
            chatbot = gr.Chatbot(type="messages")
            with gr.Row():
                mic = gr.Audio(sources=["microphone"], type="filepath", label="Record Audio")
            
            def process_audio(audio_path):
                if audio_path:
                    if not audio_path.endswith('.wav'):
                        new_path = audio_path + '.wav'
                        os.rename(audio_path, new_path)
                        audio_path = new_path
                    
                    # Create message format expected by fn
                    message = {"files": [audio_path], "text": ""}
                    response = fn(message, [])
                    
                    return [
                        {"role": "user", "content": gr.Audio(value=audio_path)},
                        {"role": "assistant", "content": response["content"]}
                    ]
                return []

            mic.change(
                fn=process_audio,
                inputs=[mic],
                outputs=[chatbot]
            )

    else:
        # For non-whisper models, use regular ChatInterface
        interface = gr.ChatInterface(
            fn=fn,
            type="messages",
            description=description,
            **kwargs
        )

    return interface


# Add these to make the module more discoverable
MODELS = [
    "whisper-v3",
    "whisper-v3-turbo",
    "f1-preview",
    "f1-mini",
    # Add other supported models here
]

def get_all_models():
    """Returns a list of all supported models."""
    return MODELS