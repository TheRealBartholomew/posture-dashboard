from flask import Blueprint, request, jsonify, Response
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import User, PostureReading, CalibrateSession
from datetime import datetime, date
from extensions import logger, posture_buffer, socketio
from collections import deque
import csv

bp = Blueprint("posture", __name__, url_prefix="/api")

tracking_active = True

def safe_emit_posture_update(name, data, user_id=None):
    try:
        room = f"user_{user_id}" if user_id else None
        socketio.emit(name, data, room=room)
    except Exception as e:
        print(f"Failed to emit {name} to {room}: {e}")

def quality_to_label(quality_score):
    if quality_score == 5:
        return "Good"
    elif quality_score == 3:
        return "Warning"
    else:
        return "Bad"

@bp.route("/export", methods=["GET"])
def export_posture_data():
    today = date.today()
    db: Session = SessionLocal()
    try:
        rows = db.query(PostureReading).filter(PostureReading.timestamp >= today).all()
        def generate():
            yield "id,user_id,angle,quality_score,posture,timestamp\n"
            for row in rows:
                yield f"{row.id},{row.user_id},{row.angle},{row.quality_score},{row.posture},{row.timestamp}\n"

        return Response(
            generate(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=posture_data.csv"}
        )
    finally:
        db.close()

@bp.route("/api/posture/buffer")
def get_buffer():
    result = []
    for user_id, dq in posture_buffer.items():
        # convert deque to list of readings and include user_id
        result.extend([{"user_id": user_id, **reading} for reading in dq])
    # optionally sort by timestamp
    result.sort(key=lambda x: x["timestamp"])
    return jsonify(result)

@bp.route("/posture/recalibrate", methods=["POST"])
def posture_recalibrate():
    db: Session = SessionLocal()
    try:
        data = request.get_json()
        print("Recalibrate request:", data)
        userId = data.get("user_id")
        user = db.query(User).filter(User.id == userId).first()

        current_angle = db.query(PostureReading).filter(PostureReading.user_id == data.get("user_id")).order_by(PostureReading.timestamp.desc()).first().angle
        if current_angle is None:
            return jsonify({"error": "User has not calibrated yet"}), 400

        user.baseline_angle = current_angle

        sessionReading = CalibrateSession(
            user_id=userId,
            baseline_angle=user.baseline_angle,
            timestamp=datetime.utcnow()
        )

        db.add(sessionReading)
        db.commit()

        return jsonify({"message": "Calibration complete", "baseline_angle": sessionReading.baseline_angle}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@bp.route("/reset", methods=["POST"])
def reset_posture():
    db: Session = SessionLocal()
    try:
        db.query(PostureReading).filter(PostureReading.timestamp >= date.today()).delete()
        db.commit()
        return jsonify({"status": "reset successful"}), 200
    finally:
        db.close()

@bp.route("/posture/toggle_tracking", methods=["POST"])
def toggle_tracking():
    global tracking_active
    action = request.json.get("action")
    if action == "start":
        tracking_active = True
    elif action == "stop":
        tracking_active = False
    return jsonify({"tracking_active": tracking_active}), 200

@bp.route("/posture", methods=["POST"])
def add_posture_reading():
    db: Session = SessionLocal()
    try:
        global tracking_active
        data = request.get_json()

        if not data or "user_id" not in data or "angle" not in data:
            return jsonify({"error": "user_id and angle are required"}), 400
        if not tracking_active:
            return jsonify({"message": "Tracking is paused"}), 400

        user_id = data["user_id"]
        angle = data["angle"]
        if not isinstance(angle, (int, float)):
            return jsonify({"error": "angle must be a number"}), 400

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        if user.baseline_angle is None:
            return jsonify({"error": "User has not calibrated yet"}), 400

        bAngle = db.query(CalibrateSession).filter(CalibrateSession.user_id == user_id).order_by(CalibrateSession.timestamp.desc()).first().baseline_angle
        if bAngle is None:
            return jsonify({"error": "User has not calibrated yet"}), 400
        
        baseline = bAngle
        diff = abs(angle - baseline)
        threshold = 10

        if diff <= threshold:
            quality_score = 5
        elif diff <= 2 * threshold:
            quality_score = 3
        else:
            quality_score = 1

        posture_label = quality_to_label(quality_score)

        posture_buffer.append({
            "user_id": user_id,
            "angle": angle,
            "quality_score": quality_score,
            "posture": posture_label,
            "timestamp": record.timestamp
        })

        

        record = PostureReading(
            user_id=user_id,
            angle=angle,
            quality_score=quality_score,
            posture=posture_label,
            timestamp=datetime.utcnow()
        )

        db.add(record)
        db.commit()

        logger.info(f"Added posture reading for user {user_id}: angle={angle}, quality_score={quality_score}")

        if user_id not in posture_buffer:
            posture_buffer[user_id] = deque(maxlen=100)
        posture_buffer[user_id].append({
            "angle": angle,
            "quality_score": quality_score,
            "posture": posture_label,
            "timestamp": record.timestamp
        })

        safe_emit_posture_update(
            "posture_update",
            {"user_id": user_id, "angle": angle, "quality_score": quality_score, "posture": posture_label},
            user_id
        )

        return jsonify({
            "status": posture_label.lower(),
            "user_id": user_id,
            "angle": angle,
            "baseline_angle": user.baseline_angle,
            "quality_score": quality_score,
            "posture": posture_label,
            "timestamp": record.timestamp.isoformat()
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
