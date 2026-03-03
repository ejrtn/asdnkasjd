import firebase_admin  # type: ignore[import-not-found]
from firebase_admin import credentials, messaging  # type: ignore[import-not-found]

from app.core import config

_app: firebase_admin.App | None = None


def get_firebase_app() -> firebase_admin.App:
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


async def send_push(fcm_token: str, title: str, body: str, data: dict | None = None) -> bool:
    """FCM 푸시 알림 발송"""
    try:
        get_firebase_app()
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=fcm_token,
        )
        messaging.send(message)
        return True
    except Exception as e:
        print(f"FCM send error: {e}")
        return False
