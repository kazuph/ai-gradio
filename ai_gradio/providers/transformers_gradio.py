import os
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch
import gradio as gr
from typing import Callable
from PIL import Image

def get_fn(model_name: str, preprocess: Callable, postprocess: Callable, **kwargs):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Get the full model path
    if "/" in model_name:
        model_path = model_name
    else:
        model_mapping = {
            "tulu-3": "allenai/llama-tulu-3-8b",
            "olmo-2-13b": "allenai/OLMo-2-1124-13B-Instruct",
            "smolvlm": "HuggingFaceTB/SmolVLM-Instruct",
            "phi-4": "microsoft/phi-4",
            "moondream": "vikhyatk/moondream2",
        }
        model_path = model_mapping.get(model_name)
        if not model_path:
            raise ValueError(f"Unknown model name: {model_name}")

    # Load model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    
    if model_name == "moondream":
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            revision="2025-01-09",
            trust_remote_code=True,
            device_map={"": "cuda" if torch.cuda.is_available() else "cpu"}
        )
    elif device == "cuda":
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            torch_dtype=torch.float16
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            torch_dtype=torch.float32
        )

    def predict(message, history, temperature=0.7, max_tokens=512, image=None):
        # Create a new list for history to avoid sharing between sessions
        history = list(history) if history else []
        
        if model_name == "moondream":
            if isinstance(message, dict):
                text = message["text"]
                # Get the first image from files if available
                files = message.get("files", [])
                image = files[0] if files else image  # Use provided image if no files
                
            if image is not None:
                # Ensure image is a PIL Image
                if not isinstance(image, Image.Image):
                    try:
                        image = Image.open(image)
                    except Exception as e:
                        return f"Error processing image: {str(e)}"
                    
                # Generate response and return as a string
                response = model.query(image, text)["answer"]
                return response
            else:
                return "Please provide an image to analyze."

        # Format conversation history
        if isinstance(message, dict):
            message = message["text"]
        
        messages = []
        for user_msg, assistant_msg in history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})
        messages.append({"role": "user", "content": message})

        # Convert to model format
        input_text = tokenizer.apply_chat_template(messages, tokenize=False)
        inputs = tokenizer(input_text, return_tensors="pt").to(device)

        # Generate response
        generation_config = {
            "input_ids": inputs["input_ids"],
            "max_new_tokens": max_tokens,
            "temperature": float(temperature),  # Ensure temperature is a float
            "do_sample": True,
            "pad_token_id": tokenizer.eos_token_id
        }
        
        outputs = model.generate(**generation_config)
        
        # For phi-4, extract only the new generated text
        if model_name == "phi-4":
            input_length = inputs["input_ids"].shape[1]
            generated_tokens = outputs[0][input_length:]
            response = tokenizer.decode(generated_tokens, skip_special_tokens=True)
        else:
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        return response

    return predict

def get_interface_args(pipeline):
    if pipeline == "chat":
        def preprocess(message, history):
            return {"message": message, "history": history}

        def postprocess(response):
            return response

        return None, None, preprocess, postprocess
    elif pipeline == "vision-chat":
        def preprocess(message, history):
            return {"message": message, "history": history}

        def postprocess(response):
            return response

        return [gr.Textbox(label="Message"), gr.Image(type="pil")], None, preprocess, postprocess
    else:
        raise ValueError(f"Unsupported pipeline type: {pipeline}")

def get_pipeline(model_name):
    if model_name == "moondream":
        return "vision-chat"
    return "chat"

def registry(name: str = None, **kwargs):
    pipeline = get_pipeline(name)
    inputs, outputs, preprocess, postprocess = get_interface_args(pipeline)
    fn = get_fn(name, preprocess, postprocess, **kwargs)

    if pipeline == "vision-chat":
        interface = gr.ChatInterface(
            fn=fn,
            additional_inputs=[
                gr.Slider(0, 1, 0.7, label="Temperature"),
                gr.Slider(1, 2048, 512, label="Max tokens"),
            ],
            multimodal=True  # Enable multimodal input
        )
    else:
        interface = gr.ChatInterface(
            fn=fn,
            additional_inputs=[
                gr.Slider(0, 1, 0.7, label="Temperature"),
                gr.Slider(1, 2048, 512, label="Max tokens"),
            ]
        )
    
    return interface 