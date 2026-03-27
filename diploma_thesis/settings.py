import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

NIH_EMAIL = os.getenv("NIH_EMAIL")

E_INFRA_API_KEY = os.getenv("E_INFRA_API_KEY")

PACKAGE_DIR = Path(__file__).parent  # = your/home/directory/diploma_thesis/diploma_thesis
DATA_DIR = PACKAGE_DIR / "data"

MODEL_NAME = "gpt-oss-120b"

EINFRA_URL = "https://llm.ai.e-infra.cz/v1/"

logging.basicConfig(
 level=logging.INFO,
 format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
 handlers=[logging.StreamHandler()]
)
#
# logging.basicConfig(
#  filename=DATA_DIR / f"diploma_thesis_{round(time.time())}.log",
#  filemode="w",
#  level=logging.INFO,
#  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )

logger = logging.getLogger("diploma_thesis")
