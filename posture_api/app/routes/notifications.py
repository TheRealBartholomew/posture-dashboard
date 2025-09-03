from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import User, NotificationSettings, PostureReading
from extensions import socketio

def safe_emit_notification_triggered(name, data, user_id=None):
    try:
        room = f"user_{user_id}" if user_id else None
        socketio.emit(name, data, room=room)
    except Exception as e:
        print(f"Failed to emit {name} to {room}: {e}")

bp = Blueprint("notifications", __name__, url_prefix="/api")

@bp.route("/notifications", methods=["POST"])
def set_notification():
    db: Session = SessionLocal()
    try:
        data = request.get_json()
        if not data or "user_id" not in data or "enabled" not in data:
            return jsonify({"error": "user_id and enabled are required"}), 400
        
        user_id = data["user_id"]
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        settings = db.query(NotificationSettings).filter(NotificationSettings.user_id == user_id).first()

        if not settings:
            settings = NotificationSettings(user_id=user_id)
            db.add(settings)

        if "enabled" in data:
            settings.enabled = data["enabled"]
        if "threshold_angle" in data:
            settings.threshold_angle = data["threshold_angle"]
        if "notification_interval" in data:
            settings.notification_interval = data["notification_interval"]
        if "quiet_hours_start" in data:
            settings.quiet_hours_start = data["quiet_hours_start"]
        if "quiet_hours_end" in data:
            settings.quiet_hours_end = data["quiet_hours_end"]

        db.commit()
        
        return jsonify({"status": "updated",
            "user_id": user_id,
            "settings": {
                "enabled": settings.enabled,
                "threshold_angle": settings.threshold_angle,
                "notification_interval": settings.notification_interval,
                "quiet_hours_start": str(settings.quiet_hours_start) if settings.quiet_hours_start else None,
                "quiet_hours_end": str(settings.quiet_hours_end) if settings.quiet_hours_end else None,
            }
        }), 200
    
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@bp.route("/notifications/<int:user_id>", methods=["GET"])
def get_notification(user_id):
    db: Session = SessionLocal()
    try:
        settings = db.query(NotificationSettings).filter(NotificationSettings.user_id == user_id).first()

        if not settings:
            return jsonify({"error": "Notification settings not found"}), 404

        latest_angle = db.query(PostureReading).filter(PostureReading.user_id == user_id).order_by(PostureReading.timestamp.desc()).first()

        if settings and settings.enabled:
            if latest_angle.angle > settings.threshold_angle:
                safe_emit_notification_triggered("notification_triggered", {"user_id": user_id, "message": f"bad posture detected. angle: {latest_angle.angle}° exceeds threshold: {settings.threshold_angle}°", "severity": "warning", "threshold_angle": settings.threshold_angle}, user_id)

        return jsonify({
            "user_id": user_id,
            "settings": {
                "enabled": settings.enabled,
                "threshold_angle": settings.threshold_angle,
                "notification_interval": settings.notification_interval,
                "quiet_hours_start": str(settings.quiet_hours_start) if settings.quiet_hours_start else None,
                "quiet_hours_end": str(settings.quiet_hours_end) if settings.quiet_hours_end else None,
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()