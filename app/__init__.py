from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Init Flask application object
app = Flask(__name__)
app.config.from_object('app.settings')

# Init flask-sqlalchemy
db = SQLAlchemy()
db.app = app
db.init_app(app)

# Register all blueprints
from .controllers import manager
from .controllers import load_balancer
from .controllers import auto_scaling

app.register_blueprint(manager.bp, url_prefix='/manager')
app.register_blueprint(load_balancer.bp, url_prefix='/load_balancer')
app.register_blueprint(auto_scaling.bp, url_prefix='/auto_scaling')

