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
daemon.request
~~~~~~~~~~~~~~~~~

This module provides a Request object to manage and persist 
request settings (cookies, auth, proxies).
"""
from .dictionary import CaseInsensitiveDict

class Request():
    """The fully mutable "class" `Request <Request>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a "class" `Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import deamon.request
      >>> req = request.Request()
      ## Incoming message obtain aka. incoming_msg
      >>> r = req.prepare(incoming_msg)
      >>> r
      <Request>
    """
    __attrs__ = [
        "method",
        "url",
        "headers",
        "body",
        "reason",
        "cookies",
        "body",
        "routes",
        "hook",
    ]

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL to send the request to.
        self.url = None
        #: dictionary of HTTP headers.
        self.headers = None
        #: HTTP path
        self.path = None        
        # The cookies set used to create Cookie header
        self.cookies = None
        #: request body to send to the server.
        self.body = None
        #: Routes
        self.routes = {}
        #: Hook point for routed mapped-path
        self.hook = None

    def extract_request_line(self, request):
        try:
            lines = request.splitlines()
            first_line = lines[0]
            method, path, version = first_line.split()

            # if path == '/':
            #     path = '/index.html'
            #This will be handle in response.py for authentication
        except Exception:
            return None, None, None

        return method, path, version
             
    def prepare_headers(self, request):
        """Prepares the given HTTP headers."""
        lines = request.split('\r\n')
        headers = {}
        for line in lines[1:]:
            if ': ' in line:
                key, val = line.split(': ', 1)
                headers[key.lower()] = val
        return headers

    def prepare(self, request, routes=None):
        """Prepares the entire request with the given parameters."""

        # Prepare the request line from the request header
        self.method, self.path, self.version = self.extract_request_line(request)
        print("[Request] {} path {} version {}".format(self.method, self.path, self.version))

        self.body = self.extract_body(request)
        print(self.body)
        print("[Request] Body length: {}".format(len(self.body) if self.body else 0))

        #
        # @bksysnet Preapring the webapp hook with WeApRous instance
        # The default behaviour with HTTP server is empty routed
        #
        # TODO manage the webapp hook in this mounting point
        if routes :
            self.routes = routes
            self.hook = routes.get((self.method, self.path))
            #
            # self.hook manipulation goes here
            # ...
            #

        self.headers = self.prepare_headers(request)
        # print("========== COOKIES ==========")
        cookies = self.headers.get('Cookie', '')

        # print(cookies)
        if cookies:
            self.prepare_cookies(self.parse_cookies(cookies))
            #
            #  TODO: implement the cookie function here
            #        by parsing the header            #

        return

    def parse_cookies(self, cookie_header: str):
        cookies = {}
        parts = cookie_header.split(';')
        for p in parts:
            if '=' in p:
                name, value = p.strip().split('=', 1)
                cookies[name] = value
        return cookies

    def extract_body(self, request):
        """Extract body from HTTP request after \r\n\r\n"""
        try:
            if '\r\n\r\n' in request:
                parts = request.split('\r\n\r\n', 1)
                if len(parts) > 1:
                    return parts[1]
            return ""
        except Exception as e:
            print("[Request] Error extracting body: {}".format(e))
            return ""

    def prepare_body(self, data, files, json=None):
        """Prepare request body with proper content length and authentication."""
        
        # Set body based on input type
        if json:
            import json as json_lib
            self.body = json_lib.dumps(json)
            if self.headers is None:
                self.headers = {}
            self.headers["Content-Type"] = "application/json"
        elif data:
            self.body = data
        elif files:
            self.body = files
        else:
            self.body = ""
        
        # Calculate and set content length
        self.prepare_content_length(self.body)
        
        #
        # TODO prepare the request authentication
        #
        # If auth credentials are set, prepare the Authorization header
        if self.auth:
            self.prepare_auth(self.auth)
        
        return


    def prepare_content_length(self, body):
        """Calculate and set Content-Length header."""
        
        if self.headers is None:
            self.headers = {}
        #
        # TODO: Calculate actual content length
        #
        if body:
            if isinstance(body, str):
                # Encode to bytes to get accurate length
                content_length = len(body.encode('utf-8'))
            elif isinstance(body, bytes):
                content_length = len(body)
            else:
                content_length = len(str(body))
            
            self.headers["Content-Length"] = str(content_length)
        else:
            self.headers["Content-Length"] = "0"
        
        return

    def prepare_auth(self, auth, url=""):
        """
        Prepare Basic Authentication header.
        
        :param auth: tuple of (username, password)
        :param url: optional URL (for future use)
        """
        #
        # TODO prepare the request authentication
        #
        if auth and isinstance(auth, tuple) and len(auth) == 2:
            import base64
            username, password = auth
            
            # Create credentials string: "username:password"
            credentials = "{}:{}".format(username, password)
            
            # Encode to base64
            encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            
            # Set Authorization header
            if self.headers is None:
                self.headers = {}
            
            self.headers["Authorization"] = "Basic {}".format(encoded)
            self.auth = auth
            
            print("[Request] Authorization header set for user: {}".format(username))
        
        return

    def prepare_cookies(self, cookies):
            self.headers["Cookie"] = cookies
