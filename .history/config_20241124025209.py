# config.py

class Config:
    SECRET_KEY = 'your_secret_key'  # Replace with a strong secret key
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable unnecessary tracking
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://root:BU%40%232006@localhost/facemate'


