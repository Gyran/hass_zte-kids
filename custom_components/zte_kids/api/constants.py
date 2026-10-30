"""Keys from decompiled ka.b — must match app flavor."""

from __future__ import annotations

from typing import Any

REGION_KEYS: dict[str, dict[str, Any]] = {
    "international": {
        "aes_key": "YNSSFWTeip5M2hSzmpoW4dXr0rWTc0Wr",
        "app_key": "U7yJRy5eO0DKTlNVrnx4z5ICm5y16a4S",
        "sign_secret_suffix": "fR1gX2AEiYxflz8sVsLFzfwTOfk8NzBu",
        "default_base": "https://care-api.nubia.com",
        "mqtt_tcp": "tcp://care.nubia.com:1883",
    },
    "cn": {
        "aes_key": "1jtTPMdnCUOAqToIiVy2NHfIraCWtSP3",
        "app_key": "HbhPoYjdh0jkczwkCyNEdY1nklvZIY5z",
        "sign_secret_suffix": "9VHl7FgycNCg4mJo0iQiT4EtLHIVxwkU",
        "default_base": "https://care-api.nubia.cn",
        "mqtt_tcp": "tcp://care.nubia.cn:1883",
    },
    "ug": {
        "aes_key": "JZ59dQJMrH40AiboiiZh6rzkf2WTg95i",
        "app_key": "6UWeo44v7736rUEB9WzDGXeVwIAD8gZI",
        "sign_secret_suffix": "LcbNr8gZb9HazNp3lQtBtSnTcc647GXc",
        "default_base": "https://care-api.nubia.com",
        "mqtt_tcp": "tcp://care.nubia.com:1883",
    },
}
