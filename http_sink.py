"""
这个脚本创建了一个简单的HTTP服务器,监听4000端口,接收POST请求并打印接收到的数据大小。它支持两种常见的传输方式:
1. Content-Length:当请求头中包含Content-Length时,服务器根据该值读取
   指定长度的数据。
   2. Chunked Transfer Encoding:当请求头中包含Transfer-Encoding: chunked时,
   服务器按照chunked编码的方式读取数据,直到遇到一个大小为0的chunk。
   使用方法：
   1. 运行此脚本,服务器将开始监听4000端口。
   2. 发送POST请求到http://localhost:4000,包含要发送的数据。
   3. 服务器将打印接收到的数据大小,并返回200 OK响应。
   注意事项：
   - 这个服务器仅用于测试和调试目的，不适合生产环境使用。
   - 确保在发送请求时正确设置Content-Length或Transfer-Encoding头,以便服务器能够正确处理数据。
   - 服务器将持续运行，直到手动停止它。
"""
from http.server import HTTPServer, BaseHTTPRequestHandler


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        transfer_encoding = self.headers.get("Transfer-Encoding", "")
        content_length = self.headers.get("Content-Length")

        if content_length:
            data = self.rfile.read(int(content_length))
        elif "chunked" in transfer_encoding.lower():
            # Read chunked transfer encoding manually
            data = b""
            while True:
                line = self.rfile.readline().strip()
                chunk_size = int(line, 16)
                if chunk_size == 0:
                    self.rfile.readline()  # trailing CRLF
                    break
                data += self.rfile.read(chunk_size)
                self.rfile.readline()  # chunk-ending CRLF
        else:
            # No content-length and not chunked — read what's available
            data = self.rfile.read()

        print(f"Received {len(data)} bytes")
        self.send_response(200)
        self.end_headers()


if __name__ == "__main__":
    print("HTTP sink listening on port 4000...")
    HTTPServer(("", 4000), Handler).serve_forever()
