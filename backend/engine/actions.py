"""Shared Action Engine for Custos OS."""

def execute_action(action):
    """
    Simulates external API calls based on action intent.
    Returns the action result string.
    """
    if action == "RETRY_PAYMENT":
        return "SIMULATED_SUCCESS (Retry logged)"
    elif action == "SEND_REMINDER":
        return "SIMULATED_SUCCESS (Email reminder logged)"
    elif action == "FLAG_FOR_HUMAN_REVIEW":
        return "NO_ACTION_TAKEN (Routed to human)"
    else:
        return "SUCCESS"
