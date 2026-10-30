# Reverse engineering notes (ZTE Kids / Nubia Care)

This Home Assistant integration talks to the **Nubia Care** cloud API used by the
**ZTE Kids** parent app. The client was built by decompiling the Android app and
matching login, request signing, and device endpoints.

Local APK / jadx / old CLIs live under **`reverse_engineering/`** (gitignored except
its README). Rebuild them when the API breaks or you need to rediscover endpoints.
See [`reverse_engineering/README.md`](../reverse_engineering/README.md).

## 1. Get the APK

1. Install the official **ZTE Kids** / **Nubia Care** parent app on an Android device
   (or obtain the APK from a source you trust).
2. Note the app version (useful when comparing future decompiles).
3. Copy the APK into this repo as e.g. `reverse_engineering/apk/zte-kids.apk`.

## 2. Decompile with jadx

```bash
# Install jadx: https://github.com/skylot/jadx
mkdir -p reverse_engineering/apk reverse_engineering/jadx_out
jadx -d reverse_engineering/jadx_out reverse_engineering/apk/zte-kids.apk
```

Expect a large Java tree under `reverse_engineering/jadx_out/sources/`.

## 3. What to look for

| Topic                             | Where (in the decompile we used)                  | What it taught us                                                                                |
| --------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Region AES / appKey / sign secret | `ka/b.java`                                       | Keys for `international`, `cn`, `ug`; default API bases                                          |
| Password encryption               | `ta/f.java` → `a()`                               | AES/GCM/NoPadding, 12-byte IV, Base64(`IV \|\| ciphertext+tag`)                                  |
| Request signing                   | `SecurityGuardRequestFilter`                      | Sorted `key=value&`… + secret suffix, SHA-256 hex; query: `sign`, `timestamp`, `nonce`, `appKey` |
| Login API                         | `y3/a.java` → `api/account/login`                 | JSON body: `loginName`, encrypted `password`, `dypwdFlag`, `mobileType`; `need-token:false`      |
| Related devices                   | Gateway `getway/accounts/{openid}/related-device` | Device list with nested `lastLocation`, `battery`, `onlineStatus`, `imei`                        |
| Last location POST                | `getway/devices/{imei}/location/last`             | Often returns `{ "code": 0 }` with **no** lat/lon — prefer `lastLocation` on related-device      |
| MQTT defaults                     | `ka/b.java` / MQTT helpers                        | Broker/user/topic patterns exist; **not** used by the HA integration yet                         |

Implemented client: [`custom_components/zte_kids/api/`](../custom_components/zte_kids/api/).

## 4. Auth behaviour observed

- Login success → `accesstoken`, `openid`, `token_expire_time` (~30 days).
- Wrong password → API code `1132`.
- Password “format” / too long → `1022` (`密码格式不正确`). **Server rejects passwords longer than 16 characters** even if the app UI allows 8–20.
- Expired token on related-device → `1002` (`无效token`) — integration re-logins with stored credentials.

## 5. Device identity

- Use API field **`imei`** as the stable unique id for HA entities and gateway paths.
- Do **not** use `bindNo` for API paths (optional attribute only).

## 6. Home Assistant mapping

Poll **related-device** only:

| Field                                 | Entity                 |
| ------------------------------------- | ---------------------- |
| `lastLocation.lat` / `lon` / `radius` | `device_tracker`       |
| `battery.percent`                     | `sensor` battery       |
| `onlineStatus`                        | `binary_sensor` online |

`lastLocation.timestamp` is Unix **seconds**. `battery.updateTime` is often **milliseconds**.

## 7. Re-verify after an app update

1. Fresh APK + jadx.
2. Diff `ka/b.java` keys and `ta/f.java` encrypt.
3. Diff `SecurityGuardRequestFilter` sign construction.
4. Hit login + related-device with the probe script (below).
5. Update `custom_components/zte_kids/api/` if anything changed.

```bash
# From repo root, with .env set (see .env.example):
.venv-ha/bin/python tests/manual/probe_api.py
```
