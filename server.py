from socket import *
from os.path import isfile

SERVER_IP = "localhost"
SERVER_PORT = 5042
STATUS_OK = "200 OK"
STATUS_MOVED = "301 Moved Permanently"
STATUS_NOTFOUND = "404 Not Found"
CONNECTION_CLOSE = "close"
LN = "\r\n"
DEFAULT_TIMEOUT = 1.0
DEFAULT_RECV_SIZE = 2048


class HTTPServer:
    def __init__(self, ip, port):
        """
        Creates a TCP server that implement the HTTP protocol.
        :param ip:
        :param port:
        """
        self.server_socket = socket(AF_INET, SOCK_STREAM)
        self.server_socket.bind((ip, port))
        self.request_parameters = {}
        self.reply_parameters = {}

    def start(self):
        """
        Start the server, waiting for connections, get HTTP requests and handle them.
        """
        self.server_socket.listen(1)
        while True:
            client_socket, client_address = self.server_socket.accept()
            try:
                while True:
                    # Initialize the request_parameters and reply_parameters before receiving new request:
                    self.request_parameters = {}
                    self.reply_parameters = {}
                    # Set a timeout for the client's socket before calling recv, as we don't multi-thread/task:
                    client_socket.settimeout(DEFAULT_TIMEOUT)
                    self.parse_request(client_socket.recv(DEFAULT_RECV_SIZE))
                    # If the request is empty we close this connection and wait for new one:
                    if not self.request_parameters:
                        client_socket.close()
                        break
                    # Else we handle the request and reply to the client.
                    self.handle_request()
                    self.reply_request(client_socket)
                    # If the request's 'Connection:' parameter is "close", we close the connection after 1 request:
                    if self.request_parameters.get("Connection:") == CONNECTION_CLOSE:
                        client_socket.close()
                        break
            except timeout:
                print("Reached the timeout for waiting for a request.")
                client_socket.close()

    def parse_request(self, request_string):
        """
        Parse a HTTP request and put it's headers into request_parameters.
        :param request_string: The string received from the client.
        """
        # Split the request string to lines, where each line is splitted to words:
        request_list = list(map(lambda x: x.split(" "), request_string.decode().split(LN)))
        # If the request wasn't empty, start splitting it to parameters:
        if len(request_list) > 0:
            # Splitting the method, requested file and protocol's name from the first line:
            self.request_parameters["Method:"] = request_list[0][0]
            self.request_parameters["Filename:"] = "files/index.html" if request_list[0][1] == "/" \
                else "files" + request_list[0][1]
            self.request_parameters["Protocol:"] = request_list[0][2]
            # For each header on the other lines, save the header as a parameter as well:
            for line in request_list[1:]:
                if len(line) > 1:
                    self.request_parameters[line[0]] = line[1]

    def handle_request(self):
        """
        Handle the HTTP request according the parsed parameters.
        implemented only 'GET' method and only statuses 200, 301 and 404.
        Fill up the reply_parameters dictionary according to the request.
        """
        if self.request_parameters["Method:"] == "GET":

            # if the file requested exists, set status to 200 and read the file:
            if isfile(self.request_parameters["Filename:"]):
                self.reply_parameters["Status:"] = STATUS_OK
                self.reply_parameters["Connection:"] = self.request_parameters["Connection:"]

                # if the file is an image or an icon, read it as a binary file:
                if self.request_parameters["Filename:"].split(".")[1] in ("ico", "jpg"):
                    with open(self.request_parameters["Filename:"], "rb") as file:
                        self.reply_parameters["File:"] = file.read()

                # else, read as a text file:
                else:
                    with open(self.request_parameters["Filename:"], "r") as file:
                        self.reply_parameters["File:"] = file.read().encode("utf-8")

            # if the file requested is "/redirect", set status to 301, and set location to "result.html"
            elif self.request_parameters["Filename:"] == "files/redirect":
                self.reply_parameters["Status:"] = STATUS_MOVED
                self.reply_parameters["Location:"] = "result.html"
                self.reply_parameters["Connection:"] = CONNECTION_CLOSE

            # if the file requested does not exists, set status to 404
            else:
                self.reply_parameters["Status:"] = STATUS_NOTFOUND
                self.reply_parameters["Connection:"] = CONNECTION_CLOSE

    def reply_request(self, client):
        """
        Creates a reply string according to the reply_parameters dictionary, and send it back to the client.
        :param client: Client's socket
        """
        # first line: Protocol + Status:
        reply = self.request_parameters["Protocol:"] + " " + self.reply_parameters["Status:"] + LN

        # second line: Connection: keep-alive / close
        reply = reply + "Connection: " + self.reply_parameters["Connection:"] + LN

        # if file exists, add the file size and the file content to the reply:
        if self.reply_parameters["Status:"] == STATUS_OK:
            reply = reply + "Content-Length: " + str(len(self.reply_parameters["File:"])) + LN + LN
            reply = reply.encode("utf-8") + self.reply_parameters["File:"] + LN.encode("utf-8")

        # if file is moved, add the new location to the reply:
        elif self.reply_parameters["Status:"] == STATUS_MOVED:
            reply = reply + "Location: " + self.reply_parameters["Location:"] + LN + LN + LN
            reply = reply.encode("utf-8")

        # if file don't exists, add a new line
        else:
            reply = reply + LN + LN + " " + LN
            reply = reply.encode("utf-8")

        # Send the reply to the client:
        client.send(reply)


server = HTTPServer(SERVER_IP, SERVER_PORT)
server.start()
