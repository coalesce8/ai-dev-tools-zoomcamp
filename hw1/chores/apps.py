from django.apps import AppConfig


class ChoresConfig(AppConfig):
    name = 'chores'

    def ready(self):
        # Validate the config file at startup; fail loudly on bad data.
        from .config import get_config

        get_config()
