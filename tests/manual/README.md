# Manual checks

Optional one-off scripts. **Not** pytest. **Not** HA start/setup tooling.

| Script                     | Needs                 | What                                   |
| -------------------------- | --------------------- | -------------------------------------- |
| `probe_api.py`             | `.env` Nubia creds    | Login + related-device dump (no HA)    |
| `smoke_add_integration.py` | HA on `:8123`, `.env` | Onboard + config flow + print entities |

HA tooling stays in [`scripts/`](../../scripts/) (`setup`, `develop` only).
