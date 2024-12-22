import os
from typing import List, Dict, Generator
import gradio as gr
from crewai import Agent, Task, Crew
from crewai_tools import ScrapeWebsiteTool
import queue
import threading
import asyncio

class MessageQueue:
    def __init__(self):
        self.message_queue = queue.Queue()
        self.last_agent = None

    def add_message(self, message: Dict):
        print(f"Adding message to queue: {message}")
        self.message_queue.put(message)

    def get_messages(self) -> List[Dict]:
        messages = []
        while not self.message_queue.empty():
            messages.append(self.message_queue.get())
        return messages

class CrewManager:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.message_queue = MessageQueue()
        self.support_agent = None
        self.qa_agent = None
        self.current_agent = None
        self.scrape_tool = None

    def initialize_agents(self, website_url: str):
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        os.environ["OPENAI_API_KEY"] = self.api_key
        self.scrape_tool = ScrapeWebsiteTool(website_url=website_url)

        self.support_agent = Agent(
            role="Senior Support Representative",
            goal="Be the most friendly and helpful support representative",
            backstory="Expert at analyzing questions and providing comprehensive support",
            allow_delegation=False,
            verbose=True
        )

        self.qa_agent = Agent(
            role="Support Quality Assurance Specialist",
            goal="Ensure the highest quality of support responses",
            backstory="Expert at reviewing and improving support responses",
            verbose=True
        )

    def create_tasks(self, inquiry: str) -> List[Task]:
        inquiry_resolution = Task(
            description=f"""
            Analyze this inquiry thoroughly:
            {inquiry}
            
            Provide detailed support response.
            """,
            expected_output="Detailed support response addressing all aspects of the inquiry",
            tools=[self.scrape_tool],
            agent=self.support_agent
        )

        quality_review = Task(
            description="""
            Review and improve the support response to ensure it's comprehensive and helpful.
            Format the response appropriately with proper structure and clarity.
            """,
            expected_output="Final polished response ready for the customer",
            agent=self.qa_agent
        )

        return [inquiry_resolution, quality_review]

    async def process_support(self, inquiry: str, website_url: str) -> Generator[List[Dict], None, None]:
        def add_agent_messages(agent_name: str, tasks: str, emoji: str = "🤖"):
            self.message_queue.add_message({
                "role": "assistant",
                "content": agent_name,
                "metadata": {"title": f"{emoji} {agent_name}"}
            })
            
            self.message_queue.add_message({
                "role": "assistant",
                "content": tasks,
                "metadata": {"title": f"📋 Task for {agent_name}"}
            })

        def setup_next_agent(current_agent: str):
            if current_agent == "Senior Support Representative":
                self.current_agent = "Support Quality Assurance Specialist"
                add_agent_messages(
                    "Support Quality Assurance Specialist",
                    "Review and improve the support response"
                )

        def task_callback(task_output):
            raw_output = task_output.raw
            if "## Final Answer:" in raw_output:
                content = raw_output.split("## Final Answer:")[1].strip()
            else:
                content = raw_output.strip()
            
            if self.current_agent == "Support Quality Assurance Specialist":
                self.message_queue.add_message({
                    "role": "assistant",
                    "content": "Final response is ready!",
                    "metadata": {"title": "✅ Final Response"}
                })
                
                formatted_content = content
                formatted_content = formatted_content.replace("\n#", "\n\n#")
                formatted_content = formatted_content.replace("\n-", "\n\n-")
                formatted_content = formatted_content.replace("\n*", "\n\n*")
                formatted_content = formatted_content.replace("\n1.", "\n\n1.")
                formatted_content = formatted_content.replace("\n\n\n", "\n\n")
                
                self.message_queue.add_message({
                    "role": "assistant",
                    "content": formatted_content
                })
            else:
                self.message_queue.add_message({
                    "role": "assistant",
                    "content": content,
                    "metadata": {"title": f"✨ Output from {self.current_agent}"}
                })
                setup_next_agent(self.current_agent)

        try:
            self.initialize_agents(website_url)
            self.current_agent = "Senior Support Representative"

            yield [{
                "role": "assistant",
                "content": "Starting to process your inquiry...",
                "metadata": {"title": "🚀 Process Started"}
            }]

            add_agent_messages(
                "Senior Support Representative",
                "Analyze inquiry and provide comprehensive support"
            )

            crew = Crew(
                agents=[self.support_agent, self.qa_agent],
                tasks=self.create_tasks(inquiry),
                verbose=True,
                task_callback=task_callback
            )

            def run_crew():
                try:
                    crew.kickoff()
                except Exception as e:
                    print(f"Error in crew execution: {str(e)}")
                    self.message_queue.add_message({
                        "role": "assistant",
                        "content": f"Error: {str(e)}",
                        "metadata": {"title": "❌ Error"}
                    })

            thread = threading.Thread(target=run_crew)
            thread.start()

            while thread.is_alive() or not self.message_queue.message_queue.empty():
                messages = self.message_queue.get_messages()
                if messages:
                    yield messages
                await asyncio.sleep(0.1)

        except Exception as e:
            print(f"Error in process_support: {str(e)}")
            yield [{
                "role": "assistant",
                "content": f"An error occurred: {str(e)}",
                "metadata": {"title": "❌ Error"}
            }]

def registry(name: str, token: str | None = None, **kwargs):
    # Use provided token or get from environment
    default_api_key = os.environ.get("OPENAI_API_KEY")
    crew_manager = None

    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🤖 CrewAI Support")
        gr.Markdown("Get help from a crew of AI agents working together.")
        
        # Only show API key input if no default key is available
        api_key = gr.Textbox(
            label="OpenAI API Key",
            type="password",
            placeholder="Type your OpenAI API key and press Enter...",
            interactive=True,
            visible=not (token or default_api_key)  # Hide if token is provided or default exists
        )

        chatbot = gr.Chatbot(
            label="Support Process",
            height=600,
            show_label=True,
            visible=token or default_api_key,  # Show immediately if API key exists
            avatar_images=(None, "https://avatars.githubusercontent.com/u/170677839?v=4"),
            render_markdown=True
        )
        
        with gr.Row(equal_height=True):
            inquiry = gr.Textbox(
                label="Your Inquiry",
                placeholder="Enter your question...",
                scale=4,
                visible=token or default_api_key  # Show immediately if API key exists
            )
            website_url = gr.Textbox(
                label="Documentation URL",
                placeholder="Enter documentation URL to search...",
                scale=4,
                visible=token or default_api_key  # Show immediately if API key exists
            )
            btn = gr.Button(
                "Get Support", 
                variant="primary", 
                scale=1, 
                visible=token or default_api_key  # Show immediately if API key exists
            )

        async def process_input(inquiry_text, website_url_text, history, api_key_text):
            nonlocal crew_manager
            # Use the first available API key
            effective_api_key = token or api_key_text or default_api_key
            
            if not effective_api_key:
                history = history or []
                history.append(("You", f"Question: {inquiry_text}\nDocumentation: {website_url_text}"))
                history.append(("Assistant", "Please provide an OpenAI API key."))
                yield history
                return

            if crew_manager is None:
                crew_manager = CrewManager(api_key=effective_api_key)

            history = history or []
            history.append(("You", f"Question: {inquiry_text}\nDocumentation: {website_url_text}"))
            yield history

            try:
                async for messages in crew_manager.process_support(inquiry_text, website_url_text):
                    for msg in messages:
                        if msg.get("role") == "user":
                            history.append(("You", msg["content"]))
                        else:
                            content = msg["content"]
                            if "metadata" in msg and "title" in msg["metadata"]:
                                content = f"**{msg['metadata']['title']}**\n\n{content}"
                            history.append(("Assistant", content))
                    yield history
            except Exception as e:
                history.append(("Assistant", f"An error occurred: {str(e)}"))
                yield history

        def show_interface():
            return {
                api_key: gr.Textbox(visible=False),
                chatbot: gr.Chatbot(visible=True),
                inquiry: gr.Textbox(visible=True),
                website_url: gr.Textbox(visible=True),
                btn: gr.Button(visible=True)
            }

        # Only set up API key submission if no default key exists
        if not (token or default_api_key):
            api_key.submit(show_interface, None, [api_key, chatbot, inquiry, website_url, btn])
        
        btn.click(process_input, [inquiry, website_url, chatbot, api_key], [chatbot])
        inquiry.submit(process_input, [inquiry, website_url, chatbot, api_key], [chatbot])

    return demo