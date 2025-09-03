
from app.db import SessionLocal
from flask import Blueprint, request, jsonify
from datetime import datetime
from app.models import PostureReading


bp = Blueprint("overview", __name__, url_prefix="/api")

@bp.route("/overview", methods=["GET"])
def daily_overview():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return {"error": "user_id is required"}, 400

    db = SessionLocal()
    try:
        today = datetime.utcnow().date()
        start_dt = datetime.combine(today, datetime.min.time())
        end_dt = datetime.combine(today, datetime.max.time())

        readings = db.query(PostureReading).filter(
            PostureReading.user_id == user_id,
            PostureReading.timestamp >= start_dt,
            PostureReading.timestamp <= end_dt
        ).all()

        if not readings:
            return jsonify({"message":" no readings available"}), 200

        angles = [r.angle for r in readings]
        quality_counts = {"good":0, "warning":0, "bad":0}
        for a in angles:
            if a < 15: quality_counts["good"] += 1
            elif a < 30: quality_counts["warning"] += 1
            else: quality_counts["bad"] += 1

        avg_angle = sum(angles) / len(angles) if angles else 0

        timeline = [{"timestamp": r.timestamp.isoformat(), "angle": r.angle} for r in readings]

        return jsonify({
            "avg_angle": avg_angle,
            "timeline": timeline,
            "quality_counts": quality_counts
        })
    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        db.close()