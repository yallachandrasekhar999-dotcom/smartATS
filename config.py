import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'smart-resume-analyzer-secret-key-129837')
    
    # Dual database support: MySQL by default if configured, otherwise fallback to SQLite
    # Example MySQL URI: mysql+pymysql://username:password@localhost/resume_analyzer
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_DATABASE_URI') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'resume_analyzer.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload configurations
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}
