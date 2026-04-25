from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    GITHUB_APP_ID: str = ""
    GITHUB_PRIVATE_KEY_PATH: str = "./github-app.pem"
    GITHUB_WEBHOOK_SECRET: str = "dev_secret_change_me"
    # Personal Access Token — when set, GitHub client uses Bearer PAT auth
    # instead of GitHub-App-installation-token. Lets us demo against any repo
    # without registering a GitHub App.
    GITHUB_PAT: str = ""

    # Defaults match agentbench-live/vllm_setup scripts (port 5000, served-name "nemotron").
    # Override with Brev IP via .env when the GPU instance is up.
    VLLM_BASE_URL: str = "http://localhost:5000/v1"
    VLLM_MODEL: str = "nemotron"
    VLLM_API_KEY: str = "not-needed"   # set to NVIDIA NGC key when hitting integrate.api.nvidia.com
    ENABLE_NVEXT_HEADERS: bool = True
    MOCK_MODE: bool = True
    # Optional fine-grained overrides — if unset, both default to MOCK_MODE.
    GITHUB_MOCK_MODE: bool | None = None
    LLM_MOCK_MODE: bool | None = None
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 1024
    LLM_TIMEOUT_SECONDS: float = 60.0

    DATABASE_URL: str = "sqlite:///./prdemo.db"
    PORT: int = 8080


settings = Settings()
