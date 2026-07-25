from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "verify-special-needs-hub-live-v241.yml"
EVENT_SHA = "${{ github.event.workflow_run.head_sha }}"


class SpecialNeedsHubShaV241Tests(unittest.TestCase):
    def test_live_deployment_stamp_is_authoritative(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("LIVE_SHA=\"$(python", source)
        self.assertIn("data=json.loads(Path('/tmp/special-needs-hub-live-v241/deployment.json')", source)
        self.assertIn("echo \"LIVE_SHA=${LIVE_SHA}\" >> \"$GITHUB_ENV\"", source)
        self.assertIn("live=os.environ['LIVE_SHA']", source)
        self.assertIn("api(f'/compare/{live}...{current}')", source)
        self.assertIn('--expected-sha "${LIVE_SHA}"', source)
        self.assertIn("data['sha_source']='live-deployment-json'", source)
        self.assertIn("ref: main", source)

        self.assertNotIn(f"EXPECTED_SHA: {EVENT_SHA}", source)
        self.assertNotIn(f"LIVE_SHA: {EVENT_SHA}", source)
        self.assertIn("TRIGGER_REPORTED_SHA: ${{ github.event.workflow_run.head_sha }}", source)


if __name__ == "__main__":
    unittest.main()
