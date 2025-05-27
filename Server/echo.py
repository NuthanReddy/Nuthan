import socket


def start_http_server(host='localhost', port=8080):
    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)  # Start listening for incoming connections
    print(f"HTTP server started on {host}:{port}")

    try:
        while True:
            # Accept an incoming connection
            client_socket, client_address = server_socket.accept()
            print(f"Connection established with {client_address}")

            # Receive request data
            request_data = client_socket.recv(1024).decode('utf-8')
            print(f"Request:\n{request_data}")

            # Send a simple HTTP response
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 13\r\n"
                "\r\n"
                "Hello, World!"
            )
            client_socket.sendall(response.encode('utf-8'))

            # Close the client connection
            client_socket.close()
    except KeyboardInterrupt:
        print("\nShutting down the server...")
    finally:
        server_socket.close()


# Run the HTTP server
if __name__ == '__main__':
    start_http_server()
