from utils.tool_logger import logged_tool

@logged_tool
def retrieve_memory(query: str) -> str:
    """Search episodic memory for past conversations, decisions, and context.
    Call this when the user references a previous session, asks 'do you remember',
    'what did we discuss', 'last time', 'before', or needs historical context.

    Args:
        query: Natural language description of what to recall from past conversations.

    Returns:
        Relevant past conversation excerpts, or a message if nothing found.
    """
    from agent.context import get_user_id
    from memory.manager import retrieve_episodes
    user_id = get_user_id()
    if not user_id:
        return "No memory context available."
    result = retrieve_episodes(user_id, query, threshold=0.45)
    return result or "No relevant past conversations found for this query."

@logged_tool
def retrieve_fact(query: str) -> str:
    """Look up a specific stored fact about the user: email address, name,
    preferences, timezone, programming languages, tools used, or any personal
    information the user has stated in past sessions.
    Use this for precise lookups, not narrative context.

    Args:
        query: The fact to look up e.g. 'email address', 'timezone', 'preferred language'.

    Returns:
        Matching stored facts or a message if nothing found.
    """
    from agent.context import get_user_id
    from memory.fact_store import search_facts, init_db
    init_db()
    user_id = get_user_id()
    if not user_id:
        return "No memory context available."
    results = search_facts(str(user_id), query)
    if not results:
        return f"No stored facts found for: '{query}'"
    out = f"📋 Stored facts for '{query}':\n\n"
    for r in results:
        out += f"• {r['fact']}\n"
    return out

@logged_tool
def list_all_facts() -> str:
    """List all facts stored about the user: emails, preferences, names, settings.
    Use this when you need a full picture of what's known about the user.

    Returns:
        All stored facts grouped by category.
    """
    from agent.context import get_user_id
    from memory.fact_store import get_all_facts, init_db
    init_db()
    user_id = get_user_id()
    if not user_id:
        return "No memory context available."
    facts = get_all_facts(str(user_id))
    if not facts:
        return "No facts stored yet about this user."
    out = "📚 All stored facts:\n\n"
    current_cat = None
    for f in facts:
        if f["category"] != current_cat:
            current_cat = f["category"]
            out += f"\n**{current_cat.upper()}**\n"
        out += f"• {f['full_fact']}\n"
    return out
