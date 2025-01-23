import asyncio
import logging
import unittest
from sipyco import logging_tools
from sipyco.test.ssl_utils import create_ssl_certs


test_address = "::1"
test_port = 7777
test_source = "test_client"
test_messages = [
    ("This is a debug message", logging.DEBUG),
    ("This is an info message", logging.INFO),
    ("This is a warning message", logging.WARNING),
    ("This is an error message", logging.ERROR),
    ("This is a multi-line message\nwith two\nlines", logging.INFO)]


class LoggingCase(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.client_logger = logging.getLogger("client_logger")
        self.client_logger.setLevel(logging.DEBUG)

        self.fwd_logger = logging_tools._fwd_logger
        self.fwd_logger.setLevel(logging.DEBUG)

        self.log_records = []
        self.handler = logging.StreamHandler()
        self.handler.setFormatter(logging_tools.MultilineFormatter())
        self.handler.emit = lambda record: self.log_records.append(record)
        self.fwd_logger.addHandler(self.handler)

    @classmethod
    def setUpClass(cls):
        cls.ssl_certs = create_ssl_certs()

    async def _do_test_logging(self, ssl_certs=None):
        self.log_records.clear()
        server_ssl = {}
        forwarder_ssl = {}

        if ssl_certs:
            server_ssl = {
                "local_cert": ssl_certs["SERVER_CERT"],
                "local_key": ssl_certs["SERVER_KEY"],
                "peer_cert": ssl_certs["CLIENT_CERT"]
            }
            forwarder_ssl = {
                "local_cert": ssl_certs["CLIENT_CERT"],
                "local_key": ssl_certs["CLIENT_KEY"],
                "peer_cert": ssl_certs["SERVER_CERT"]
            }

        server = logging_tools.Server()
        await server.start(test_address, test_port, **server_ssl)

        try:
            forwarder = logging_tools.LogForwarder(test_address, test_port,
                reconnect_timer=0.1, **forwarder_ssl)
            forwarder.setFormatter(logging_tools.MultilineFormatter())

            self.client_logger.addFilter(
                logging_tools.SourceFilter(logging.DEBUG, test_source))
            self.client_logger.addHandler(forwarder)

            forwarder_task = asyncio.create_task(forwarder._do())

            try:
                for message, level in test_messages:
                    self.log_records.clear()
                    self.client_logger.log(level, message)

                    start_time = self.loop.time()
                    while not self.log_records and (self.loop.time() - start_time) < 5.0:
                        await asyncio.sleep(0.1)

                    self.assertTrue(self.log_records)
                    record = self.log_records[0]
                    self.assertEqual(record.getMessage(), message)
                    self.assertEqual(record.levelno, level)
                    self.assertEqual(record.source, test_source)

                    if "\n" in message:
                        linebreaks = message.count("\n")
                        formatted_message = self.handler.formatter.format(record)
                        self.assertIn(f"<{linebreaks + 1}>", formatted_message)
            finally:
                self.client_logger.removeHandler(forwarder)
                forwarder_task.cancel()
                try:
                    await forwarder_task
                except asyncio.CancelledError:
                    pass
        finally:
            await server.stop()

    def test_logging(self):
        self.loop.run_until_complete(self._do_test_logging())

    def test_ssl_logging(self):
        self.loop.run_until_complete(self._do_test_logging(ssl_certs=self.ssl_certs))

    def tearDown(self):
        self.fwd_logger.removeHandler(self.handler)
        self.loop.close()
