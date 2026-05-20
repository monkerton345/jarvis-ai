"""J.A.R.V.I.S. — Just A Rather Very Intelligent System"""
from .core import Jarvis
from .config import load_config, JarvisConfig

__version__ = "1.0.0"
__all__ = ["Jarvis", "load_config", "JarvisConfig"]
