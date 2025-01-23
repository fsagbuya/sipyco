import unittest
import asyncio
from sipyco import broadcast
from sipyco.test.ssl_utils import create_ssl_certs


test_address = "::1"
test_port = 7777
test_channel = "test_channel"
test_message = {"key": "value", "number": 42}


class BroadcastCase(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.received_messages = []

    @classmethod
    def setUpClass(cls):
        cls.ssl_certs = create_ssl_certs()

    def notify_callback(self, message):
        self.received_messages.append(message)

    async def _do_test_broadcast(self, ssl_certs=None):
        broadcaster = broadcast.Broadcaster()
        broadcaster_ssl = {}
        receiver_ssl = {}

        if ssl_certs:
            broadcaster_ssl = {
                "local_cert": ssl_certs["SERVER_CERT"],
                "local_key": ssl_certs["SERVER_KEY"],
                "peer_cert": ssl_certs["CLIENT_CERT"]
            }
            receiver_ssl = {
                "local_cert": ssl_certs["CLIENT_CERT"],
                "local_key": ssl_certs["CLIENT_KEY"],
                "peer_cert": ssl_certs["SERVER_CERT"]
            }

        await broadcaster.start(test_address, test_port, **broadcaster_ssl)

        receiver = broadcast.Receiver(test_channel, self.notify_callback)

        for attempt in range(100):
            try:
                await receiver.connect(test_address, test_port, **receiver_ssl)
            except ConnectionRefusedError:
                pass
            else:
                break
        await asyncio.sleep(0.1)

        broadcaster.broadcast(test_channel, test_message)
        await asyncio.sleep(0.1)

        await receiver.close()
        await broadcaster.stop()

        self.assertEqual(len(self.received_messages), 1)
        self.assertEqual(self.received_messages[0], test_message)

    def test_broadcast(self):
        self.loop.run_until_complete(self._do_test_broadcast())

    def test_ssl_broadcast(self):
        self.loop.run_until_complete(self._do_test_broadcast(ssl_certs=self.ssl_certs))

    def tearDown(self):
        self.loop.close()
