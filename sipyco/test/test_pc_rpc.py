import asyncio
import inspect
import subprocess
import sys
import time
import unittest
import os
import ssl

import numpy as np

from sipyco import pc_rpc, pyon
from sipyco.test.ssl_utils import create_ssl_certs


test_address = "::1"
test_port = 7777
test_object = [5, 2.1, None, True, False,
               {"a": 5, 2: np.linspace(0, 10, 1)},
               (4, 5), (10,), "ab\nx\"'"]


class RPCCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ssl_certs = create_ssl_certs()

    def _run_server_and_test(self, test, *args, ssl_args={}):
        env = os.environ.copy()
        if ssl_args:
            env.update(self.ssl_certs)

        # running this file outside of unittest starts the echo server
        with subprocess.Popen([sys.executable,
                               sys.modules[__name__].__file__], env=env) as proc:
            try:
                test(*args, ssl_args=ssl_args)
            except (ssl.SSLError, SyntaxError):
                proc.kill()
                raise
            finally:
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    raise

    def _blocking_echo(self, target, die_using_sys_exit=False, ssl_args={}):
        for attempt in range(100):
            time.sleep(.2)
            try:
                remote = pc_rpc.Client(test_address, test_port, target, **ssl_args)
            except ConnectionRefusedError:
                pass
            else:
                break
        try:
            test_object_back = remote.echo(test_object)
            self.assertEqual(test_object, test_object_back)
            test_object_back = remote.async_echo(test_object)
            self.assertEqual(test_object, test_object_back)
            with self.assertRaises(AttributeError):
                remote.non_existing_method
            if die_using_sys_exit:
                # If the server dies and just drops the connection, we
                # expect a client-side error due to lack of data.
                with self.assertRaises(SyntaxError):
                    remote.raise_sys_exit()
            else:
                remote.terminate()
        finally:
            remote.close_rpc()

    def test_blocking_echo(self):
        self._run_server_and_test(self._blocking_echo, "test")

    def test_ssl_blocking_echo(self):
        ssl_args = {"local_cert": self.ssl_certs["CLIENT_CERT"],
                    "local_key": self.ssl_certs["CLIENT_KEY"],
                    "peer_cert": self.ssl_certs["SERVER_CERT"]}
        self._run_server_and_test(self._blocking_echo, "test", ssl_args=ssl_args)

    def test_sys_exit(self):
        self._run_server_and_test(self._blocking_echo, "test", True)

    def test_blocking_echo_autotarget(self):
        self._run_server_and_test(self._blocking_echo, pc_rpc.AutoTarget)

    def test_ssl_verification_fail(self):
        wrong_certs = create_ssl_certs()
        wrong_client_args = {"local_cert": wrong_certs["CLIENT_CERT"],
                             "local_key": wrong_certs["CLIENT_KEY"],
                             "peer_cert": self.ssl_certs["SERVER_CERT"]}

        wrong_local_key = {"local_cert": self.ssl_certs["CLIENT_CERT"],
                           "local_key": wrong_certs["CLIENT_KEY"],
                           "peer_cert": self.ssl_certs["SERVER_CERT"]}

        wrong_peer_cert = {"local_cert": self.ssl_certs["CLIENT_CERT"],
                           "local_key": self.ssl_certs["CLIENT_KEY"],
                           "peer_cert": wrong_certs["SERVER_CERT"]}

        with self.assertRaises(SyntaxError):
            self._run_server_and_test(self._blocking_echo, "test", ssl_args=wrong_client_args)
        with self.assertRaises(ssl.SSLError):
            self._run_server_and_test(self._blocking_echo, "test", ssl_args=wrong_local_key)
        with self.assertRaises(ssl.SSLCertVerificationError):
            self._run_server_and_test(self._blocking_echo, "test", ssl_args=wrong_peer_cert)

    async def _asyncio_echo(self, target, ssl_args={}):
        remote = pc_rpc.AsyncioClient()
        for attempt in range(100):
            await asyncio.sleep(.2)
            try:
                await remote.connect_rpc(test_address, test_port, target, **ssl_args)
            except ConnectionRefusedError:
                pass
            else:
                break
        try:
            test_object_back = await remote.echo(test_object)
            self.assertEqual(test_object, test_object_back)
            test_object_back = await remote.async_echo(test_object)
            self.assertEqual(test_object, test_object_back)
            with self.assertRaises(TypeError):
                await remote.return_unserializable()
            with self.assertRaises(AttributeError):
                await remote.non_existing_method
            await remote.terminate()
        finally:
            remote.close_rpc()

    def _loop_asyncio_echo(self, target, ssl_args={}):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._asyncio_echo(target, ssl_args=ssl_args))
        finally:
            loop.close()

    def test_asyncio_echo(self):
        self._run_server_and_test(self._loop_asyncio_echo, "test")

    def test_ssl_asyncio_echo(self):
        ssl_args = {"local_cert": self.ssl_certs["CLIENT_CERT"],
                    "local_key": self.ssl_certs["CLIENT_KEY"],
                    "peer_cert": self.ssl_certs["SERVER_CERT"]}
        self._run_server_and_test(self._loop_asyncio_echo, "test", ssl_args=ssl_args)

    def test_asyncio_echo_autotarget(self):
        self._run_server_and_test(self._loop_asyncio_echo, pc_rpc.AutoTarget)

    def test_rpc_encode_function(self):
        """Test that `pc_rpc` can encode a function properly.

        Used in `get_rpc_method_list` part of
        :meth:`sipyco.pc_rpc.Server._process_action`
        """

        def _annotated_function(
            arg1: str, arg2: np.ndarray = np.array([1,])
        ) -> np.ndarray:
            """Sample docstring."""
            return arg1

        argspec_documented, docstring = pc_rpc.Server._document_function(
            _annotated_function
        )
        self.assertEqual(docstring, "Sample docstring.")

        # purposefully ignore how argspec["annotations"] is treated.
        # allows option to change PYON later to encode annotations.
        argspec_master = dict(inspect.getfullargspec(_annotated_function)._asdict())
        argspec_without_annotation = argspec_master.copy()
        del argspec_without_annotation["annotations"]
        # check if all items (excluding annotations) are same in both dictionaries
        self.assertLessEqual(
            argspec_without_annotation.items(), argspec_documented.items()
        )
        self.assertDictEqual(
            argspec_documented, pyon.decode(pyon.encode(argspec_documented))
        )


class Echo:
    def raise_sys_exit(self):
        sys.exit(0)

    def echo(self, x):
        return x

    async def async_echo(self, x):
        await asyncio.sleep(0.01)
        return x

    def return_unserializable(self):
        # Arbitrary classes can't be PYON-serialized.
        return Echo()


def run_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        echo = Echo()
        server = pc_rpc.Server({"test": echo}, builtin_terminate=True)
        ssl_args = {}
        if all(k in os.environ for k in ["SERVER_CERT", "SERVER_KEY", "CLIENT_CERT"]):
            ssl_args = {"local_cert": os.environ["SERVER_CERT"],
                        "local_key": os.environ["SERVER_KEY"],
                        "peer_cert": os.environ["CLIENT_CERT"]}

        loop.run_until_complete(server.start(test_address, test_port, **ssl_args))
        try:
            loop.run_until_complete(server.wait_terminate())
        finally:
            loop.run_until_complete(server.stop())
    finally:
        loop.close()


if __name__ == "__main__":
    run_server()
