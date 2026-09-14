from datetime import datetime, timezone
from flask_jwt_extended import create_access_token, create_refresh_token

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