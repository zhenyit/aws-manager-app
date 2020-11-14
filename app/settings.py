import os
from dotenv import load_dotenv

load_dotenv()

AMI_ID = 'ami-e3f432f5'
SUBNET_ID = 'Fill with your subnet Id'

SECRET_KEY = os.urandom(32)

# SQLite Database Config
APP_PATH = os.path.dirname(os.path.abspath(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + APP_PATH + '/models/sqlite.db'
SQLALCHEMY_TRACK_MODIFICATIONS = True