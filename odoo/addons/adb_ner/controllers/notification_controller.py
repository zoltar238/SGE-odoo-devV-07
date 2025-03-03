from typing import Any


def create_notification(title: str, message: str, sticky: bool, notification_type: str) -> dict[str, str | dict[str, Any]]:
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': title,
            'message': message,
            'sticky': sticky,
            'type': notification_type
        }
    }