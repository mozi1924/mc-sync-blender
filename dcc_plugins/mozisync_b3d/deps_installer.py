import sys
import subprocess
import logging

logger = logging.getLogger("Mozisync")

def is_websockets_installed() -> bool:
    try:
        import websockets
        return True
    except ImportError:
        return False

def install_websockets() -> bool:
    logger.info("Attempting to install 'websockets' module into Blender's Python environment...")
    python_binary = sys.executable
    try:
        # 运行 pip install websockets
        cmd = [python_binary, "-m", "pip", "install", "websockets"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info(f"Successfully installed websockets:\n{result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install websockets: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error during websockets installation: {e}")
        return False
