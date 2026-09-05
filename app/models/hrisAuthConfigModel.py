from app import db


class HrisAuthConfig(db.Model):
    __tablename__ = 'HRIS_AUTH_CONFIG'

    ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    AUTH_MODE = db.Column(db.String(10), nullable=False, default='LOCAL')
    SSO_SERVER = db.Column(db.String(255), nullable=True)
    SSO_CALLBACK = db.Column(db.String(255), nullable=True)
    SYSADMIN_USERNAME = db.Column(db.String(50), nullable=False)
    SYSADMIN_PASSWORD_HASH = db.Column(db.String(255), nullable=False)
    SYSADMIN_ENABLED = db.Column(db.Boolean, nullable=False, default=True)
    CREATED_AT = db.Column(db.DateTime, nullable=False)
    UPDATED_AT = db.Column(db.DateTime, nullable=False)

    def to_dict(self):
        return {
            'id': self.ID,
            'auth_mode': self.AUTH_MODE,
            'sso_server': self.SSO_SERVER,
            'sso_callback': self.SSO_CALLBACK,
            'sysadmin_username': self.SYSADMIN_USERNAME,
            'sysadmin_enabled': bool(self.SYSADMIN_ENABLED),
            'created_at': self.CREATED_AT,
            'updated_at': self.UPDATED_AT,
        }
