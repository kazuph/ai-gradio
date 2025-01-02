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

class CrewFactory:
    @staticmethod
    def create_crew_config(crew_type: str, topic: str) -> dict:
        configs = {
            "article": {
                "agents": [
                    {
                        "role": "Content Planner",
                        "goal": f"Plan engaging and factually accurate content on {topic}",
                        "backstory": "Expert content planner with focus on creating engaging outlines",
                        "tasks": [
                            """Create a detailed content plan for an article by:
                            1. Prioritizing the latest trends and key players
                            2. Identifying the target audience
                            3. Developing a detailed content outline
                            4. Including SEO keywords and sources"""
                        ]
                    },
                    {
                        "role": "Content Writer",
                        "goal": f"Write insightful piece about {topic}",
                        "backstory": "Expert content writer with focus on engaging articles",
                        "tasks": [
                            """1. Use the content plan to craft a compelling blog post
                            2. Incorporate SEO keywords naturally
                            3. Create proper structure with introduction, body, and conclusion"""
                        ]
                    },
                    {
                        "role": "Editor",
                        "goal": "Polish and refine the content",
                        "backstory": "Expert editor with eye for detail and clarity",
                        "tasks": [
                            """1. Review for clarity and coherence
                            2. Correct any errors
                            3. Ensure consistent tone and style"""
                        ]
                    }
                ]
            },
            "support": {
                "agents": [
                    {
                        "role": "Senior Support Representative",
                        "goal": "Be the most helpful support representative",
                        "backstory": "Expert at analyzing questions and providing support",
                        "tasks": [
                            f"""Analyze this inquiry thoroughly: {topic}
                            Provide detailed support response."""
                        ]
                    },
                    {
                        "role": "Support Quality Assurance",
                        "goal": "Ensure highest quality of support responses",
                        "backstory": "Expert at reviewing and improving support responses",
                        "tasks": [
                            """Review and improve the support response to ensure it's:
                            1. Comprehensive and helpful
                            2. Properly formatted with clear structure"""
                        ]
                    }
                ]
            }
        }
        return configs.get(crew_type, configs["article"])

class CrewManager:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.message_queue = MessageQueue()
        self.agents = []
        self.current_agent = None
        self.scrape_tool = None

    def initialize_agents(self, crew_type: str, topic: str, website_url: str = None):
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        os.environ["OPENAI_API_KEY"] = self.api_key
        if website_url:
            self.scrape_tool = ScrapeWebsiteTool(website_url=website_url)

        # Get crew configuration
        config = CrewFactory.create_crew_config(crew_type, topic)
        
        # Initialize agents from configuration
        self.agents = []
        for agent_config in config["agents"]:
            agent = Agent(
                role=agent_config["role"],
                goal=agent_config["goal"],
                backstory=agent_config["backstory"],
                allow_delegation=False,
                verbose=True
            )
            self.agents.append((agent, agent_config["tasks"]))

    def create_tasks(self, topic: str) -> List[Task]:
        tasks = []
        for agent, task_descriptions in self.agents:
            for task_desc in task_descriptions:
                task = Task(
                    description=task_desc,
                    expected_output="Detailed and well-formatted response",
                    agent=agent,
                    tools=[self.scrape_tool] if self.scrape_tool else []
                )
                tasks.append(task)
        return tasks

    async def process_support(self, inquiry: str, website_url: str, crew_type: str) -> Generator[List[Dict], None, None]:
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
            if crew_type == "support":
                if current_agent == "Senior Support Representative":
                    self.current_agent = "Support Quality Assurance Specialist"
                    add_agent_messages(
                        "Support Quality Assurance Specialist",
                        "Review and improve the support response"
                    )
            elif crew_type == "article":
                if current_agent == "Content Planner":
                    self.current_agent = "Content Writer"
                    add_agent_messages(
                        "Content Writer",
                        "Write the article based on the content plan"
                    )
                elif current_agent == "Content Writer":
                    self.current_agent = "Editor"
                    add_agent_messages(
                        "Editor",
                        "Review and polish the article"
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
            self.initialize_agents(crew_type, inquiry, website_url)
            # Set initial agent based on crew type
            self.current_agent = "Senior Support Representative" if crew_type == "support" else "Content Planner"

            yield [{
                "role": "assistant",
                "content": "Starting to process your inquiry...",
                "metadata": {"title": "🚀 Process Started"}
            }]

            # Set initial task message based on crew type
            if crew_type == "support":
                add_agent_messages(
                    "Senior Support Representative",
                    "Analyze inquiry and provide comprehensive support"
                )
            else:
                add_agent_messages(
                    "Content Planner",
                    "Create a detailed content plan for the article"
                )

            crew = Crew(
                agents=[agent for agent, _ in self.agents],
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

def registry(name: str, token: str | None = None, crew_type: str = "support", **kwargs):
    has_api_key = bool(token or os.environ.get("OPENAI_API_KEY"))
    crew_manager = None

    with gr.Blocks(theme=gr.themes.Soft()) as demo:
        title = "📝 AI Article Writing Crew" if crew_type == "article" else "🤖 CrewAI Assistant"
        gr.Markdown(f"# {title}")
        
        api_key = gr.Textbox(
            label="OpenAI API Key",
            type="password",
            placeholder="Type your OpenAI API key and press Enter...",
            interactive=True,
            visible=not has_api_key
        )

        chatbot = gr.Chatbot(
            label="Writing Process" if crew_type == "article" else "Process",
            height=700 if crew_type == "article" else 600,
            show_label=True,
            visible=has_api_key,
            avatar_images=(None, "https://avatars.githubusercontent.com/u/170677839?v=4"),
            render_markdown=True,
            type="messages"
        )
        
        with gr.Row(equal_height=True):
            topic = gr.Textbox(
                label="Article Topic" if crew_type == "article" else "Topic/Question",
                placeholder="Enter topic..." if crew_type == "article" else "Enter your question...",
                scale=4,
                visible=has_api_key
            )
            website_url = gr.Textbox(
                label="Documentation URL",
                placeholder="Enter documentation URL to search...",
                scale=4,
                visible=(has_api_key) and crew_type == "support"
            )
            btn = gr.Button(
                "Write Article" if crew_type == "article" else "Start", 
                variant="primary", 
                scale=1, 
                visible=has_api_key
            )

        async def process_input(topic, website_url, history, api_key):
            nonlocal crew_manager
            effective_api_key = token or api_key or os.environ.get("OPENAI_API_KEY")
            
            if not effective_api_key:
                yield [
                    {"role": "user", "content": f"Question: {topic}\nDocumentation: {website_url}"},
                    {"role": "assistant", "content": "Please provide an OpenAI API key."}
                ]
                return  # Early return without value

            if crew_manager is None:
                crew_manager = CrewManager(api_key=effective_api_key)

            messages = [{"role": "user", "content": f"Question: {topic}\nDocumentation: {website_url}"}]
            yield messages

            try:
                async for new_messages in crew_manager.process_support(topic, website_url, crew_type):
                    for msg in new_messages:
                        if "metadata" in msg:
                            messages.append({
                                "role": msg["role"],
                                "content": msg["content"],
                                "metadata": {"title": msg["metadata"]["title"]}
                            })
                        else:
                            messages.append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })
                    yield messages
            except Exception as e:
                messages.append({
                    "role": "assistant", 
                    "content": f"An error occurred: {str(e)}",
                    "metadata": {"title": "❌ Error"}
                })
                yield messages

        def show_interface():
            return {
                api_key: gr.Textbox(visible=False),
                chatbot: gr.Chatbot(visible=True),
                topic: gr.Textbox(visible=True),
                website_url: gr.Textbox(visible=True),
                btn: gr.Button(visible=True)
            }

        if not has_api_key:
            api_key.submit(show_interface, None, [api_key, chatbot, topic, website_url, btn])
        
        btn.click(process_input, [topic, website_url, chatbot, api_key], [chatbot])
        topic.submit(process_input, [topic, website_url, chatbot, api_key], [chatbot])

    return demo