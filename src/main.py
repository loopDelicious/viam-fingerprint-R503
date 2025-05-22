import asyncio
from viam.module.module import Module
try:
    from models.adafruit_r503 import AdafruitR503
except ModuleNotFoundError:
    # when running as local module with run.sh
    from .models.adafruit_r503 import AdafruitR503


if __name__ == '__main__':
    asyncio.run(Module.run_from_registry())
