import unittest
import asyncio

from sipyco import broadcast


test_address = "::1"
test_port = 7777
test_message = {"key": "value", "number": 42}


class BroadcastCase(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.received_messages = []
        self.message_received = asyncio.Event()

    async def _do_test_broadcast(self):
        def notify_callback(message):
            self.received_messages.append(message)
            self.message_received.set()

        broadcaster = broadcast.Broadcaster()
        await broadcaster.start(test_address, test_port)

        receiver = broadcast.Receiver("test_channel", notify_callback)
        await receiver.connect(test_address, test_port)

        # Sleep to avoid race condition. If broadcast() runs before server
        # setup recipient's message queue, initial messages may be lost.
        await asyncio.sleep(0.01)

        broadcaster.broadcast("test_channel", test_message)
        await self.message_received.wait()

        await receiver.close()
        await broadcaster.stop()

        self.assertEqual(len(self.received_messages), 1)
        self.assertEqual(self.received_messages, [test_message])

    def test_broadcast(self):
        self.loop.run_until_complete(self._do_test_broadcast())

    def tearDown(self):
        self.loop.close()
