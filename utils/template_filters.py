from datetime import datetime

def format_datetime(value):
    """格式化日期时间"""
    if not value:
        return ""
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        else:
            dt = value
        return dt.strftime("%d %B %Y %H:%M")
    except Exception:
        return value
