# V2.4.1 Reliance on security patches

> Date: 2026-09-17.Scope:Tornado Locks the version and release records without changing the logic of the application.

V2.4.0 After release[CI Security checks](https://github.com/eddyzzl/marvis-risk-agent/actions/runs/35185959598/job/105087970316)
Found the lock file.Tornado 6.5.7 Hit.`PYSEC-2026-3928`,`GHSA-wwv5-g3v4-889x`
and`GHSA-8423-8fgw-73vq`,and will be 6.5.8 Listed as fixes version.
[Upstream 6.5.8 Issuance of notes](https://www.tornadoweb.org/en/stable/releases/v6.5.8.html)
Description of the number of form parameters,multipart Memory consumption and old patterncookie Parameter verification safety fixes.

Pass.`uv lock --upgrade-package tornado==6.5.8` The new version of the report is a new one for the Hashi.
The rest of the versions are unchanged, without missing loopholes, without lowering the level of the checks, without moving already publicly availableV2.4.0 label.
Patch version still from`scripts/release_push.py` Create and push.

## Authentication

- andCI Same lock file export withpip-audit 2.10.1 Check exit code 0, result is
  `No known vulnerabilities found`.
- andCI Same complete regressionBandit 1.9.4 Baseline check exit code 0; original baseline unchanged.
- `uv lock --check` and`git diff --check` Pass.
- [V2.4.0 Full doorbar](2026-09-17-v2-4-0-release-readiness.md) of 12,415 Adoption of the outcome
  From installedTornado 6.5.8 * The present document contains the text of the decision taken by the Committee at its 1st meeting, on 2 October 2008.Tornado The test is already in existence before this round.
  This patch does not apply code changes, so the package 1 is not repeated:43:05 - The test.
- Formal Patchwheel Reconstruct and reconcile after the release upgrade; remote security checks and the restCI Status submitted as Patch
  Actions The result is the same as the local scan.CI All done.

No day-to-day changes in current cycleconda Environment. Native.Windows,RealLLM,Qualified boundary between production deployment and operational signature
The same is true.
