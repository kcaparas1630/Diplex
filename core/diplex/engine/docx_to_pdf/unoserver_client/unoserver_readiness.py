"""Tells whether a unoserver on localhost is ready: it answers its info call once LibreOffice is up."""

import http.client
import xmlrpc.client
from xml.parsers.expat import ExpatError

UNOSERVER_HOST = "127.0.0.1"


def unoserver_answers(port: int, timeout_seconds: float) -> bool:
    """Tell whether the unoserver on the localhost port answers its info call within the timeout."""
    connection = http.client.HTTPConnection(UNOSERVER_HOST, port, timeout=timeout_seconds)
    try:
        request_body = xmlrpc.client.dumps((), "info").encode()
        connection.request("POST", "/RPC2", body=request_body, headers={"Content-Type": "text/xml"})
        response = connection.getresponse()
        if response.status != 200:
            return False
        xmlrpc.client.loads(response.read())  # a fault raises here
        return True
    except (OSError, http.client.HTTPException, xmlrpc.client.Error, ExpatError):
        return False
    finally:
        connection.close()
