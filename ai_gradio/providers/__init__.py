import gradio as gr

def custom_load(name: str, src: dict, **kwargs):
    # Split name into provider and model if specified
    if ':' in name:
        provider, model = name.split(':')
    else:
        provider = 'openai'  # Default to OpenAI if no provider specified
        model = name
    
    # Create provider-specific model key
    model_key = f"{provider}:{model}"
    
    if model_key not in src:
        available_models = [k for k in src.keys()]
        raise ValueError(f"Model {model_key} not found. Available models: {available_models}")
    return src[model_key](name=model, **kwargs)

# Add the custom load function to gradio
gr.load = custom_load

registry = {}

try:
    from .openai_gradio import registry as openai_registry
    registry.update({f"openai:{k}": openai_registry for k in ['gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo', 'gpt-4o-mini-realtime-preview-2024-12-17']})
except ImportError:
    pass

try:
    from .gemini_gradio import registry as gemini_registry
    registry.update({f"gemini:{k}": gemini_registry for k in ['gemini-pro', 'gemini-pro-vision', 'gemini-2.0-flash-exp']})
except ImportError:
    pass

try:
    from .crewai_gradio import registry as crewai_registry
    # Add CrewAI models with their own prefix
    registry.update({f"crewai:{k}": crewai_registry for k in ['gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo']})
except ImportError:
    pass

if not registry:
    raise ImportError(
        "No providers installed. Install with either:\n"
        "pip install 'ai-gradio[openai]' for OpenAI support\n"
        "pip install 'ai-gradio[gemini]' for Gemini support\n"
        "pip install 'ai-gradio[crewai]' for CrewAI support\n"
        "pip install 'ai-gradio[all]' for all providers"
    )

__all__ = ["registry"]
