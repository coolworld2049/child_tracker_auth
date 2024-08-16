import uuid

import requests
from loguru import logger
from requests import HTTPError
from requests.auth import HTTPBasicAuth

from child_tracker_auth.settings import settings


def send_verification_sms(to_phone: str, code: str) -> bool | HTTPError:
    data = {
        "messages": [
            {
                "recipient": str(to_phone),
                "message-id": "".join(settings.project_name[:11])
                + uuid.uuid4().__str__()[:7],
                "sms": {
                    "originator": "3700",
                    "content": {
                        "text": f"Child-Tracker. Kod podtverjdeniya dlya vhoda {code} Nikomu ne soobshayte ego."
                        # Don`t touch
                    },
                },
            }
        ]
    }
    response = requests.post(
        "https://send.smsxabar.uz/broker-api/send",
        json=data,
        headers={
            "Content-Type": "application/json",
        },
        auth=HTTPBasicAuth(settings.sms_provider_login, settings.sms_provider_password),
    )
    response.encoding = "utf-8"
    if response.status_code == 200:
        logger.info(f"Sent confirmation code to phone number {to_phone}")
        return True
    else:
        logger.error(
            f"url: {response.url} response.status_code: {response.status_code} response.text: {response.text}"
        )
        response.raise_for_status()
