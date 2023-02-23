import os


class BaseConfig:
    pass


class DevelopmentConfig(BaseConfig):
    DATABASE_URL: str = os.environ.get("DATABASE_URL",
                                       f"postgresql+asyncpg://reza:reza@rezayogaswara.com:5432/db_advanced_application")

    DATABASE_CONNECT_DICT: dict = {}


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
