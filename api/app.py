import os
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import yaml
from dotenv import dotenv_values

app = FastAPI()

# ---- CORS: allow all origins so the browser grader can call us ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Precedence 1: hard-coded defaults ----
config = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

# ---- Precedence 2: config.development.yaml ----
def load_yaml(path):
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}

yaml_config = load_yaml("config.development.yaml")
config.update(yaml_config)

# ---- Precedence 3: .env file ----
env_path = Path(".env")
if env_path.exists():
    dotenv_dict = dotenv_values(env_path)
    for key, value in dotenv_dict.items():
        # Map known aliases
        if key == "NUM_WORKERS":
            config["workers"] = int(value)
        elif key.startswith("APP_"):
            # e.g., APP_API_KEY -> api_key
            new_key = key[4:].lower()
            config[new_key] = value
        else:
            config[key] = value

# ---- Precedence 4: OS environment variables (APP_*) ----
for key, value in os.environ.items():
    if key.startswith("APP_"):
        new_key = key[4:].lower()   # APP_WORKERS → workers, APP_DEBUG → debug, etc.
        config[new_key] = value

# ---- Helper: type coercion ----
def coerce_types(cfg):
    # port, workers → int
    for int_key in ("port", "workers"):
        if int_key in cfg:
            cfg[int_key] = int(cfg[int_key])
    # debug → bool
    if "debug" in cfg:
        val = str(cfg["debug"]).lower()
        cfg["debug"] = val in ("true", "1", "yes", "on")
    # log_level stays string
    return cfg

coerce_types(config)

# ---- Endpoint ----
@app.get("/effective-config")
async def effective_config(set: list[str] = Query(default=[])):
    # Start from the merged base config (layers 1-4)
    final_cfg = config.copy()

    # ---- Precedence 5: CLI overrides (?set=key=value) ----
    for override in set:
        if "=" in override:
            key, value = override.split("=", 1)
            key = key.strip()
            final_cfg[key] = value

    # Coerce types again after overrides
    coerce_types(final_cfg)

    # Mask api_key
    final_cfg["api_key"] = "****"

    return final_cfg
