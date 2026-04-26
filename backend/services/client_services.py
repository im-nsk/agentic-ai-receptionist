from backend.db.database import SessionLocal
from backend.models.client import Client

def get_client(client_id):
    db = SessionLocal()
    try:
        if not client_id:
            return None

        return db.query(Client).filter(Client.id == client_id).first()

    finally:
        db.close()