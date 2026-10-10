# Policy, testing and acceptance pack

Bilingual draft handoff; external results and signatures remain unexecuted. This package grants no production acceptance.

- [POLICY_PACK](policies/POLICY_PACK_EN.md)
- [COVER_LETTER](policies/COVER_LETTER_EN.md)
- [CLIENT_REQUIREMENTS](policies/CLIENT_REQUIREMENTS_EN.md)
- [WINDOWS_LAPTOP_GUIDE](WINDOWS_LAPTOP_GUIDE_EN.md)
- [DEPLOYMENT_GUIDE](DEPLOYMENT_GUIDE_EN.md)
- [EXTERNAL_TEST_PLAN](EXTERNAL_TEST_PLAN_EN.md)
- [EXTERNAL_TEST_REPORT_TEMPLATE](EXTERNAL_TEST_REPORT_TEMPLATE_EN.md)
- [UAT_PLAN](UAT_PLAN_EN.md)
- [UAT_SCENARIOS](UAT_SCENARIOS_EN.md)
- [UAT_CHECKLIST](UAT_CHECKLIST_EN.md)
- [PENETRATION_TEST_PLAN](PENETRATION_TEST_PLAN_EN.md)
- [PENETRATION_TEST_SCOPE](PENETRATION_TEST_SCOPE_EN.md)

Canonical filenames contain Arabic; `_EN.md` counterparts share document IDs and versions. Includes 13 financial FIN-ADRs distinct from architecture ADRs, 25 UAT scenarios and 15 security test areas. UAT-25 is blocked by unavailable production G5 execution.

[Check wrapper](../scripts/deploy_check.sh) invokes the [checker](../scripts/deploy_check.py) without installation, migration or data changes. Passing indicates engineering checks only. Authoritative references: [acceptance contract](ACCEPTANCE_CONTRACT.md), [gate status](../GATE_STATUS.md), [API coverage](FRONTEND_ROUTE_API_MATRIX.md).
