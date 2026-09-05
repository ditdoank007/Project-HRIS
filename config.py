# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # baca file .env

class Config:
    AUTH_MODE = os.getenv('AUTH_MODE', 'LOCAL').upper()
    BDIP_SSO_URL = os.getenv('BDIP_SSO_URL', 'https://bdip.sarsurabaya.id')
    HRIS_SSO_CALLBACK = os.getenv('HRIS_SSO_CALLBACK', 'http://hris.sarsurabaya.id/api/login/sso')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = os.getenv('DB_PORT')
    DB_NAME = os.getenv('DB_NAME')

    # Format URI: mysql+pymysql://user:password@host:port/dbname
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # matikan overhead tracking yg gak perlu

    GOOGLE_CALENDAR_API_KEY = os.environ.get('GOOGLE_CALENDAR_API_KEY')

    SECRET_KEY = os.getenv('SECRET_KEY')