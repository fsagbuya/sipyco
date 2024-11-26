Introduction
============

SiPyCo (Simple Python Communications) is a library for writing networked Python programs. It was originally part of ARTIQ, and was split out to enable light-weight programs to be written without a dependency on ARTIQ.

API documentation
=================

:mod:`sipyco.pyon` module
-------------------------

.. automodule:: sipyco.pyon
    :members:


:mod:`sipyco.pc_rpc` module
---------------------------

.. automodule:: sipyco.pc_rpc
    :members:


:mod:`sipyco.fire_and_forget` module
------------------------------------

.. automodule:: sipyco.fire_and_forget
    :members:


:mod:`sipyco.sync_struct` module
--------------------------------

.. automodule:: sipyco.sync_struct
    :members:


:mod:`sipyco.remote_exec` module
--------------------------------

.. automodule:: sipyco.remote_exec
    :members:

:mod:`sipyco.common_args` module
--------------------------------

.. automodule:: sipyco.common_args
    :members:

:mod:`sipyco.asyncio_tools` module
----------------------------------

.. automodule:: sipyco.asyncio_tools
    :members:

:mod:`sipyco.logging_tools` module
----------------------------------

.. automodule:: sipyco.logging_tools
    :members:



Remote Procedure Call tool
==========================

This tool is the preferred way of handling simple RPC servers.
Instead of writing a client for simple cases, you can simply use this tool
to call remote functions of an RPC server. For secure connections, see `SSL Setup`_.

* Listing existing targets

        The ``list-targets`` sub-command will print to standard output the
        target list of the remote server::

            $ sipyco_rpctool hostname port list-targets

* Listing callable functions

        The ``list-methods`` sub-command will print to standard output a sorted
        list of the functions you can call on the remote server's target.

        The list will contain function names, signatures (arguments) and
        docstrings.

        If the server has only one target, you can do::

            $ sipyco_rpctool hostname port list-methods

        Otherwise you need to specify the target, using the ``-t target``
        option::

            $ sipyco_rpctool hostname port list-methods -t target_name

* Remotely calling a function

        The ``call`` sub-command will call a function on the specified remote
        server's target, passing the specified arguments.
        Like with the previous sub-command, you only need to provide the target
        name (with ``-t target``) if the server hosts several targets.

        The following example will call the ``set_attenuation`` method of the
        Lda controller with the argument ``5``::

            $ sipyco_rpctool ::1 3253 call -t lda set_attenuation 5

        In general, to call a function named ``f`` with N arguments named
        respectively ``x1, x2, ..., xN`` you can do::

            $ sipyco_rpctool hostname port call -t target f x1 x2 ... xN

        You can use Python syntax to compute arguments as they will be passed
        to the ``eval()`` primitive. The numpy package is available in the namespace
        as ``np``. Beware to use quotes to separate arguments which use spaces::

            $ sipyco_rpctool hostname port call -t target f '3 * 4 + 2' True '[1, 2]'
            $ sipyco_rpctool ::1 3256 call load_sample_values 'np.array([1.0, 2.0], dtype=float)'

        If the called function has a return value, it will get printed to
        the standard output if the value is not None like in the standard
        python interactive console::

            $ sipyco_rpctool ::1 3253 call get_attenuation
            5.0

Command-line details:

.. argparse::
   :ref: sipyco.sipyco_rpctool.get_argparser
   :prog: sipyco_rpctool


SSL Setup
=========

SiPyCo supports SSL/TLS encryption with mutual authentication for secure communication, but it is disabled by default. To enable and use SSL, follow these steps:

**Generate server certificate:**

.. code-block:: bash

   openssl req -x509 -newkey rsa -keyout server.key -nodes -out server.pem -sha256 -subj "/" --addext "subjectAltName=IP:127.0.0.1"

**Generate client certificate:**

.. code-block:: bash

   openssl req -x509 -newkey rsa -keyout client.key -nodes -out client.pem -sha256 -subj "/" --addext "subjectAltName=IP:127.0.0.1"

.. note::
    .. note::
    The ``--addext "subjectAltName=IP:127.0.0.1"`` parameter specifies the valid IP address for the certificate, which is needed for hostname verification. You should replace this with the actual IP address of your server.

    Examples for different network configurations:

    - For IPv6 localhost: ``--addext "subjectAltName=IP:::1"``
    - For local network IP: ``--addext "subjectAltName=IP:192.168.1.100"``
    - For multiple IPs: ``--addext "subjectAltName=IP:127.0.0.1,IP:::1"``
    - For hostname (if needed): ``--addext "subjectAltName=DNS:your.hostname.com"``

This creates:

- A server certificate (``server.pem``) and key (``server.key``)
- A client certificate (``client.pem``) and key (``client.key``)


Enabling SSL
------------

To enable SSL, the server needs its certificate/key and trusts the client's certificate, while the client needs its certificate/key and trusts the server's certificate:

**For servers:**

.. code-block:: python

   simple_server_loop(targets, host, port,
                     local_cert="path/to/server.pem",
                     local_key="path/to/server.key",
                     peer_cert="path/to/client.pem")

**For clients:**

.. code-block:: python

   client = Client(host, port,
                  local_cert="path/to/client.pem",
                  local_key="path/to/client.key",
                  peer_cert="path/to/server.pem")

.. note::
    When SSL is enabled, mutual TLS authentication is mandatory. Both server and client must provide valid certificates and each must trust the other's certificate for the connection to be established.