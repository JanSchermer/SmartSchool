from OpenSSL import SSL
from os import getenv, path

# SSL configuration
USE_SSL = getenv("SMART_SCHOOL_SSL", False)
SSL_CHAIN = getenv("SMART_SCHOOL_SSL_CHAIN", "")
SSL_PRIVE = getenv("SMART_SCHOOL_SSL_PRIVE", "")

def generateSSLContext():
    """
    Generates ssl context with openSSL if ssl is in use
    Returns none, if provided files don't exist or ssl is not used
    """

    # Returning none if ssl is not used
    if not USE_SSL:
        return None

    # Checking if files exist.
    chain_exists = path.exists(SSL_CHAIN)
    prive_exists = path.exists(SSL_PRIVE)

    # Returning none, if one of the required files dose not exist
    if not chain_exists or not prive_exists:
        print("WARNING: SSL is active, but key or chain files do not exist. Falling back to deactivating SSL!")
        return None

    # Generating ssl context with provided key and chain files
    context = SSL.Context(SSL.PROTOCOL_TLSv1_2)
    context.use_certificate_chain_file(SSL_CHAIN)
    context.use_privatekey_file(SSL_PRIVE)

    return context
