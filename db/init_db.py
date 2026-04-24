from db.database import engine
from models.client import Client

def init_db():
    Client.metadata.create_all(bind=engine)