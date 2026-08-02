from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / ".github" / "workflows" / "deploy-complete-pages-with-ai-search.yml"
PROOF = ROOT / ".github" / "workflows" / "verify-special-needs-live-v236.yml"
EVENT_SHA = "${{ github.event.workflow_run.head_sha }}"


class PagesArtifactShaV242Tests(unittest.TestCase):
    def test_pages_selects_latest_complete_main_artifact(self) -> None:
        source = DEPLOY.read_text(encoding="utf-8")

        self.assertIn("BASELINE_ARTIFACT: validated-production-site", source)
        self.assertIn('item.get("workflow_run", {}).get("head_branch") == "main"', source)
        self.assertIn("if not item.get(\"expired\")", source)
        self.assertIn("max(candidates, key=lambda value: value.get(\"created_at\", \"\"))", source)
        self.assertIn("output.write(f\"run_id={item['workflow_run']['id']}\\n\")", source)
        self.assertIn("output.write(f\"artifact_id={item['id']}\\n\")", source)
        self.assertIn("ref: main", source)

    def test_live_proof_uses_public_deployment_sha(self) -> None:
        source = PROOF.read_text(encoding="utf-8")

        self.assertIn("LIVE_SHA=\"$(python", source)
        self.assertIn("data=json.loads(Path('/tmp/special-needs-live-v236/deployment.json')", source)
        self.assertIn("echo \"LIVE_SHA=${LIVE_SHA}\" >> \"$GITHUB_ENV\"", source)
        self.assertIn("live = os.environ['LIVE_SHA']", source)
        self.assertIn("required_to_live = compare(required, live)", source)
        self.assertIn("live_to_current = compare(live, current)", source)
        self.assertIn('--expected-sha "${LIVE_SHA}"', source)
        self.assertIn("data['sha_source']='live-deployment-json'", source)

        self.assertNotIn(f"EXPECTED_SHA: {EVENT_SHA}", source)
        self.assertNotIn(f"LIVE_SHA: {EVENT_SHA}", source)
        self.assertNotIn("candidate = os.environ['EXPECTED_SHA']", source)
        self.assertIn("TRIGGER_REPORTED_SHA: ${{ github.event.workflow_run.head_sha }}", source)

    def test_artifact_run_id_remains_exact(self) -> None:
        source = DEPLOY.read_text(encoding="utf-8")
        self.assertIn("run-id: ${{ steps.baseline.outputs.run_id }}", source)
        self.assertIn("name: ${{ env.BASELINE_ARTIFACT }}", source)
        self.assertIn("path: _site", source)
        self.assertIn("repository: khaledaltheeb/healthrenewal.org", source)
        self.assertIn("github-token: ${{ github.token }}", source)


if __name__ == "__main__":
    unittest.main()
