from app.mcp import context as ctx
from app.mcp import agent


def send_context(domain: str, user_id: str, payload: dict) -> str:
    from app.mcp import context as ctx
    ctx.prune_expired()
    return ctx.create_context(domain, user_id, payload)["context_id"]


def request_action(context_id: str) -> dict:
    context = ctx.get_context(context_id)
    proposed = agent.propose(context)
    model = agent.get_model_for(context)
    return ctx.update_context(
        context_id,
        proposed=proposed,
        status="staged",
        iteration_count=context["iteration_count"] + 1,
        agent_model=model,
    )


def receive_result(context_id: str) -> dict:
    return ctx.get_context(context_id)


def confirm(context_id: str) -> dict:
    return ctx.confirm(context_id)


def rollback(context_id: str) -> dict:
    return ctx.rollback(context_id)


def find_pending_for_user(user_id: str) -> str | None:
    from app.mcp import context as ctx
    return ctx.find_pending_for_user(user_id)
