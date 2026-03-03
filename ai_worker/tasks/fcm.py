"""ai_worker용 FCM 푸시 발송 태스크"""

import logging

import firebase_admin  # type: ignore[import-not-found]
from firebase_admin import credentials, messaging  # type: ignore[import-not-found]

from ai_worker.core.config import Config

config = Config()
_app: firebase_admin.App | None = None


def _get_app() -> firebase_admin.App:
    global _app
    if _app is None:
        cred = credentials.Certificate(
            {
                "type": "service_account",
                "project_id": config.FIREBASE_PROJECT_ID,
                "private_key": config.FIREBASE_PRIVATE_KEY.replace("\\n", "\n"),
                "client_email": config.FIREBASE_CLIENT_EMAIL,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )
        _app = firebase_admin.initialize_app(cred)
    return _app


async def send_push_notification(fcm_token: str, title: str, body: str, data: dict | None = None) -> bool:
    try:
        _get_app()
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=fcm_token,
        )
        messaging.send(message)
        logging.info(f"📱 FCM 발송 성공: {title}")
        return True
    except Exception as e:
        logging.error(f"❌ FCM 발송 실패: {e}")
        return False
