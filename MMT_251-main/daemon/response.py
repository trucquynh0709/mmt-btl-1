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
daemon.response
~~~~~~~~~~~~~~~~~

This module provides a :class: `Response <Response>` object to manage and persist 
response settings (cookies, auth, proxies), and to construct HTTP responses
based on incoming requests. 

The current version supports MIME type detection, content loading and header formatting
"""
import datetime
import os
import mimetypes
from .dictionary import CaseInsensitiveDict

BASE_DIR = ""

UNAUTHORIZED_PAGE = """
        <!DOCTYPE html>
        <html>
        <head><title>401 Unauthorized</title></head>
        <body>
        <h1>401 Unauthorized</h1>
        <p>Invalid username or password.</p>
        </body>
        </html>
    """

class Response():   
    """The :class:`Response <Response>` object, which contains a
    server's response to an HTTP request.

    Instances are generated from a :class:`Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    :class:`Response <Response>` object encapsulates headers, content, 
    status code, cookies, and metadata related to the request-response cycle.
    It is used to construct and serve HTTP responses in a custom web server.

    :attrs status_code (int): HTTP status code (e.g., 200, 404).
    :attrs headers (dict): dictionary of response headers.
    :attrs url (str): url of the response.
    :attrsencoding (str): encoding used for decoding response content.
    :attrs history (list): list of previous Response objects (for redirects).
    :attrs reason (str): textual reason for the status code (e.g., "OK", "Not Found").
    :attrs cookies (CaseInsensitiveDict): response cookies.
    :attrs elapsed (datetime.timedelta): time taken to complete the request.
    :attrs request (PreparedRequest): the original request object.

    Usage::

      >>> import Response
      >>> resp = Response()
      >>> resp.build_response(req)
      >>> resp
      <Response>
    """

    __attrs__ = [
        "_content",
        "_header",
        "status_code",
        "method",
        "headers",
        "url",
        "history",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
        "request",
        "body",
        "reason",
    ]


    def __init__(self, request=None):
        """
        Initializes a new :class:`Response <Response>` object.

        : params request : The originating request object.
        """

        self._content = False
        self._content_consumed = False
        self._next = None

        #: Integer Code of responded HTTP Status, e.g. 404 or 200.
        self.status_code = None

        #: Case-insensitive Dictionary of Response Headers.
        #: For example, ``headers['content-type']`` will return the
        #: value of a ``'Content-Type'`` response header.
        self.headers = {}

        #: URL location of Response.
        self.url = None

        #: Encoding to decode with when accessing response text.
        self.encoding = None

        #: A list of :class:`Response <Response>` objects from
        #: the history of the Request.
        self.history = []

        #: Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".
        self.reason = None

        #: A of Cookies the response headers.
        self.cookies = CaseInsensitiveDict()

        #: The amount of time elapsed between sending the request
        self.elapsed = datetime.timedelta(0)

        #: The :class:`PreparedRequest <PreparedRequest>` object to which this
        #: is a response.
        self.request = None


    def get_mime_type(self, path):
        """
        Determines the MIME type of a file based on its path.

        "params path (str): Path to the file.

        :rtype str: MIME type string (e.g., 'text/html', 'image/png').
        """

        try:
            mime_type, _ = mimetypes.guess_type(path)
        except Exception:
            return 'application/octet-stream'
        return mime_type or 'application/octet-stream'

    def prepare_content_type(self, mime_type='text/html'):
        """
        Prepares the Content-Type header and determines the base directory
        for serving the file based on its MIME type.

        :params mime_type (str): MIME type of the requested resource.
        :rtype str: Base directory path for locating the resource.
        :raises ValueError: If the MIME type is unsupported.
        """

        base_dir = ""

        # Split MIME type into main/sub parts
        main_type, sub_type = mime_type.split('/', 1)
        print("[Response] processing MIME main_type={} sub_type={}".format(main_type, sub_type))

        if main_type == 'text':
            self.headers['Content-Type'] = 'text/{}'.format(sub_type)

            # === TEXT FILES ===
            if sub_type in ['plain', 'css', 'csv', 'xml']:
                base_dir = BASE_DIR + "static/"
            elif sub_type == 'html':
                base_dir = BASE_DIR + "www/"
            else:
                handle_text_other(sub_type)

        elif main_type == 'image':
            # === IMAGE FILES ===
            self.headers['Content-Type'] = 'image/{}'.format(sub_type)
            base_dir = BASE_DIR + "static/"

        elif main_type == 'application':
            # === APPLICATION FILES ===
            self.headers['Content-Type'] = 'application/{}'.format(sub_type)
            if sub_type in ['json', 'xml', 'zip', 'pdf']:
                base_dir = BASE_DIR + "apps/"
            else:
                base_dir = BASE_DIR + "static/apps/"

        elif main_type == 'video':
            # === VIDEO FILES ===
            self.headers['Content-Type'] = 'video/{}'.format(sub_type)
            base_dir = BASE_DIR + "static/videos/"

        elif main_type == 'audio':
            # === AUDIO FILES (optional) ===
            self.headers['Content-Type'] = 'audio/{}'.format(sub_type)
            base_dir = BASE_DIR + "static/audio/"

        else:
            # Unsupported MIME type
            raise ValueError("Invalid MIME type: main_type={} sub_type={}".format(main_type, sub_type))

        return base_dir


    def build_content(self, path, base_dir):
        """
        Loads the objects file from storage space.

        :params path (str): relative path to the file.
        :params base_dir (str): base directory where the file is located.

        :rtype tuple: (int, bytes) representing content length and content data.
        """

        filepath = os.path.join(base_dir, path.lstrip('/'))

        print("[Response] serving the object at location {}".format(filepath))
            #
            #  TODO: implement the step of fetch the object file
            #        store in the return value of content
            #
        with open(filepath,"rb") as f:
            content = f.read()
        return len(content), content


    def build_response_header(self, request):
        """
        Constructs the HTTP response headers based on the class:`Request <Request>
        and internal attributes.

        :params request (class:`Request <Request>`): incoming request object.

        :rtypes bytes: encoded HTTP response header.
        """
         # --- Status line ---
        self.status_code = self.status_code or 200
        self.reason = self.reason or "OK"
        status_line = f"HTTP/1.1 {self.status_code} {self.reason}\r\n"

        reqhdr = request.headers
        rsphdr = self.headers

        #Build dynamic headers
        headers = {
                "Accept": "{}".format(reqhdr.get("Accept", "application/json")),
                "Accept-Language": "{}".format(reqhdr.get("Accept-Language", "en-US,en;q=0.9")),
                "Authorization": "{}".format(reqhdr.get("Authorization", "Basic <credentials>")),
                'Access-Control-Allow-Origin': "*",
                'Access-Control-Allow-Methods':'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers':'Content-Type',
                "Cache-Control": "no-cache",
                "Content-Type": "{}".format(self.headers['Content-Type']),
                "Content-Length": "{}".format(len(self._content)),
                "Date": "{}".format(datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")),
                "Max-Forward": "10",
                "Pragma": "no-cache",
                "Proxy-Authorization": "Basic dXNlcjpwYXNz",  # example base64
                "Warning": "199 Miscellaneous warning",
                "User-Agent": "{}".format(reqhdr.get("User-Agent", "Chrome/123.0.0.0")),
            }

        # Header text alignment
            #
            #  TODO: implement the header building to create formated
            #        header from the provied headers
            #
        #
        # TODO prepare the request authentication
        if hasattr(self,"_set_auth_cookie") and self._set_auth_cookie:
            headers["Set-Cookie"] = "auth=true; Path=/; HttpOnly"
    
        header_lines = [f"{k}: {v}" for k, v in headers.items()]
        formatted = status_line + "\r\n".join(header_lines) + "\r\n\r\n"
        return formatted.encode("utf-8")


    def build_notfound(self):
        """
        Constructs a standard 404 Not Found HTTP response.

        :rtype bytes: Encoded 404 response.
        """

        return (
                "HTTP/1.1 404 Not Found\r\n"
                "Accept-Ranges: bytes\r\n"
                "Content-Type: text/html\r\n"
                "Content-Length: 13\r\n"
                "Cache-Control: max-age=86000\r\n"
                "Connection: close\r\n"
                "\r\n"
                "404 Not Found"
            ).encode('utf-8')

    def build_response(self, request):
        # Check if we have dynamic content from WeApRous route
        if self._content:
            if isinstance(self._content, bytes) and self._content.startswith(b"HTTP/1.1"):
                print("[Response] Detected pre-built HTTP response; sending as-is")
                return self._content
            print("[Response] Building dynamic response for {} {}".format(request.method, request.path))
            if 'Content-Type' not in self.headers:
                self.headers['Content-Type'] = 'application/json'

            #self.headers['Content-Type'] = 'application/json'
            _content = self._content.encode('utf-8') if isinstance(self._content, str) else self._content
            _header = self.build_response_header(request)
            return _header + _content
        
        print("Content from request not found!")
        

        path = request.path
        set_auth_cookie = False  # Flag to control cookie setting
        
        
        if path == "/login" or path == "/":
            cookie_header = request.headers.get('cookie', '')
            cookies = {}
            for item in cookie_header.split(';'):
                if '=' in item:
                    k, v = item.strip().split('=', 1)
                    cookies[k] = v
            
            authenticated = False
            
            # Check existing cookie
            if cookies.get('auth') == 'true':
                authenticated = True
                print("Authenticated from cookie")
            
            # Check POST credentials
            elif request.method == "POST" and request.body:
                import urllib.parse
                try:
                    credential = urllib.parse.parse_qs(request.body)
                    username = credential.get("username", [""])[0]
                    password = credential.get("password", [""])[0]
                    
                    if username == "admin" and password == "password":
                        authenticated = True
                        set_auth_cookie = True  # Only set cookie on successful login
                        print("Authenticated from credentials")
                    else:
                        return (
                            "HTTP/1.1 401 Unauthorized\r\n"
                            "Content-Type: text/html; charset=utf-8\r\n"
                            f"Content-Length: {len(UNAUTHORIZED_PAGE.encode())}\r\n"
                            "Connection: close\r\n"
                            "\r\n"
                            f"{UNAUTHORIZED_PAGE}"
                        ).encode()
                except:
                    pass
            
            if authenticated:
                path = "/index.html"
            else:
                path = '/login.html'
        
        # Store the flag in response object so build_response_header can use it
        self._set_auth_cookie = set_auth_cookie
        
            # Detect MIME type automatically
        mime_type = self.get_mime_type(path)
        print("[Response] {} path {} mime_type {}".format(request.method, request.path, mime_type))

        base_dir = ""

        # --- Handle text/html ---
        if path.endswith('.html') or mime_type == 'text/html':
            base_dir = self.prepare_content_type(mime_type='text/html')

        # --- Handle CSS ---
        elif mime_type == 'text/css':
            base_dir = self.prepare_content_type(mime_type='text/css')

        # --- Handle images ---
        elif mime_type and mime_type.startswith('image/'):
            base_dir = self.prepare_content_type(mime_type=mime_type)

        # --- Handle JavaScript ---
        elif mime_type in ['application/javascript', 'text/javascript']:
            base_dir = self.prepare_content_type(mime_type='application/javascript')

        # --- Handle JSON ---
        elif mime_type == 'application/json':
            base_dir = self.prepare_content_type(mime_type='application/json')

        # --- Handle video or audio files ---
        elif mime_type.startswith('video/') or mime_type.startswith('audio/'):
            base_dir = self.prepare_content_type(mime_type=mime_type)

        # --- Unsupported type or not found ---
        else:
            print(f"[Response] Unsupported MIME or file not found: {mime_type}")
            return self.build_notfound()

        try:
            # Read and attach content
            c_len, self._content = self.build_content(path, base_dir)
            self._header = self.build_response_header(request)
            
            print("========== RAW RESPONSE ==========")
            if not  mime_type.startswith('image/'):
                print((self._header+self._content).decode())
            else: 
                print("image type so cant print resp directly")
            print("=================================")
            
            return self._header + self._content

        except FileNotFoundError:
            # If file missing → return a 404
            print(f"[Response] File not found at {base_dir}{path}")
            return self.build_notfound()
