"""Shared Evidence Engine for Custos OS."""

def build_evidence(event, raw):
    """
    Builds the structured evidence payload for an event.
    """
    evidence = []
    
    # Gateway Data
    evidence.append({
        "source": "Razorpay Gateway",
        "icon": "gateway",
        "strength": "Strong" if raw.get("error_reason") or raw.get("error") else "Partial",
        "detail": raw.get("error_description") or raw.get("error") or "No error recorded",
        "fields": {
            "Error Code": raw.get("error_code", "N/A"),
            "Error Reason": raw.get("error_reason") or raw.get("error", "N/A"),
            "Error Step": raw.get("error_step", "N/A"),
            "Error Source": raw.get("error_source", "N/A"),
        }
    })
    
    # CRM / Customer Data
    evidence.append({
        "source": "CRM / Internal DB",
        "icon": "crm",
        "strength": "Strong" if event["customer_ref"] else "Weak",
        "detail": "Customer payment profile extracted",
        "fields": {
            "Customer Ref": event["customer_ref"] or "Unknown",
            "Attempts": raw.get("attempts", 1),
            "Method": raw.get("method", "N/A"),
        }
    })
    
    # Network Data
    if "card" in raw.get("method", "").lower() and "card" in raw:
        card = raw["card"]
        evidence.append({
            "source": f"{card.get('network', 'Card')} Network",
            "icon": "network",
            "strength": "Strong",
            "detail": f"{card.get('type', '').title()} {card.get('sub_type', '')}",
            "fields": {
                "Network": card.get("network", "N/A"),
                "Last 4": card.get("last4", "N/A"),
                "Intl": "Yes" if card.get("international") else "No",
                "Name": card.get("name", "N/A")
            }
        })
        
    return evidence
