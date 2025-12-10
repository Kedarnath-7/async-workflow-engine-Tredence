import sys
import os

print("Verifying WebSocket Implementation...")

checks = [
    ("websockets in requirements.txt", lambda: "websockets" in open("requirements.txt").read()),
    ("websocket_manager.py exists", lambda: os.path.exists("app/core/websocket_manager.py")),
    ("WebSocket endpoint in routes.py", lambda: "/ws/run/" in open("app/api/routes.py").read()),
    ("Broadcasting in engine.py", lambda: "ws_manager.broadcast" in open("app/core/engine.py").read()),
    ("Documentation in README.md", lambda: "WebSocket" in open("README.md").read()),
    ("Client example exists", lambda: os.path.exists("examples/websocket_client_example.py")),
    ("Test script exists", lambda: os.path.exists("tests/test_websocket.py"))
]

passed_count = 0
for name, check_func in checks:
    try:
        if check_func():
            print(f"[OK] {name}")
            passed_count += 1
        else:
            print(f"[FAIL] {name}")
    except Exception as e:
        print(f"[ERR] {name}: {e}")

print(f"\nResult: {passed_count}/{len(checks)} checks passed.")

if passed_count == len(checks):
    sys.exit(0)
else:
    sys.exit(1)
