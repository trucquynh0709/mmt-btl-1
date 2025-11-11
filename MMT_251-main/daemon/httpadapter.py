#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.httpadapter
~~~~~~~~~~~~~~~~~

This module provides a http adapter object to manage and persist 
http settings (headers, bodies). The adapter supports both
raw URL paths and RESTful route definitions, and integrates with
Request and Response objects to handle client-server communication.
"""

from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict

class HttpAdapter:
    """
    A mutable :class:`HTTP adapter <HTTP adapter>` for managing client connections
    and routing requests.

    The `HttpAdapter` class encapsulates the logic for receiving HTTP requests,
    dispatching them to appropriate route handlers, and constructing responses.
    It supports RESTful routing via hooks and integrates with :class:`Request <Request>` 
    and :class:`Response <Response>` objects for full request lifecycle management.

    Attributes:
        ip (str): IP address of the client.
        port (int): Port number of the client.
        conn (socket): Active socket connection.
        connaddr (tuple): Address of the connected client.
        routes (dict): Mapping of route paths to handler functions.
        request (Request): Request object for parsing incoming data.
        response (Response): Response object for building and sending replies.
    """

    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Initialize a new HttpAdapter instance.

        :param ip (str): IP address of the client.
        :param port (int): Port number of the client.
        :param conn (socket): Active socket connection.
        :param connaddr (tuple): Address of the connected client.
        :param routes (dict): Mapping of route paths to handler functions.
        """

        #: IP address.
        self.ip = ip
        #: Port.
        self.port = port
        #: Connection
        self.conn = conn
        #: Conndection address
        self.connaddr = connaddr
        #: Routes
        self.routes = routes
        #: Request
        self.request = Request()
        #: Response
        self.response = Response()

    def handle_client(self, conn, addr, routes):
        # --- Connection setup ---
        self.conn = conn        
        self.connaddr = addr
        req = self.request
        resp = self.response

        try:
            msg = conn.recv(4096).decode()
        except Exception as e:
            print("[HttpAdapter] Failed to receive/decode message:", e)
            conn.close()
            return

        if not msg or not msg.strip():
            print("[HttpAdapter] Empty request received, closing connection")
            conn.close()
            return

        req.prepare(msg, routes)

        if req.method is None or req.path is None:
            print("[HttpAdapter] Invalid request - failed to parse")
            response = (
                "HTTP/1.1 400 Bad Request\r\n"
                "Content-Type: text/html\r\n"
                "Content-Length: 15\r\n"
                "\r\n"
                "400 Bad Request"
            ).encode()
            conn.sendall(response)
            conn.close()
            return

        print(f"[HttpAdapter] {req.method} {req.path}")

        # --- CORS Preflight (must come before any other logic) ---
        if req.method == "OPTIONS":
            print("[HttpAdapter] Handling OPTIONS preflight request")
            # Send CORS preflight response
            preflight_response = (
                "HTTP/1.1 204 No Content\r\n"
                "Access-Control-Allow-Origin: *\r\n"
                "Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\r\n"
                "Access-Control-Allow-Headers: Content-Type, Authorization\r\n"
                "Access-Control-Max-Age: 86400\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).encode()
            conn.sendall(preflight_response)
            conn.close()
            return

        # --- Route Handling ---
        if req.hook:
            print("[HttpAdapter] Matched route:", req.hook._route_path)

            try:
                result = req.hook(headers=str(req.headers), body=req.body)
                resp._content = result if result else ""
            except Exception as e:
                print(f"[HttpAdapter] Error executing route: {e}")
                resp.status_code = 500
                resp.reason = "Internal Server Error"
                resp._content = f'{{"status":"error","message":"{str(e)}"}}'

        # --- Final Response ---
        try:
            response = resp.build_response(req)
            conn.sendall(response)
        except Exception as e:
            print(f"[HttpAdapter] Error building response: {e}")
        finally:
            conn.close()


    #@property
    def extract_cookies(self, req, resp):
        """
        Build cookies from the :class:`Request <Request>` headers.

        :param req:(Request) The :class:`Request <Request>` object.
        :param resp: (Response) The res:class:`Response <Response>` object.
        :rtype: cookies - A dictionary of cookie key-value pairs.
        """
        cookies = {}
        for header in cookies.headers:
            if header.startswith("Cookie:"):
                cookie_str = header.split(":", 1)[1].strip()
                for pair in cookie_str.split(";"):
                    key, value = pair.strip().split("=")
                    cookies[key] = value
        return cookies
    
    def add_headers(self, request):
        """
        Add headers to the request.

        This method is intended to be overridden by subclasses to inject
        custom headers. It does nothing by default.

        
        :param request: :class:`Request <Request>` to add headers to.
        """
        pass

    def build_proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. 

        :class:`HttpAdapter <HttpAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        :rtype: dict
        """
        headers = {}
        #
        # TODO: build your authentication here
        #       username, password =...
        # we provide dummy auth here
        #
        # username, password = ("user1", "password")

        # if username:
        #     headers["Proxy-Authorization"] = (username, password)

        # return headers
        from urllib.parse import urlparse
        try:
            parsed = urlparse(proxy)
            username = parsed.username if parsed.username else "user1"
            password = parsed.password if parsed.password else "password"
        except:
            username,password = ("user1","password")
        
        headers["Proxy-Authorization"] = (username, password)
        return headers