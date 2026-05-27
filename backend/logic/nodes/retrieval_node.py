from data_layer.vector_db.query import query_legal_context

def retrieval_node(state):

    if state.get("search_queries"):
        query = state["search_queries"][-1]
    else:
        query = state["complaint_text"]

    docs = query_legal_context(query)

    state["retrieved_docs"] = docs

    return state