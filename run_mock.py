"""在 PyCharm 里右键 Run 即可启动被测服务（:9000）。

如果报 Errno 10048（端口被占用），先跑同目录下的 stop.ps1。
"""
import errno
import sys

import uvicorn

if __name__ == "__main__":
    try:
        uvicorn.run("mock_server.main:app", host="127.0.0.1", port=9000, reload=False)
    except SystemExit:
        raise
    except OSError as exc:
        if getattr(exc, "errno", None) in (errno.EADDRINUSE, 10048):
            print("\n[端口被占用] 9000 上已经有服务在跑。")
            print("解决：在 PyCharm 的 Terminal 里执行  .\\stop.ps1  然后重新 Run。")
            sys.exit(1)
        raise
