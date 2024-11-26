import ssl
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_ssl_context(local_cert=None, local_key=None, peer_cert=None, server_mode=False):
    """Create an SSL context with mutual authentication.

    :param local_cert: Certificate file. Providing this enables SSL.
    :param local_key: Private key file. Required when local_cert is provided.
    :param peer_cert: Peer's certificate file to trust. Required when local_cert is provided.
    :param server_mode: If True, create a server context, otherwise client context.
    """
    if local_key is None:
        raise ValueError("local_key is required when local_cert is provided")
    if peer_cert is None:
        raise ValueError("peer_cert is required when local_cert is provided")

    if server_mode:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.verify_mode = ssl.CERT_REQUIRED
    else:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    context.load_verify_locations(cafile=peer_cert)
    context.load_cert_chain(local_cert, local_key)
    return context
