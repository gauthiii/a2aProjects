# stock_server.py
import click
import httpx
from dotenv import load_dotenv

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from stock_data_agent import StockAgent
from stock_agent_executor import StockAgentExecutor

load_dotenv()


def get_agent_card(host: str, port: int) -> AgentCard:
    capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
    skill = AgentSkill(
        id="get_stock_price",
        name="Stock Market Data Skill",
        description="Fetches stock prices and related data from Yahoo Finance MCP.",
        tags=["stocks", "market", "yahoo finance"],
        examples=["What is GOOG stock price today in USD?"],
    )
    return AgentCard(
        name="Market Agent",
        description="Agent that analyzes stock data using StockMCP.",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=StockAgent.SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=StockAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=capabilities,
        skills=[skill],
    )


@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=10002)
def main(host: str, port: int) -> None:
    client = httpx.AsyncClient()
    request_handler = DefaultRequestHandler(
        agent_executor=StockAgentExecutor(),
        task_store=InMemoryTaskStore(),
        push_notifier=InMemoryPushNotifier(client),
    )
    server = A2AStarletteApplication(
        agent_card=get_agent_card(host, port), http_handler=request_handler
    )

    import uvicorn

    uvicorn.run(server.build(), host=host, port=port)


if __name__ == "__main__":
    main()
