# application/config.py
import json


class Config:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, config_file="config.json"):
        if not hasattr(self, "_initialized"):  # Prevent re-initialization
            with open(config_file, "r") as f:
                self.data = json.load(f)
            self._initialized = True

    def get(self, *keys, default=None):
        """
        Access nested configuration values.
        Example: config.get('entities', 'human', 'max_age')
        """
        value = self.data
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default


# Create a single, globally accessible instance
config = Config()
