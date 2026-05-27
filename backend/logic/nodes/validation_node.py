import re
from backend.logic.llm_wrapper import generate_response


def validation_node(state):

    docs = state.get("retrieved_docs", [])
    category = state.get("category", "Other")

    prompt = f"""You are a legal retrieval quality assessor.

Complaint Category: {category}

Retrieved Legal Context:
{chr(10).join(f'- {d}' for d in docs) if docs else '(none)'}

Evaluate whether the retrieved legal context is sufficient to analyze this complaint category.

- If sufficient: respond with exactly "Context Good"
- If insufficient: respond on one line as "Context Bad: <improved search query>"
  where <improved search query> is a specific legal search query targeting
  relevant statutes, sections, or case law for this complaint.

Do NOT include any other text."""

    response = generate_response(prompt)

    if response.strip().startswith("Context Good"):
        state["validation_decision"] = "Context Good"
    else:
        match = re.match(r"Context Bad:\s*(.+)", response, re.DOTALL)
        new_query = match.group(1).strip() if match else f"Legal statutes related to {category} corruption"

        state.setdefault("search_queries", []).append(new_query)
        state["retrieval_attempts"] = state.get("retrieval_attempts", 0) + 1
        state["validation_decision"] = "Context Bad"

    return state
