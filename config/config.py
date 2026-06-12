import yaml
from dataclasses import dataclass
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent

DEFAULT_CONFIG = (
    CONFIG_DIR /
    "config.yaml"
)

@dataclass
class ProjectConfig:
    linux_root: str

@dataclass
class CacheConfig:
    enabled: bool
    semantic_bundle_path: str

@dataclass
class OllamaConfig:
    endpoint: str
    model: str

@dataclass
class LLMConfig:
    enabled: bool
    provider: str
    ollama: OllamaConfig

@dataclass
class ExportsConfig:
    mermaid_dir: str
    graph_dir: str
    report_dir: str

@dataclass
class RuntimeConfig:
    debug_traversal: bool
    max_depth_default: int

@dataclass
class ProfilesConfig:
    auto_detect: bool

@dataclass
class AppConfig:
    project: ProjectConfig
    cache: CacheConfig
    llm: LLMConfig
    exports: ExportsConfig
    runtime: RuntimeConfig
    profiles: ProfilesConfig

def load_config(config_path=DEFAULT_CONFIG) -> AppConfig:
    """Loads the YAML file and maps it into the AppConfig dataclass."""
    config_path = Path(config_path)
    #print(f"config_path ({config_path})")

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    ollama_raw = (
        raw.get("llm", {})
        .get("ollama", {})
    )
    return AppConfig(
        project=ProjectConfig(**raw.get("project", {})),
        cache=CacheConfig(**raw.get("cache", {})),
        llm=LLMConfig(
            enabled=raw.get("llm", {}).get("enabled", True),
            provider=raw.get("llm", {}).get("provider", "ollama"),

            ollama=OllamaConfig(
                endpoint=ollama_raw.get(
                    "endpoint",
                    "http://127.0.0.1:11434/api/generate" # fallback
                ),
                model=ollama_raw.get(
                    "model",
                    "qwen2.5-coder:7b"
                )
            ),
        ),
        exports=ExportsConfig(**raw.get("exports", {})),
        runtime=RuntimeConfig(**raw.get("runtime", {})),
        profiles=ProfilesConfig(**raw.get("profiles", {}))
    )

# Instantiate a global config object that any file can import
app_config = load_config()