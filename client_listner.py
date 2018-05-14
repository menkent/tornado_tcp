# -*- coding: utf-8 -*-
import logging

log = logging.getLogger(__name__)

import settings
from tornado.options import options
from tornado.tcpclient import TCPClient
import asyncio
from tornado.platform.asyncio import AsyncIOMainLoop


class SimpleClientListener(object):
    def __init__(self, *av, **kw):
        super(SimpleClientListener, self).__init__(*av, **kw)
        self.stream = None

    async def connect(self, *av, **kw):
        self.stream = await TCPClient().connect(*av, **kw)
        print('SimpleClientListener:: Connecting:: ')
        return self.stream

    async def read_messages(self):
        while not self.stream.closed():
            try:
                message = await self.stream.read_until(delimiter=b'\r\n')
                print(message)
            except Exception as e:
                print("Trouble: ", e)
                self.stream.close()
                asyncio.get_event_loop().stop()

async def main():
    client = SimpleClientListener()
    await client.connect(options.tcp_listener_host, options.tcp_listener_port)
    await client.read_messages()


if __name__ == "__main__":
    AsyncIOMainLoop().install()
    asyncio.get_event_loop().create_task(main())
    asyncio.get_event_loop().run_forever()
