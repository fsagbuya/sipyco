import os
import atexit
import tempfile
import subprocess
import shutil
from pathlib import Path


def create_ssl_certs():
    cert_dir = tempfile.mkdtemp()

    for cert_name in ["server", "client"]:
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", os.path.join(cert_dir, f"{cert_name}.key"),
            "-nodes",
            "-out", os.path.join(cert_dir, f"{cert_name}.pem"),
            "-sha256", "-days", "1",
            "-subj", "/",
            "-addext", "subjectAltName=IP:::1"
        ], check=True)

    certs = {
        "SERVER_KEY": os.path.join(cert_dir, "server.key"),
        "SERVER_CERT": os.path.join(cert_dir, "server.pem"),
        "CLIENT_KEY": os.path.join(cert_dir, "client.key"),
        "CLIENT_CERT": os.path.join(cert_dir, "client.pem")
    }

    def cleanup():
        if os.path.exists(cert_dir):
            shutil.rmtree(cert_dir)

    atexit.register(cleanup)
    return certs
