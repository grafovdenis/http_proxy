#!/usr/bin/python
import socket

# For compressing
from io import BytesIO
from PIL import Image


MAX_IMG_SIZE = (128, 128)


def image_to_bytes(image):
    imgByteArr = BytesIO()
    image.save(imgByteArr, format=image.format)
    imgByteArr = imgByteArr.getvalue()
    return imgByteArr


def headers_to_string(headers):
    return ''.join(map(lambda key: "%s: %s\r\n" % (key, headers[key]), headers))


class HttpMessage:
    def method(self):
        if self.type == "request":
            return self.first_line.split(' ')[0]
        else:
            return None

    def __init__(self, firstLine, headers, data, type):
        self.first_line = firstLine
        self.headers = headers
        self.data = data
        self.type = type

    def bytes(self):
        raw_headers = headers_to_string(self.headers).encode()
        return b''.join([self.first_line.encode(), b'\r\n', raw_headers, b'\r\n', self.data, b'\r\n'])


def parse_header(data):
    lines = data.split('\r\n')
    isRequest = False
    if len(lines[0].split()) != 0 and lines[0].split()[0] == "GET":
        isRequest = True
    headers = {}
    for line in lines[1:]:
        if line != '':
            line_args = line.split(': ')
            headers[line_args[0]] = line_args[1]
    return (lines[0], headers, isRequest)


def read_bytes(sock):
    response_head_buffer = b''
    while True:
        byte = sock.recv(1)
        response_head_buffer += byte
        if len(response_head_buffer) == 0:
            break
        if response_head_buffer[-1] == 10 \
                and response_head_buffer[-2] == 13 \
                and response_head_buffer[-3] == 10 \
                and response_head_buffer[-4] == 13:
            break
    (first_line, headers, isRequest) = parse_header(
        response_head_buffer.decode())
    data = b''
    if 'Content-Length' in headers.keys():
        while int(headers['Content-Length']) > len(data):
            data += sock.recv(int(headers['Content-Length']))
    return HttpMessage(first_line, headers, data, "request" if isRequest else "response")


def main():
    # Create a TCP socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Re-use the socket
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('', 8080))

    server_sock.listen(1000)  # become a server socket

    while True:
        # Establish the connection
        client_sock = server_sock.accept()[0]

        request = read_bytes(client_sock)

        # Connect to remote host
        host_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        host_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if 'Host' in request.headers.keys():
            try:
                host_sock.connect((request.headers['Host'], 80))
            except Exception:
                print("Can't connect")
                continue
        else:
            print("Can't find Host in headers")
            continue

        # send request
        if (request.method() == "GET"):
            host_sock.send(request.bytes())
            print(request.first_line)

        # read response
        response = read_bytes(host_sock)
        host_sock.close()

        # compress image
        if 'Content-Type' in response.headers.keys():
            if response.headers['Content-Type'] == "image/png" \
                    or response.headers['Content-Type'] == "image/jpeg" \
                or response.headers['Content-Type'] == "image/jpg"\
                    or response.headers['Content-Type'] == "image/gif":
                img = Image.open(BytesIO(response.data))
                if img.size[0] > MAX_IMG_SIZE[0] or img.size[1] > MAX_IMG_SIZE[1]:
                    try:
                        img.thumbnail(MAX_IMG_SIZE)
                        print("img compressed")
                    except ZeroDivisionError:
                        pass
                    response.data = image_to_bytes(img)
                    response.headers['Content-Length'] = len(response.data)

        # send result
        client_sock.send(response.bytes())
        client_sock.close()


if __name__ == '__main__':
    main()
