from datetime import datetime, timedelta, timezone

from flask_jwt_extended import create_access_token, create_refresh_token, decode_token

from gateway.domain.seguridad import nuevo_jti

TIPO_TICKET_MFA = "mfa"
DURACION_TICKET_MFA_APP = 5  # minutos


class TokenServiceFlaskJWT:
    def crear_par(self, *, user_id, rol, email, refresh_jti, refresh_expira):
        access_token = create_access_token(
            identity=user_id,
            additional_claims={"rol": rol, "email": email},
        )
        refresh_token = create_refresh_token(
            identity=user_id,
            additional_claims={"rol": rol, "email": email, "jti": refresh_jti},
            expires_delta=refresh_expira - datetime.now(timezone.utc),
        )
        return {"access_token": access_token, "refresh_token": refresh_token}

    def crear_ticket_mfa(self, *, user_id, rol, email):
        """Firma un ticket de paso MFA de corta duración (no es sesión).

        El ticket se crea SOLO después de validar el password (o el perfil de
        Google) y permite completar el segundo factor. No concede acceso directo.
        """
        return create_access_token(
            identity=user_id,
            additional_claims={
                "rol": rol,
                "email": email,
                "tipo": TIPO_TICKET_MFA,
                "jti": nuevo_jti(),
            },
            expires_delta=timedelta(minutes=DURACION_TICKET_MFA_APP),
        )

    def decodificar_ticket(self, token: str) -> dict | None:
        """Decodifica un ticket MFA. Devuelve sus claims o None si es inválido."""
        try:
            claims = decode_token(token)
        except Exception:
            return None
        if claims.get("tipo") != TIPO_TICKET_MFA:
            return None
        return claims