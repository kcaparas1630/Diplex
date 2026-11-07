"""A stand-in for the unoserver command in the pool tests: same arguments, same XML-RPC calls, no LibreOffice.

Run as `python stand_in_unoserver.py --port P --uno-port Q ...`. Like unoserver, it starts a stand-in LibreOffice child
in its own process group, which holds the UNO port and ignores SIGTERM, as soffice.bin outlived unoserver in the
benchmark. The DOCX bytes pick what a conversion does: b"slow..." takes a minute, b"crash..." kills this unoserver
(leaving its LibreOffice running), b"fault..." raises, and anything else returns a PDF naming this process. Each start
appends a line to the file in STAND_IN_UNOSERVER_LOG, if set; STAND_IN_UNOSERVER_START_SECONDS delays readiness, and
STAND_IN_UNOSERVER_CONVERT_SECONDS makes every conversion take that long.
"""

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
import xmlrpc.server

SLOW_CONVERSION_SECONDS = 60


def main() -> None:
    """Start the stand-in LibreOffice on the UNO port, then serve info and convert on the XML-RPC port."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--libreoffice", action="store_true", help="run as the stand-in LibreOffice child")
    parser.add_argument("--interface", default="127.0.0.1")
    parser.add_argument("--uno-interface", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2003)
    parser.add_argument("--uno-port", type=int, default=2002)
    parser.add_argument("--user-installation")
    parser.add_argument("--temp-dir")
    arguments = parser.parse_args()
    if arguments.libreoffice:
        _hold_the_uno_port(arguments.uno_interface, arguments.uno_port)
        return
    _record_start(arguments)
    libreoffice = subprocess.Popen(
        [sys.executable, __file__, "--libreoffice", "--uno-interface", arguments.uno_interface, "--uno-port", str(arguments.uno_port)]
    )
    time.sleep(float(os.environ.get("STAND_IN_UNOSERVER_START_SECONDS", "0")))
    if libreoffice.poll() is not None:
        sys.exit(1)  # the UNO port was taken, as when an old soffice.bin still holds it
    server = xmlrpc.server.SimpleXMLRPCServer(
        (arguments.interface, arguments.port), allow_none=True, logRequests=False, use_builtin_types=True
    )
    server.register_function(_report_info, "info")
    server.register_function(_convert, "convert")
    server.serve_forever()


def _hold_the_uno_port(uno_interface: str, uno_port: int) -> None:
    """Listen on the UNO port and sleep, ignoring SIGTERM, until killed."""
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    listener = socket.create_server((uno_interface, uno_port))
    while True:
        listener.settimeout(None)
        connection, _ = listener.accept()
        connection.close()


def _record_start(arguments: argparse.Namespace) -> None:
    """Append this start's process ID, group and arguments to the log file, if one is set."""
    log_path = os.environ.get("STAND_IN_UNOSERVER_LOG")
    if log_path:
        with open(log_path, "a") as log_file:
            log_file.write(
                f"start pid={os.getpid()} pgid={os.getpgid(0)} port={arguments.port} uno_port={arguments.uno_port} "
                f"interface={arguments.interface} uno_interface={arguments.uno_interface} "
                f"user_installation={arguments.user_installation} temp_dir={arguments.temp_dir}\n"
            )


def _report_info() -> dict:
    """Answer unoserver's info call."""
    return {"unoserver": "stand-in", "api": "3", "import_filters": {}, "export_filters": {}}


def _convert(inpath, indata, outpath, convert_to, filtername, filter_options, update_index, infiltername):
    """Act on the DOCX bytes: be slow, crash, fail, or return a PDF that names this process."""
    time.sleep(float(os.environ.get("STAND_IN_UNOSERVER_CONVERT_SECONDS", "0")))
    if indata.startswith(b"slow"):
        time.sleep(SLOW_CONVERSION_SECONDS)
    if indata.startswith(b"crash"):
        os._exit(1)
    if indata.startswith(b"fault"):
        raise RuntimeError("Could not load document <remote file> using the MS Word 2007 XML filter.")
    return f"%PDF-1.7 converted by {os.getpid()}".encode()


if __name__ == "__main__":
    main()
