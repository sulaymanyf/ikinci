from datetime import datetime
from dateutil import parser
from dateutil.tz import tzlocal

def format_datetime(value):
    """格式化日期时间"""
    if not value:
        return ""
    
    if isinstance(value, str):
        dt = parser.parse(value)
    else:
        dt = value
    
    now = datetime.now(tzlocal())
    diff = now - dt
    
    if diff.days == 0:
        if diff.seconds < 60:
            return "şimdi"
        elif diff.seconds < 3600:
            minutes = diff.seconds // 60
            return f"{minutes} dakika önce"
        else:
            hours = diff.seconds // 3600
            return f"{hours} saat önce"
    elif diff.days == 1:
        return "dün"
    elif diff.days < 7:
        return f"{diff.days} gün önce"
    else:
        return dt.strftime("%d.%m.%Y %H:%M")
