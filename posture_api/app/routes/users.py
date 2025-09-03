from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import User

bp = Blueprint("users", __name__, url_prefix="/api")

@bp.route("/users", methods=["POST"])
def create_user():
    db: Session = SessionLocal()
    try:
        data = request.get_json()
        if not data or "name" not in data:
            return jsonify({"error": "name is required"}), 400

        name = data["name"].strip()
        if not name:
            return jsonify({"error": "name cannot be empty"}), 400
        
        user = User(name=name)
        db.add(user)
        db.commit()
        db.refresh(user)
        return jsonify({"status": "created",
            "user_id": user.id,
            "name": user.name,
            "baseline_angle": user.baseline_angle,
            "created_at": user.created_at.isoformat()
        }), 201
    
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()



@bp.route("/users", methods=["GET"])
def list_users():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        users_list = [
            {
                "user_id": u.id,
                "name": u.name,
                "baseline_angle": u.baseline_angle,
                "created_at": u.created_at.isoformat()
            } for u in users
        ]
        return jsonify(users_list), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id: int):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({
            "user_id": user.id,
            "name": user.name,
            "baseline_angle": user.baseline_angle,
            "created_at": user.created_at.isoformat()
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
