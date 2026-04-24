from db.database import SessionLocal
from models.client import Client

def get_client(client_id):
    db = SessionLocal()
    try:
        return db.query(Client).filter(Client.id == client_id).first()
    finally:
        db.close()