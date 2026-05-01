"""Backward compatibility - use app.services.auth_service and interfaces.api.dependencies instead."""

from interfaces.api.dependencies import auth_service, get_current_user, oauth2_scheme

hash_password = auth_service.hash_password
verify_password = auth_service.verify_password
create_access_token = auth_service.create_access_token

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "get_current_user",
    "oauth2_scheme",
]
