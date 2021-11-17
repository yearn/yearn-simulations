import functools
from types import FunctionType
from typing import List, Dict


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ScheduledScripts(metaclass=Singleton):
    def __init__(self) -> None:
        self._scheduled_scripts = []

    def add(self, item: "ScheduledScript"):
        self._scheduled_scripts.append(item)

    @property
    def scheduled_scripts(self):
        return self._scheduled_scripts


class ScheduledScript:
    def __init__(
        self,
        script: FunctionType,
        telegram_chat_id: str,
        environment: Dict[str, str] = None,
        secrets: List[str] = None,
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
        self.environment = environment
        self.secrets = secrets

        if environment is None:
            self.environment = {}

        if secrets is None:
            self.secrets = []

    def __str__(self):

        return f"<ScheduledScript {self.script.__module__} {self.telegram_chat_id} day={self.day} hour={self.hour} minute={self.minute} month={self.month} week_day={self.week_day} year={self.year}>"


def schedule_script(
    telegram_chat_id: str,
    environment: Dict[str, str] = None,
    secrets: List[str] = None,
    day: str = None,
    hour: str = None,
    minute: str = None,
    month: str = None,
    week_day: str = None,
    year: str = None,
):
    def script(func):
        global schedule_scripts_storage

        @functools.wraps(func)
        def wrapped_script(*args, **kwargs):
            return func(*args, **kwargs)

        schedule_scripts_storage.add(
            ScheduledScript(
                wrapped_script,
                telegram_chat_id,
                environment=environment,
                secrets=secrets,
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


schedule_scripts_storage = ScheduledScripts()
