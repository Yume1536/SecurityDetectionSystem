import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
    MYSQL_HOST = os.getenv('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'root')
    MYSQL_DB = os.getenv('MYSQL_DB', 'security_detection')
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ALGO_SERVICE_URL = os.getenv('ALGO_SERVICE_URL', 'http://127.0.0.1:5001')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(os.path.dirname(__file__), 'uploads'))
    HEATMAP_FOLDER = os.getenv('HEATMAP_FOLDER', os.path.join(os.path.dirname(__file__), 'static', 'heatmaps'))
    REPORT_FOLDER = os.getenv('REPORT_FOLDER', os.path.join(os.path.dirname(__file__), 'reports'))
