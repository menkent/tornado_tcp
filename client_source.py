# -*- coding: utf-8 -*-
import logging

log = logging.getLogger(__name__)

import settings
from tornado.options import options
from tornado.tcpclient import TCPClient
import random
import asyncio
from utils import status_map, byte_message_xor
from tornado.platform.asyncio import AsyncIOMainLoop


class SimpleClientSource(object):
    def __init__(self, *av, **kw):
        super(SimpleClientSource, self).__init__(*av, **kw)
        self.message_number = 0  #  max = 2 ** 16, then close sendings
        self.status = random.choice(list(status_map.keys()))
        # todo: get source_id from another place
        self.source_id = bytes(('s_{}'.format(random.randint(0, 9999))).ljust(8, '_'), encoding='ascii')
        self.stream = None


    def generate_message_from_source(self):
        res = bytearray()
        # header
        res.append(0x01)

        # message number
        self.message_number += 1
        res.extend(int(self.message_number).to_bytes(length=2, byteorder="big", signed=False))

        # source_id
        res.extend(self.source_id)

        # status
        res.extend(self.status)

        # numfields
        numfields = random.randint(1, 7)  # todo max = 255
        res.extend(numfields.to_bytes(length=1, byteorder="big", signed=False))

        # fields
        for field_num in range(0, numfields):
            field_name = ('f_{}'.format(field_num)).ljust(8, ' ')
            field_value = random.randint(0, 200)  # todo: max = 2 ** 32

            res.extend(bytes(field_name, encoding='ascii'))
            res.extend(int(field_value).to_bytes(length=4, byteorder="big", signed=False))

        # xor
        res.extend(byte_message_xor(res))
        return res

    async def connect(self, *av, **kw):
        self.stream = await TCPClient().connect(*av, **kw)
        print('Connecting:: ', self.source_id)
        return self.stream

    def is_trouble_reply(self, reply):
        if reply[0] == 0x11:
            mes_number = int.from_bytes(reply[1:3], byteorder="big", signed=False)
            if reply[3] != byte_message_xor(reply[0:3])[0]:
                return True
        else:
            return True
        return False

    async def send_message(self):
        mes = self.generate_message_from_source()
        try:
            await self.stream.write(mes)
            reply = await self.stream.read_bytes(num_bytes=4)

            if not self.is_trouble_reply(reply) and self.message_number < 2 ** 16:
                await asyncio.sleep(random.randint(5, 10))
                asyncio.get_event_loop().create_task(self.send_message())
            else:
                self.stream.close()
        except Exception as e:
            print('Trouble:', e)
            self.stream.close()
            asyncio.get_event_loop().stop()


async def main():
    client = SimpleClientSource()
    await client.connect(options.tcp_listener_host, options.tcp_source_port)
    await client.send_message()


if __name__ == "__main__":
    AsyncIOMainLoop().install()
    asyncio.get_event_loop().create_task(main())
    asyncio.get_event_loop().run_forever()
