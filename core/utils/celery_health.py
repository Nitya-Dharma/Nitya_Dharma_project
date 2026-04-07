import socket


def is_redis_available(host="redis", port=6379, timeout=1):
    try:
        sock = socket.create_connection((host, port), timeout)
        sock.close()
        return True
    except Exception:
        return False

