import os
from dotenv import load_dotenv
load_dotenv()
from src.config import Config

try:
    g = Config.get_neo4j_graph()
    print("Neo4j Schema:", g.schema)
    print("Connected successfully!")
except Exception as e:
    import traceback
    traceback.print_exc()
