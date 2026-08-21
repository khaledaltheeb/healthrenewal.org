Production release trigger for care-guides extension sitemap coverage contract.

Required main ancestry:
- 1683e18589d8dde2ec38fe0e76d971b210a790be (extension-aware coverage contract)
- 60bac5ef8be08bace2f09e2955cc83d180067c26 (quick-info publication restore)
- e416f389c6afcc6523dfcd489008f9a52ea40ffd (pediatric oncology palliative/bereavement five-page publication source)
- 83d3967fcf730ce178b13d6141c70d8c1386010a (pediatric oncology evidence materialization: five study routes and one thesis route)

Release retrigger: 2026-08-21T11:16:00+03:00. Trigger the current production-v6 workflow from the latest main state after the earlier dispatched run was cancelled before starting jobs.

Do not treat this marker as production evidence. Production status is determined only by deploy-production-v3.yml and subsequent live verification.
