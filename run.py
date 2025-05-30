from flask import Flask

from app.routes import bp as main_bp

def main():
    app = Flask(__name__)

    app.config['DEBUG'] = True

    app.register_blueprint(main_bp)

    return app

if __name__ == '__main__':
    app = main()
    app.run()
