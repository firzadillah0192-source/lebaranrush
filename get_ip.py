import socket

def get_local_ip():
    try:
        # Create a dummy socket to detect preferred outbound IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # We don't actually connect, just use the connect_ex to determine the local address
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

if __name__ == "__main__":
    print(get_local_ip())
