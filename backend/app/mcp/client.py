from app.mcp import context as ctx
from app.mcp import agent


def send_context(domain: str, user_id: str, payload: dict) -> str:
    context = ctx.create_context(domain, user_id, payload)
    return context["context_id"]


def request_action(context_id: str) -> dict:
    context = ctx.get_context(context_id)
    proposed = agent.propose(context)
    return ctx.update_context(
        context_id,
        proposed=proposed,
        status="staged",
        iteration_count=context["iteration_count"] + 1,
    )


def receive_result(context_id: str) -> dict:
    return ctx.get_context(context_id)


def confirm(context_id: str) -> dict:
    return ctx.confirm(context_id)


def rollback(context_id: str) -> dict:
    return ctx.rollback(context_id)
