from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain import hub
from langchain_core.messages import AIMessage, HumanMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
import gradio as gr
from typing import Generator, List, Dict

def create_agent(model_name: str = None):
    # Initialize search tool
    search = TavilySearchResults()
    tools = [search]
    
    # Initialize LLM
    llm = ChatOpenAI(
        model_name=model_name if model_name else "gpt-3.5-turbo-0125",
        temperature=0
    )
    
    # Get the prompt
    prompt = hub.pull("hwchase17/openai-functions-agent")
    
    # Create the agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    # Create the executor
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

def stream_agent_response(agent: AgentExecutor, message: str, history: List) -> Generator[Dict, None, None]:
    # First yield the thinking message
    yield {
        "role": "assistant",
        "content": "Let me think about that...",
        "metadata": {"title": "🤔 Thinking"}
    }
    
    try:
        # Convert history to LangChain format
        chat_history = []
        for msg in history:
            if msg["role"] == "user":
                chat_history.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                chat_history.append(AIMessage(content=msg["content"]))
        
        # Run the agent
        response = agent.invoke({
            "input": message,
            "chat_history": chat_history
        })
        
        # Yield the final response
        yield {
            "role": "assistant",
            "content": response["output"]
        }
                
    except Exception as e:
        yield {
            "role": "assistant",
            "content": f"Error: {str(e)}",
            "metadata": {"title": "❌ Error"}
        }

async def interact_with_agent(message: str, history: List, model_name: str = None) -> Generator[List, None, None]:
    # Add user message
    history.append({"role": "user", "content": message})
    yield history
    
    # Create agent instance with specified model
    agent = create_agent(model_name)
    
    # Stream agent responses
    for response in stream_agent_response(agent, message, history):
        history.append(response)
        yield history

def registry(name: str, **kwargs):
    # Extract model name from the name parameter
    model_name = name.split(':')[-1] if ':' in name else None
    
    with gr.Blocks() as demo:
        gr.Markdown("# LangChain Assistant 🦜️")
        
        chatbot = gr.Chatbot(
            type="messages",
            label="Agent",
            avatar_images=(None, "https://python.langchain.com/img/favicon.ico"),
            height=500
        )
        
        msg = gr.Textbox(
            label="Your message",
            placeholder="Type your message here...",
            lines=1
        )

        async def handle_message(message, history):
            async for response in interact_with_agent(message, history, model_name=model_name):
                yield response

        msg.submit(
            fn=handle_message,
            inputs=[msg, chatbot],
            outputs=[chatbot],
            api_name="predict"
        ).then(lambda _:"", msg, msg)

    return demo
