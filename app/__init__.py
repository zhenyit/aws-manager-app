from flask import Flask

# Init Flask application object
app = Flask(__name__)

# Register all blueprints
from .controllers import manager
from .controllers import load_balancer
from .controllers import auto_scaling

app.register_blueprint(manager.bp, url_prefix='/manager')
app.register_blueprint(load_balancer.bp, url_prefix='/load_balancer')
app.register_blueprint(auto_scaling.bp, url_prefix='/auto_scaling')

