from typing import TypedDict, List, Dict

class ComplaintState(TypedDict):
    complaint_text: str
    category: str
    severity_score: float
    retrieved_docs: List[str]
    risk_level: str
    recommended_action: str
    relevant_laws: List[str]
    escalation_required: bool
    structured_output: Dict
    retrieval_attempts: int
    search_queries: List[str]
    validation_decision: str