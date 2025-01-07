import os
from langchain_openai import ChatOpenAI
from browser_use import Agent
import gradio as gr
from typing import Callable
import asyncio

def get_fn(model_name: str, preprocess: Callable, postprocess: Callable, api_key: str):
    async def fn(message, history):
        inputs = preprocess(message, history)
        
        agent = Agent(
            task=inputs["message"],
            llm=ChatOpenAI(
                api_key=api_key,
                model=model_name
            )
        )
        
        try:
            result = await agent.run()
            return postprocess(result)
        except Exception as e:
            return f"Error: {str(e)}"
    
    return fn  # Remove sync_wrapper, return async function directly

def get_interface_args(pipeline):
    if pipeline == "browser":
        def preprocess(message, history):
            return {"message": message}

        def postprocess(result):
            if hasattr(result, 'all_results') and hasattr(result, 'all_model_outputs'):
                # Get the thought process from non-final results
                thoughts = [r.extracted_content for r in result.all_results if not r.is_done]
                # Get the final answer from the last result
                final_answer = next((r.extracted_content for r in reversed(result.all_results) if r.is_done), None)
                
                if final_answer:
                    # Return in Gradio's message format
                    return {
                        "role": "assistant",
                        "content": final_answer,
                        "metadata": {
                            "title": "🔍 " + " → ".join(thoughts)
                        }
                    }
            
            # Fallback to simple message format
            return {
                "role": "assistant",
                "content": str(result) if not isinstance(result, str) else result
            }

        return preprocess, postprocess
    else:
        raise ValueError(f"Unsupported pipeline type: {pipeline}")

def registry(name: str, token: str | None = None, **kwargs):
    api_key = token or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")

    pipeline = "browser"
    preprocess, postprocess = get_interface_args(pipeline)
    fn = get_fn(name, preprocess, postprocess, api_key)

    # Remove title and description from kwargs if they exist
    kwargs.pop('title', None)
    kwargs.pop('description', None)

    interface = gr.ChatInterface(
        fn=fn,
        title="Browser Use Agent",
        description="Chat with an AI agent that can perform browser tasks.",
        examples=["Go to amazon.com and find the best rated laptop and return the price.", 
                 "Find the current weather in New York"],
        **kwargs
    )

    return interface
