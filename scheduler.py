import functools
from types import FunctionType

SCHEDULED_SCRIPTS = []


class ScheduledScript:
    def __init__(
        self,
        script: FunctionType,
        telegram_chat_id: str,
        day: str = None,
        hour: str = None,
        minute: str = None,
        month: str = None,
        week_day: str = None,
        year: str = None,
    ):
        self.script = script
        self.day = day
        self.hour = hour
        self.minute = minute
        self.month = month
        self.week_day = week_day
        self.year = year
        self.telegram_chat_id = telegram_chat_id

    def __str__(self):

        return f"<ScheduledScript {self.script.__module__} {self.telegram_chat_id} day={self.day} hour={self.hour} minute={self.minute} month={self.month} week_day={self.week_day} year={self.year}>"


def schedule_script(
    telegram_chat_id: str = None,
    day: str = None,
    hour: str = None,
    minute: str = None,
    month: str = None,
    week_day: str = None,
    year: str = None,
):
    def script(func):
        @functools.wraps(func)
        def wrapped_script(*args, **kwargs):
            return func(*args, **kwargs)
        print("wrapping brownie script....")
        SCHEDULED_SCRIPTS.append(
            ScheduledScript(
                wrapped_script,
                telegram_chat_id,
                day=day,
                hour=hour,
                minute=minute,
                month=month,
                week_day=week_day,
                year=year,
            )
        )
        return wrapped_script

    return script
