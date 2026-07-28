from typing import Any, Dict, Tuple

def model_a(token: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Model A — processes token and signals handoff to Model B."""
    token["a_done"] = True
    output = {"processed_by": "A", "a_result": f"A processed: {token.get('input', '')}"}
    handoff = True   # True = pass to next model
    return output, handoff

def model_b(token: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Model B — final processing, no further handoff."""
    token["b_done"] = True
    output = {"processed_by": "B", "b_result": f"B processed: {token.get('input', '')}"}
    handoff = False  # False = pipeline complete
    return output, handoff
