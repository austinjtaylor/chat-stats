"""
Authentication middleware for Supabase JWT token validation.
Protects API endpoints and extracts user information from tokens.
"""

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional

from supabase_client import get_jwt_secret as get_supabase_jwt_secret, SUPABASE_URL
from utils.security_logger import log_auth_failure

# Security scheme for Bearer tokens
security = HTTPBearer()


def get_jwt_secret() -> str:
    """
    Get the JWT secret for token verification.
    Supabase JWTs are signed with the JWT_SECRET (not the service key).
    """
    return get_supabase_jwt_secret()


def decode_jwt_token(token: str, ip_address: Optional[str] = None) -> dict:
    """
    Decode and validate a Supabase JWT token.

    Args:
        token: JWT token string
        ip_address: Client IP address for logging

    Returns:
        Decoded token payload with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Decode the token using the Supabase service key as secret
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=["HS256"],
            audience="authenticated",  # Supabase audience
        )
        return payload
    except jwt.ExpiredSignatureError:
        log_auth_failure(
            reason="expired_token",
            ip_address=ip_address,
            details={"error": "Token has expired"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        log_auth_failure(
            reason="invalid_token",
            ip_address=ip_address,
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Dependency to get the current authenticated user from JWT token.
    Use this in protected routes.

    Args:
        request: FastAPI request object (for IP logging)
        credentials: Bearer token from Authorization header

    Returns:
        User information from token payload

    Example:
        @app.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"user_id": user["sub"], "email": user.get("email")}
    """
    token = credentials.credentials
    ip_address = request.client.host if request.client else None
    payload = decode_jwt_token(token, ip_address=ip_address)

    # Extract user information
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
        )

    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role"),
        "exp": payload.get("exp"),
        "iat": payload.get("iat"),
    }


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[dict]:
    """
    Optional auth dependency - returns user if authenticated, None otherwise.
    Use this for routes that work with or without auth.

    Args:
        credentials: Optional Bearer token from Authorization header

    Returns:
        User information if authenticated, None otherwise

    Example:
        @app.get("/public-or-private")
        async def flexible_route(user: Optional[dict] = Depends(get_current_user_optional)):
            if user:
                return {"message": f"Welcome {user['email']}"}
            return {"message": "Welcome guest"}
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        payload = decode_jwt_token(token)
        user_id = payload.get("sub")

        if not user_id:
            return None

        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "role": payload.get("role"),
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
        }
    except HTTPException:
        return None


def verify_user_owns_resource(user_id: str, resource_user_id: str) -> bool:
    """
    Verify that a user owns a specific resource.

    Args:
        user_id: Current user's ID
        resource_user_id: User ID associated with the resource

    Returns:
        True if user owns the resource

    Raises:
        HTTPException: If user doesn't own the resource
    """
    if user_id != resource_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this resource"
        )
    return True


# Example protected route decorator
def require_auth(user: dict = Depends(get_current_user)) -> dict:
    """
    Simple dependency to require authentication.
    Returns the authenticated user.

    Example:
        @app.get("/profile")
        async def get_profile(user: dict = Depends(require_auth)):
            return {"user_id": user["user_id"]}
    """
    return user
