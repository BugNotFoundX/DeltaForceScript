from pathlib import Path

from deltaforcescript.paths import get_app_paths


def test_get_app_paths_finds_project_root_from_nested_cwd(monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(project_root / "src" / "deltaforcescript")

    paths = get_app_paths()

    assert paths.project_root == project_root
    assert paths.regions_file == project_root / "regions_2k.json"
    assert paths.detection_model_dir == project_root / "models" / "PP-OCRv5_server_det_infer"
    assert paths.recognition_model_dir == project_root / "models" / "PP-OCRv5_server_rec_infer"
