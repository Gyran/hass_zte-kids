# ZTE Kids (Home Assistant)

Unofficial [Home Assistant](https://www.home-assistant.io/) custom integration for **ZTE Kids** watches via the **Nubia Care** parent cloud API.

**Entities:** `device_tracker` (location), battery `%`, online status, last location fix, refresh-location button.  
**Setup:** config flow only (no custom Lovelace UI).

> This is reverse-engineered and unsupported. It can break when Nubia changes the API. See [docs/REVERSE_ENGINEERING.md](docs/REVERSE_ENGINEERING.md).

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=zte_kids)

## Install (HACS custom repository)

Not submitted to the HACS default list / Marketplace — add as a **custom repository** only.

1. HACS → Integrations → Custom repositories → add this GitHub repo (category: Integration)
2. Install **ZTE Kids**
3. Restart Home Assistant if prompted
4. Settings → Devices & services → Add integration → **ZTE Kids** (or My link above after install)

## Install (manual)

Copy [`custom_components/zte_kids`](custom_components/zte_kids) into your HA `config/custom_components/`, restart, then add **ZTE Kids** via the UI.

## Configuration

| Field            | Notes                                                 |
| ---------------- | ----------------------------------------------------- |
| Email / password | Same account as the ZTE Kids / Nubia Care parent app  |
| Password length  | **8–16 characters** (server returns `1022` if longer) |
| Region           | `international` (default), `cn`, or `ug`              |
| Update interval  | Default 300s (minimum 60)                             |

One HA device per watch (`imei`):

| Entity                      | Source                                                        |
| --------------------------- | ------------------------------------------------------------- |
| `device_tracker.*`          | `lastLocation.lat` / `lon` / `radius`                         |
| `sensor.*_battery`          | `battery.percent`                                             |
| `binary_sensor.*_online`    | `onlineStatus == 1`                                           |
| `sensor.*_last_location_fix`| `lastLocation.timestamp` (diagnostic)                         |
| `button.*_refresh_location` | `POST location/last`, then poll until the timestamp changes   |

Service `zte_kids.refresh_location` does the same thing as the button. In an automation, target the watch device or any of its entities. Several watches run one after another.

Setup shows an error when the account has no watches, and does not create the entry. After setup, an empty poll does not fail the integration. A watch paired later shows up on the next poll.

State comes from polling **related-device**. The refresh button and the service ask the watch for a new fix first. The POST response usually has no coordinates. Invalid token (`1002`) triggers re-login; persistent failure starts reauth.

## Repository layout

```
hacs.json
LICENSE
README.md
docs/REVERSE_ENGINEERING.md     # tracked RE notes
custom_components/zte_kids/     # HA integration (HACS installs this)
scripts/                        # setup + develop only
tests/manual/                   # API probe / smoke (not HA tooling)
reverse_engineering/            # local APK/jadx/old CLIs (ignored except README)
config/configuration.yaml.example
.env.example
```

Not in git (see `.gitignore`): everything under `reverse_engineering/` except its README,
`.env`, local HA `.storage`, venvs.

## Local development

Needs **Python 3.14+** for current Home Assistant pins in `requirements_dev.txt`.

```bash
cp .env.example .env   # fill NUBIA_EMAIL / NUBIA_PASSWORD
scripts/setup          # .venv-ha + HA install
scripts/develop        # HA on http://127.0.0.1:8123
```

Onboard and add **ZTE Kids** in the UI. Manual API/integration checks: [`tests/manual/`](tests/manual/).

## License

MIT — see [LICENSE](LICENSE).
