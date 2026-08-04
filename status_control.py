def is_run_active(status):
    if status is None:
        return False
    status_text = str(status).strip()
    return "Start" in status_text or "green" in status_text.lower()
