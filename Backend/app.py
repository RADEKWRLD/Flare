from flask import Flask
from flask_cors import CORS
from config.settings import app_config
from routes.auth_routes import auth_bp
from routes.todo_routes import todo_bp
from routes.search_routes import search_bp
from waitress import serve

def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True)
    app.config['SECRET_KEY'] = app_config.secret_key
    
    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(todo_bp)
    app.register_blueprint(search_bp)
    
    return app

if __name__ == "__main__":
    app = create_app()
    ##开发环境
    # app.run(host='0.0.0.0', port=5000)
    serve(app, host='0.0.0.0', port=5000,threads=32)

