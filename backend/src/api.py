import os
from dotenv import load_dotenv
import redis

load_dotenv()

host = os.getenv("REDIS_HOST")
port = int(os.getenv("REDIS_PORT"))
password = os.getenv("REDIS_PASSWORD")

r = redis.Redis(host=host, port=port, password=password, db=0)

print(r.ping())  # True se conectado
