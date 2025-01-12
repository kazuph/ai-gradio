import os
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.tools.retriever import create_retriever_tool
from langchain import hub
import gradio as gr
from typing import Callable

def registry(name: str, token: str | None = None, **kwargs):
    # Set up environment variables
    api_key = token or os.environ.get("LANGCHAIN_API_KEY")
    if not api_key:
        raise ValueError("LANGCHAIN_API_KEY environment variable is not set.")
    
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = api_key

    # Create tools
    search = TavilySearchResults()
    
    # Create retriever
    loader = WebBaseLoader("https://docs.smith.langchain.com/overview")
    docs = loader.load()
    documents = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200
    ).split_documents(docs)
    vector = FAISS.from_documents(documents, OpenAIEmbeddings())
    retriever = vector.as_retriever()
    
    retriever_tool = create_retriever_tool(
        retriever,
        "langsmith_search",
        "Search for information about LangSmith. For any questions about LangSmith, you must use this tool!"
    )

    tools = [search, retriever_tool]

    # Create agent components
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0)
    prompt = hub.pull("hwchase17/openai-functions-agent")
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # Create Gradio interface
    with gr.Blocks() as interface:
        chatbot = gr.Chatbot()
        msg = gr.Textbox()
        clear = gr.Button("Clear")

        def user(user_message, history):
            return "", history + [[user_message, None]]

        def bot(history):
            user_message = history[-1][0]
            response = agent_executor.invoke({"input": user_message})
            history[-1][1] = response["output"]
            return history

        msg.submit(user, [msg, chatbot], [msg, chatbot], queue=False).then(
            bot, chatbot, chatbot
        )
        clear.click(lambda: None, None, chatbot, queue=False)

    return interface