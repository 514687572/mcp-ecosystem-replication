"""Configuration loading and project path resolution.

Paths are always resolved relative to the project root, so scripts behave the
same no matter which working directory they are launched from.
"""
import os

import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))

DEFAULT_CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "config.yaml")

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
INTERIM_DIR = os.path.join(DATA_DIR, "interim")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
TABLES_DIR = os.path.join(RESULTS_DIR, "tables")
FIGURES_DIR = os.path.join(RESULTS_DIR, "figures")

ALL_DIRS = [
    RAW_DIR,
    INTERIM_DIR,
    PROCESSED_DIR,
    CACHE_DIR,
    TABLES_DIR,
    FIGURES_DIR,
]


def load_dotenv(path=None):
    """Load KEY=VALUE pairs from a gitignored .env file into os.environ.

    Real environment variables always win, so a shell-level export overrides
    the file. Used for GITHUB_TOKEN, which must never be committed.
    """
    env_path = path or os.path.join(PROJECT_ROOT, ".env")
    if not os.path.isfile(env_path):
        return False
    with open(env_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    return True


def ensure_dirs():
    """Create every output directory the pipeline writes to."""
    for path in ALL_DIRS:
        if not os.path.isdir(path):
            os.makedirs(path)


def load(path=None):
    """Load the YAML config, falling back to the packaged default."""
    load_dotenv()
    cfg_path = path or DEFAULT_CONFIG_PATH
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    ensure_dirs()
    return cfg


def out(name, directory=PROCESSED_DIR):
    """Absolute path for a pipeline output file."""
    ensure_dirs()
    return os.path.join(directory, name)
