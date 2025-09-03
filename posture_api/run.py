from flask import Flask, request, render_template
from flask_socketio import SocketIO, join_room
from app.db import engine, Base
from app.routes import posture, users, calibrate, stats, notifications, overview
import logging
from extensions import socketio, logger
from collections import deque
from flask_socketio import emit



app = Flask(__name__, template_folder='app/templates', static_folder='app/static')

socketio.init_app(app, cors_allowed_origins="*")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard_design_1.html", default_user_id=1)

@socketio.on('connect')
def handle_connect(auth):
    user_id = request.args.get('user_id', 0)
    join_room(f"user_{user_id}")
    print(f"User {user_id} connected and joined room user_{user_id}")
    

@socketio.on("disconnect")
def handle_disconnect():
    logger.info("Client disconnected")

app.register_blueprint(posture.bp)
app.register_blueprint(users.bp)
app.register_blueprint(calibrate.bp)
app.register_blueprint(stats.bp)
app.register_blueprint(notifications.bp)
app.register_blueprint(overview.bp)

Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    
    logger.info("Starting Server...")
    socketio.run(app, debug=True)

