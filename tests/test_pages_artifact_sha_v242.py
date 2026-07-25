from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / ".github" / "workflows" / "deploy-validated-main.yml"
PROOF = ROOT / ".github" / "workflows" / "verify-special-needs-live-v236.yml"
EVENT_SHA = "${{ github.event.workflow_run.head_sha }}"


class PagesArtifactShaV242Tests(unittest.TestCase):
    def test_pages_uses_stamped_artifact_sha_as_candidate(self) -> None:
        source = DEPLOY.read_text(encoding="utf-8")

        self.assertIn("data = json.loads((root / 'deployment.json').read_text", source)
        self.assertIn("candidate = data.get('commit')", source)
        self.assertIn("handle.write(f'CANDIDATE_SHA={candidate}\\n')", source)
        self.assertIn("candidate = os.environ['CANDIDATE_SHA']", source)
        self.assertIn("TOKEN=\"${CANDIDATE_SHA}\"", source)
        self.assertIn("expected_sha = os.environ['CANDIDATE_SHA']", source)
        self.assertIn("pages-provenance-v242", source)
        self.assertIn("artifact_candidate_sha", source)
        self.assertIn("trigger_reported_sha", source)

        self.assertNotIn(f"CANDIDATE_SHA: {EVENT_SHA}", source)
        self.assertNotIn(f"EXPECTED_SHA: {EVENT_SHA}", source)
        self.assertNotRegex(
            source,
            re.compile(r"candidate\s*=\s*os\.environ\[['\"]TRIGGER_REPORTED_SHA['\"]\]"),
        )
        self.assertNotRegex(
            source,
            re.compile(r"expected_sha\s*=\s*os\.environ\[['\"]TRIGGER_REPORTED_SHA['\"]\]"),
        )

        # The event SHA remains metadata/provenance only; it is never exported as CANDIDATE_SHA.
        self.assertGreaterEqual(source.count(EVENT_SHA), 1)
        self.assertIn("TRIGGER_REPORTED_SHA: ${{ github.event.workflow_run.head_sha }}", source)

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
        self.assertIn("run-id: ${{ github.event.workflow_run.id }}", source)
        self.assertIn("name: validated-production-site", source)
        self.assertIn("path: validated-site", source)


if __name__ == "__main__":
    unittest.main()
