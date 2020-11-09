from flask import Flask

# Init Flask application object
app = Flask(__name__)

# Register all blueprints
from .controllers import manager
app.register_blueprint(manager.bp, url_prefix='/manager')

