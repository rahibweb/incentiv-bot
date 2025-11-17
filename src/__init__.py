__version__ = "2.0.0"
__author__ = "Rey"

from src.bot import IncentivBot
from src.register_existing import Register
from database import Database
from src.logger import logger
from src.captcha import CaptchaSolver
from src import utils

__all__ = [
    'IncentivBot',
    'Register',
    'Database',
    'logger',
    'CaptchaSolver',
    'utils'
]
