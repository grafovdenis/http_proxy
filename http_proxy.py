from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from http import client
import requests

from io import BytesIO
from PIL import Image

MAX_IMG_SIZE = (128, 128)

def image_to_bytes(image):
    imgByteArr = BytesIO()
    image.save(imgByteArr, format=image.format)
    imgByteArr = imgByteArr.getvalue()
    return imgByteArr

class CompressingHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        _url = self.path
        _headers = self.headers
        try:
            _response = requests.get(_url, headers=_headers)
            _response.encoding = _response.apparent_encoding
            if _response.content is not None:
                self.send_response(_response.status_code)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                if (_headers.get('Accept') == "image/webp,*/*"):
                    try:
                        img = Image.open(BytesIO(_response.content))
                        if img.size[0] > MAX_IMG_SIZE[0] or img.size[1] > MAX_IMG_SIZE[1]:
                            try:
                                img.thumbnail(MAX_IMG_SIZE)
                                print("img compressed")
                            except ZeroDivisionError:
                                pass
                        _modified_img = image_to_bytes(img)
                        self.send_header('Content-Length', len(_modified_img))
                        self.wfile.write(_modified_img)
                    except Exception:
                        pass
                else:
                    self.wfile.write(_response.content)
            else:
                self._send_bad_client_response()
        except requests.exceptions.TooManyRedirects:
            pass

    def do_CONNECT(self):
        self.send_response(200)
        self.end_headers()
        print('localhost connected')

    def _send_bad_client_response(self):
        self.send_response(200)
        self.send_header('content-type', 'text/html')
        self.end_headers()
        self.wfile.write("Can't process your response")


def run(server_class=HTTPServer, handler_class=CompressingHTTPRequestHandler):
    server_address = ('', 8080)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()


if __name__ == "__main__":
    run()
