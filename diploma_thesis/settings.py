import logging
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

if os.environ.get("RUNNING_IN_DOCKER") == "1":
    NEO4J_URI = "neo4j://neo4j-db:7687"
else:
    NEO4J_URI = "neo4j://127.0.0.1:7687"

NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")

PACKAGE_DIR = Path(__file__).parent  # = your/home/directory/diploma_thesis/diploma_thesis
DATA_DIR = PACKAGE_DIR / "data"

logging.basicConfig(
 level=logging.INFO,
 format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
 handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("diploma_thesis")
logger.setLevel(logging.INFO)
