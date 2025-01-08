import os
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch
import gradio as gr
from typing import Callable

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
        }
        model_path = model_mapping.get(model_name)
        if not model_path:
            raise ValueError(f"Unknown model name: {model_name}")

    # Load model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    
    if device == "cuda":
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

    def predict(message, history, temperature=0.7, max_tokens=512):
        # Format conversation history
        messages = []
        for user_msg, assistant_msg in history:
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})
        messages.append({"role": "user", "content": message})

        # Convert to model format
        input_text = tokenizer.apply_chat_template(messages, tokenize=False)
        inputs = tokenizer(input_text, return_tensors="pt").to(device)

        # Generate response
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        yield response

    return predict

def get_interface_args(pipeline):
    if pipeline == "chat":
        def preprocess(message, history):
            return {"message": message, "history": history}

        def postprocess(response):
            return response

        return None, None, preprocess, postprocess
    else:
        raise ValueError(f"Unsupported pipeline type: {pipeline}")

def get_pipeline(model_name):
    return "chat"

def registry(name: str = None, **kwargs):
    pipeline = get_pipeline(name)
    inputs, outputs, preprocess, postprocess = get_interface_args(pipeline)
    fn = get_fn(name, preprocess, postprocess, **kwargs)

    interface = gr.ChatInterface(
        fn=fn,
        additional_inputs=[
            gr.Slider(0, 1, 0.7, label="Temperature"),
            gr.Slider(1, 2048, 512, label="Max tokens"),
        ]
    )
    
    return interface 