import json
import logging

import oracledb

from app import config
from loaders import migrate_and_load

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

with oracledb.connect(user=config.ORACLE_USER, password=config.ORACLE_PASSWORD, dsn=config.ORACLE_DSN) as conn:
    print(json.dumps(migrate_and_load(conn), indent=2))
