"""Deterministic output-depth selection; not a model thinking-mode guarantee."""


def resolve_depth(requested: str, prompt: str) -> str:
    if requested in ("low", "medium", "high"):
        return requested
    if requested != "auto":
        raise ValueError("Response depth must be auto, low, medium or high")
    lowered = prompt.lower()
    complex_terms = ("analyze", "compare", "evaluate", "strategy", "multi-step", "security review", "thorough")
    if len(prompt) >= 400 or any(term in lowered for term in complex_terms):
        return "high"
    if len(prompt) <= 100 and not any(term in lowered for term in ("draft", "explain", "outline", "plan")):
        return "low"
    return "medium"
