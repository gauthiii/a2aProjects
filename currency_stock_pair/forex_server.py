# forex_server.py
import click
import httpx
from dotenv import load_dotenv

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from currency_agent import CurrencyAgent  # your inner agent
from forex_agent_executor import ForexAgentExecutor

load_dotenv()


def get_agent_card(host: str, port: int) -> AgentCard:
    """AgentCard for the Forex (currency) agent."""
    capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
    skill = AgentSkill(
        id="convert_currency",
        name="Currency Conversion Skill",
        description="Converts amounts between currencies using CurrencyMCP.",
        tags=["currency", "forex", "exchange rates"],
        examples=["How much is 100 USD in EUR?"],
    )
    return AgentCard(
        name="Forex Agent",
        description="Agent that converts between currencies using MCP tools.",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=capabilities,
        skills=[skill],
    )


@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=10001)
def main(host: str, port: int) -> None:
    client = httpx.AsyncClient()
    request_handler = DefaultRequestHandler(
        agent_executor=ForexAgentExecutor(),
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
