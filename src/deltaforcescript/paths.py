# -*- coding: utf-8 -*-
"""Project path discovery and resource locations."""

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT_ENV = "DELTAFORCESCRIPT_ROOT"
REGIONS_FILE = "regions_2k.json"


@dataclass(frozen=True)
class AppPaths:
    """Resolved filesystem paths used by the runtime."""

    project_root: Path
    regions_file: Path
    detection_model_dir: Path
    recognition_model_dir: Path


def _candidate_roots() -> list[Path]:
    candidates: list[Path] = []

    env_root = os.environ.get(PROJECT_ROOT_ENV)
    if env_root:
        candidates.append(Path(env_root))

    cwd = Path.cwd()
    candidates.extend([cwd, *cwd.parents])

    package_file = Path(__file__).resolve()
    candidates.extend(package_file.parents)
    return candidates


def find_project_root() -> Path:
    """Find the repo/resource root without relying on the current directory."""
    for candidate in _candidate_roots():
        if (candidate / REGIONS_FILE).is_file():
            return candidate

    searched = "\n".join(str(path) for path in _candidate_roots())
    raise FileNotFoundError(
        f"找不到 {REGIONS_FILE}。请在项目根目录运行，或设置 {PROJECT_ROOT_ENV}。\n"
        f"已搜索:\n{searched}"
    )


def get_app_paths(project_root: str | Path | None = None) -> AppPaths:
    """Resolve all runtime resource paths."""
    root = Path(project_root).resolve() if project_root is not None else find_project_root()
    models_dir = root / "models"
    return AppPaths(
        project_root=root,
        regions_file=root / REGIONS_FILE,
        detection_model_dir=models_dir / "PP-OCRv5_server_det_infer",
        recognition_model_dir=models_dir / "PP-OCRv5_server_rec_infer",
    )
