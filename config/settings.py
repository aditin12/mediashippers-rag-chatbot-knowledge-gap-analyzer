from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Gemini
    GEMINI_API_KEY:        str = ""
    # PostgreSQL
    DB_HOST:               str = "localhost"
    DB_PORT:               int = 5432
    DB_NAME:               str = "mediashippers"
    DB_USER:               str = "postgres"
    DB_PASSWORD:           str = "postgres123"
    # AWS (optional - works without these)
    AWS_ACCESS_KEY_ID:     str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION:            str = "ap-south-1"
    S3_BUCKET_NAME:        str = "mediashippers-support-doc"
    # AWS OpenSearch Serverless (optional - filled by setup_opensearch.py)
    OPENSEARCH_HOST:       str = ""
    OPENSEARCH_INDEX:      str = "mediashippers-docs"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
