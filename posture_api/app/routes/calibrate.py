from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from app.db import get_db, SessionLocal
from app.models import User, CalibrateSession
from datetime import datetime
from extensions import socketio, logger

def safe_emit_calibration_complete(name, data, user_id=None):
    try:
        room = f"user_{user_id}" if user_id else None
        socketio.emit(name, data, room=room)
    except Exception as e:
        logger.error(f"Failed to emit {name} to {room}: {e}")

    except Exception as e:
        logger.error(f"Failed to emit calibration_complete to user_{user_id}: {e}")

bp = Blueprint("calibrate", __name__, url_prefix="/api")

@bp.route("/calibrate", methods=["POST"])
def calibrate():
    db: Session = SessionLocal()
    try:
        data = request.get_json()

        if not data or "user_id" not in data or "baseline_angle" not in data:
            return jsonify({"error": "user_id and baseline_angle are required"}), 400
        
        user_id = data["user_id"]
        baseline_angle = data["baseline_angle"]

        if not isinstance(baseline_angle, (int, float)):
            return jsonify({"error": "baseline_angle must be a number"}), 400
        
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user.baseline_angle = baseline_angle

        session_entry = CalibrateSession(
            user_id=user_id,
            baseline_angle=baseline_angle,
            timestamp=datetime.utcnow()
        )
        db.add(session_entry)
        db.commit()

        safe_emit_calibration_complete("calibration_complete", {"user_id": user_id, "baseline_angle": baseline_angle}, user_id)

        return jsonify({"status": "calibrated",
            "user_id": user_id,
            "baseline_angle": baseline_angle,
            "timestamp": session_entry.timestamp.isoformat()
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        db.close()
