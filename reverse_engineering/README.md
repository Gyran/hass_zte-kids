# Reverse engineering workspace

Local-only scratch space. **Ignored by git** except this README.

Tracked notes live in [`docs/REVERSE_ENGINEERING.md`](../docs/REVERSE_ENGINEERING.md).

## Layout (create as needed)

| Path                                   | Purpose                                    |
| -------------------------------------- | ------------------------------------------ |
| `apk/`                                 | ZTE Kids / Nubia Care APKs                 |
| `jadx_out/`                            | jadx decompile output                      |
| `bruno/`                               | Bruno / HTTP collections                   |
| `nubia_care/`                          | Old standalone Python client (pre-HA)      |
| `nubia_login.py` / `nubia_location.py` | Old CLI probes                             |
| `nubia_session.json`                   | Local session dump                         |
| `pyproject.toml`                       | Packaging for the old `nubia_care` package |

## Decompile

```bash
# From repo root
mkdir -p reverse_engineering/apk reverse_engineering/jadx_out
# copy APK → reverse_engineering/apk/zte-kids.apk
jadx -d reverse_engineering/jadx_out reverse_engineering/apk/zte-kids.apk
```

## Old CLI (optional)

```bash
cd reverse_engineering
# needs deps from historical pyproject / local venv
python nubia_login.py
```

Prefer [`tests/manual/probe_api.py`](../tests/manual/probe_api.py) against the HA client.
