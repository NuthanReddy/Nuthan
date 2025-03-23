import socket


def start_echo_server(host='localhost', port=12345):
    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)  # Start listening for incoming connections
    print(f"Echo server started on {host}:{port}")

    try:
        while True:
            # Accept incoming connections
            client_socket, client_address = server_socket.accept()
            print(f"Connection established with {client_address}")

            # Receive data and echo it back
            data = client_socket.recv(1024)
            if data:
                print(f"Received: {data.decode('utf-8')}")
                client_socket.sendall(data)  # Echo back the received data

            # Close the client connection
            client_socket.close()
    except KeyboardInterrupt:
        print("\nShutting down the server...")
    finally:
        server_socket.close()


# Run the echo server
if __name__ == '__main__':
    start_echo_server()
