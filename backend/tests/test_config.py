import os
import unittest
from pathlib import Path
from unittest import mock

from review_advisory_api import config as config_module


class ConfigDiscoveryTests(unittest.TestCase):
    def test_discovers_runs_index_from_repo_root(self) -> None:
        repo = Path(__file__).resolve().parents[2]
        index = repo / "data" / "history" / "runs_index.json"
        self.assertTrue(index.exists(), "fixture runs_index.json required for tests")

        with mock.patch.dict(os.environ, {}, clear=False):
            if "REVIEW_ADVISORY_REPO_ROOT" in os.environ:
                del os.environ["REVIEW_ADVISORY_REPO_ROOT"]
            if "REVIEW_ADVISORY_HISTORY_DIR" in os.environ:
                del os.environ["REVIEW_ADVISORY_HISTORY_DIR"]
            reloaded = config_module
            # Re-import would be ideal; instead call discovery helpers via module reload
            import importlib

            importlib.reload(config_module)
            self.assertTrue((config_module.history_dir() / "runs_index.json").exists())
            self.assertGreaterEqual(
                len((config_module.history_dir() / "runs_index.json").read_text()),
                10,
            )

    def test_misconfigured_repo_root_env_still_finds_index(self) -> None:
        repo = Path(__file__).resolve().parents[2]
        wrong_backend_root = str(repo / "backend")
        with mock.patch.dict(
            os.environ,
            {
                "REVIEW_ADVISORY_REPO_ROOT": wrong_backend_root,
                "REVIEW_ADVISORY_HISTORY_DIR": "",
            },
            clear=False,
        ):
            import importlib

            importlib.reload(config_module)
            index_path = config_module.history_dir() / "runs_index.json"
            self.assertTrue(index_path.exists(), f"expected index at {index_path}")


if __name__ == "__main__":
    unittest.main()
