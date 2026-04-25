from backend.db.database import engine
from backend.models.client import Client

def init_db():
    Client.metadata.create_all(bind=engine)