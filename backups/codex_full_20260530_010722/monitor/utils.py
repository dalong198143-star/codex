from datetime import datetime, timezone, timedelta

_TZ = timezone(timedelta(hours=8))

def now():
    """Return Asia/Shanghai current datetime"""
    return datetime.now(_TZ)

def now_str():
    """Return Asia/Shanghai time string"""
    return now().strftime('%Y-%m-%d %H:%M')
