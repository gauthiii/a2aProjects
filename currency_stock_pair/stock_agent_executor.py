# stock_agent_executor.py
import logging
from stock_data_agent import StockAgent  # wrap stock_data_agent logic into this

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils import new_agent_text_message, new_task, new_text_artifact

logger = logging.getLogger(__name__)


class StockAgentExecutor(AgentExecutor):
    """A2A wrapper around your Stock MCP + LLM agent."""

    def __init__(self):
        self.agent = StockAgent()  # uses StockMCP (Yahoo) under the hood

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        query = context.get_user_input()
        task = context.current_task

        if not context.message:
            raise Exception("No message provided")

        if not task:
            task = new_task(context.message)
            event_queue.enqueue_event(task)

        async for event in self.agent.stream(query, task.contextId):
            if event["is_task_complete"]:
                event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        append=False,
                        contextId=task.contextId,
                        taskId=task.id,
                        lastChunk=True,
                        artifact=new_text_artifact(
                            name="current_result",
                            description="Result of stock query.",
                            text=event["content"],
                        ),
                    )
                )
                event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        status=TaskStatus(state=TaskState.completed),
                        final=True,
                        contextId=task.contextId,
                        taskId=task.id,
                    )
                )
            elif event["require_user_input"]:
                event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        status=TaskStatus(
                            state=TaskState.input_required,
                            message=new_agent_text_message(
                                event["content"], task.contextId, task.id
                            ),
                        ),
                        final=True,
                        contextId=task.contextId,
                        taskId=task.id,
                    )
                )
            else:
                event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        status=TaskStatus(
                            state=TaskState.working,
                            message=new_agent_text_message(
                                event["content"], task.contextId, task.id
                            ),
                        ),
                        final=False,
                        contextId=task.contextId,
                        taskId=task.id,
                    )
                )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise Exception("cancel not supported")
