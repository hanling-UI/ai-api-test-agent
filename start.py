"""容器入口：先起被测服务（内部 9000），再起应用（$PORT）。

这样部署一个服务就够——演示时不用再单独部署 mock。
"""
import os
import subprocess
import sys
import time

INTERNAL_MOCK_PORT = os.getenv("MOCK_PORT", "9000")
APP_PORT = os.getenv("PORT", "8000")

os.environ.setdefault("TARGET_BASE_URL", f"http://127.0.0.1:{INTERNAL_MOCK_PORT}")

mock = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "mock_server.main:app",
     "--host", "127.0.0.1", "--port", INTERNAL_MOCK_PORT],
    stdout=sys.stdout, stderr=sys.stderr,
)
time.sleep(2)

print(f"[start] 应用启动于 :{APP_PORT}，被测服务在 :{INTERNAL_MOCK_PORT}", flush=True)
try:
    os.execv(sys.executable, [
        sys.executable, "-m", "uvicorn", "main:app",
        "--host", "0.0.0.0", "--port", APP_PORT,
    ])
finally:
    mock.terminate()
