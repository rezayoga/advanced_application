import os


class BaseConfig:
    pass


class DevelopmentConfig(BaseConfig):
    DATABASE_URL: str = os.environ.get("DATABASE_URL",
                                       "postgresql+asyncpg://reza:rezareza1985@rezayogaswara.com:5433/db_advanced_application")

    DATABASE_CONNECT_DICT: dict = {'server_settings': {'jit': 'off'}}


class ProductionConfig(BaseConfig):
    pass


class TestingConfig(BaseConfig):
    pass


def get_settings():
    config_cls_dict = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "testing": TestingConfig
    }

    config_name = os.environ.get("FASTAPI_CONFIG", "development")
    config_cls = config_cls_dict[config_name]
    return config_cls()


settings = get_settings()
