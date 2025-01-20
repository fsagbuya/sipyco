import sys
import asyncio
import unittest
import os

from sipyco.pc_rpc import Server
from sipyco.test.ssl_utils import create_ssl_certs


class Target:
    def output_value(self):
        return 4125380


class TestRPCTool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ssl_certs = create_ssl_certs()

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    async def check_value(self, ssl_certs=None):
        cmd = [sys.executable, "-m", "sipyco.sipyco_rpctool", "::1", "7777"]
        if ssl_certs:
            cmd.extend(["--ssl", ssl_certs["CLIENT_CERT"],
                        ssl_certs["CLIENT_KEY"],
                        ssl_certs["SERVER_CERT"]])
        cmd.extend(["call", "output_value"])

        proc = await asyncio.create_subprocess_exec(*cmd,
                            stdout=asyncio.subprocess.PIPE, env=os.environ)
        (value, err) = await proc.communicate()
        self.assertEqual(value.decode('ascii').rstrip(), '4125380')
        await proc.wait()

    async def do_test(self, ssl_certs=None):
        ssl_args = {}
        if ssl_certs:
            ssl_args = {
                "local_cert": ssl_certs["SERVER_CERT"],
                "local_key": ssl_certs["SERVER_KEY"],
                "peer_cert": ssl_certs["CLIENT_CERT"]
            }
        server = Server({"target": Target()})
        await server.start("::1", 7777, **ssl_args)
        await self.check_value(ssl_certs)
        await server.stop()

    def test_rpc(self):
        self.loop.run_until_complete(self.do_test())

    def test_ssl_rpc(self):
        self.loop.run_until_complete(self.do_test(ssl_certs=self.ssl_certs))

    def tearDown(self):
        self.loop.close()
