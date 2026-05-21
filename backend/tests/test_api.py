import unittest

from fastapi.testclient import TestClient

from review_advisory_api.main import app


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_list_runs(self) -> None:
        response = self.client.get("/api/runs")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("runs", payload)
        self.assertGreaterEqual(len(payload["runs"]), 1)

    def test_latest_pulse(self) -> None:
        latest = self.client.get("/api/runs/latest")
        self.assertEqual(latest.status_code, 200)
        run_id = latest.json()["run"]["run_id"]
        pulse = self.client.get(f"/api/runs/{run_id}/pulse")
        self.assertEqual(pulse.status_code, 200)
        body = pulse.json()
        self.assertIn("weekly_pulse", body)
        self.assertIn("top_themes", body["weekly_pulse"])

    def test_quotes_per_theme(self) -> None:
        latest = self.client.get("/api/runs/latest")
        run_id = latest.json()["run"]["run_id"]
        response = self.client.get(f"/api/runs/{run_id}/quotes?per_theme=5")
        self.assertEqual(response.status_code, 200)
        quotes = response.json()["quote_candidates"]
        self.assertGreaterEqual(len(quotes), 3)
        by_theme: dict[str, int] = {}
        for row in quotes:
            name = row["theme_name"]
            by_theme[name] = by_theme.get(name, 0) + 1
            self.assertLessEqual(by_theme[name], 5)


if __name__ == "__main__":
    unittest.main()
