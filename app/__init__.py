from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = 'your-secret-key-goes-here' # IMPORTANT: Change this!
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db' # Database file name
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login' # Redirect to login page if user is not logged in

    # Import and register the blueprint from routes.py
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # User loader function for Flask-Login
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app