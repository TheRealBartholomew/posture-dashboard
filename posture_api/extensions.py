from flask_socketio import SocketIO
import logging

socketio = SocketIO()

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(handler)

posture_buffer = {}  # user_id -> deque of recent posture readings
