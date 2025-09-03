from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session 
from sqlalchemy import func
from datetime import datetime
from app.db import SessionLocal
from app.models import PostureReading, User

bp = Blueprint("stats", __name__, url_prefix="/api")

@bp.route("/stats", methods=["GET"])
def get_stats():
    db: Session = SessionLocal()
    try:
        user_id = request.args.get("user_id", type=int)
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")


        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        query = db.query(PostureReading).filter(PostureReading.user_id == user_id)

        if start_date:
            query = query.filter(PostureReading.timestamp >= datetime.fromisoformat(start_date))

        if end_date:
            query = query.filter(PostureReading.timestamp <= datetime.fromisoformat(end_date))

        readings = query.all()
        if not readings:
            return jsonify({"message": "No posture readings found for the given criteria"}), 404

        avg_angle = query.with_entities(func.avg(PostureReading.angle)).scalar()
        avg_quality = query.with_entities(func.avg(PostureReading.quality_score)).scalar()
        total_readings = query.count()
        worst = query.order_by(PostureReading.quality_score.asc()).first()

        return jsonify({
           "user_id": user_id,
            "summary": {
                "average_angle": round(avg_angle, 2) if avg_angle else None,
                "average_quality": round(avg_quality, 2) if avg_quality else None,
                "total_readings": total_readings,
                "worst_posture": {
                    "angle": worst.angle if worst else None,
                    "quality_score": worst.quality_score if worst else None,
                    "timestamp": worst.timestamp.isoformat() if worst else None
                }
            }
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        db.close()


