from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    tushare_token: str = Field(..., env="TUSHARE_TOKEN")
    smtp_host: str = Field(..., env="SMTP_HOST")
    smtp_user: str = Field(..., env="SMTP_USER")
    smtp_pass: str = Field(..., env="SMTP_PASS")
    smtp_to: str = Field(..., env="SMTP_TO")
    db_path: str = Field("data/portfolio_radar.db", env="DB_PATH")
    weight_tech: float = Field(0.40, env="WEIGHT_TECH")
    weight_event: float = Field(0.35, env="WEIGHT_EVENT")
    weight_senti: float = Field(0.25, env="WEIGHT_SENTI")
    advice_buy_threshold: float = Field(0.65, env="ADVICE_BUY_THRESHOLD")
    advice_sell_threshold: float = Field(0.35, env="ADVICE_SELL_THRESHOLD")
    advice_watch_upper: float = Field(0.55, env="ADVICE_WATCH_UPPER")
    advice_watch_lower: float = Field(0.45, env="ADVICE_WATCH_LOWER")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
