# -*- coding: utf-8 -*-
import logging
log = logging.getLogger(__name__)

import settings
from tornado.tcpserver import TCPServer
from tornado.options import options
import asyncio
from utils import status_map, byte_message_xor, get_ms_time
from tornado.netutil import bind_sockets
from tornado.platform.asyncio import AsyncIOMainLoop


class MyTCPListenerFromSource(TCPServer):
    def __init__(self, sender_server, *av, **kw):
        super(MyTCPListenerFromSource, self).__init__(*av, **kw)
        self.sender_server = sender_server
        sender_server.listener_server = self
        self.sources = dict()

    def answer_for_source(self, is_error, message_number):
        res = bytearray()
        res.append(0x12 if is_error else 0x11)
        res.extend(int(0 if is_error else message_number).to_bytes(length=2, byteorder="big", signed=False))
        res.extend(byte_message_xor(res))
        return res

    def update_source_info(self, source_id, message_number, status):
        self.sources[source_id] = (message_number, status, get_ms_time())

    async def handle_stream(self, stream, address):
        print('Source:: New connection from {}'.format(str(address)))
        source_id = None
        while not stream.closed():
            try:
                message = bytearray()
                # header
                header = await stream.read_bytes(1)
                message.extend(header)

                # message number
                message_number = await stream.read_bytes(2)
                message.extend(message_number)
                message_number = int.from_bytes(message_number, byteorder="big", signed=False)

                # source_id
                source_id = await stream.read_bytes(8)
                message.extend(source_id)
                source_id = str(source_id, encoding='ascii')

                # status
                status = await stream.read_bytes(1)
                message.extend(status)

                # status
                numfields = await stream.read_bytes(1)
                message.extend(numfields)
                numfields = int.from_bytes(numfields, byteorder="big", signed=False)

                # fields
                for field_num in range(0, numfields):
                    field_name = await stream.read_bytes(8)
                    message.extend(field_name)
                    field_name = str(field_name, encoding='ascii')

                    field_value = await stream.read_bytes(4)
                    message.extend(field_value)
                    field_value = int.from_bytes(field_value, byteorder="big", signed=False)

                    # broadcast to listeners
                    # todo: заменить на отложенные таски, чтобы не прерывать обработку данного сообщения рассылкой
                    await self.sender_server.broadcast_message(source_id, field_name, field_value)

                # xor
                xor_sum = await stream.read_bytes(1)
                xor_message = byte_message_xor(message)

                if xor_sum == xor_message:
                    print('Message is OK')
                    await stream.write(self.answer_for_source(is_error=False, message_number=message_number))

                    # Update Source Info
                    self.update_source_info(source_id=source_id, message_number=message_number, status=status)

                else:
                    print('Message is FAIL')
                    await stream.write(self.answer_for_source(is_error=True, message_number=message_number))
            except Exception as e:
                stream.close()

        # del self.sources[source_id]
        if source_id and source_id in self.sources:
            del self.sources[source_id]


class MyTCPSenderToListeners(TCPServer):
    def __init__(self, *av, **kw):
        super(MyTCPSenderToListeners, self).__init__(*av, **kw)
        self.listeners = []
        self.listener_server = None

    async def broadcast_message(self, source_id, field_name, field_value):
        message = "[{}] {} | {}\r\n".format(source_id, field_name, field_value)
        need_to_remove = []
        for listener_stream in self.listeners:
            try:
                await listener_stream.write(message.encode(encoding='ascii'))
            except Exception as e:
                listener_stream.close()
                need_to_remove.append(listener_stream)

        for st in need_to_remove:
            if st in self.listeners:
                self.listeners.remove(st)


    async def handle_stream(self, stream, address):
        print('Listeners :: New connection from {}'.format(str(address)))
        self.listeners.append(stream)

        source_init_format = '[{source_id}] {message_number} | {status} | {t} \r\n'

        if self.listener_server:
            for source_id, (message_number, status, last_time) in self.listener_server.sources.items():
                message = source_init_format.format(
                    source_id=source_id,
                    message_number=message_number,
                    status=status_map.get(status, None),
                    t=get_ms_time() - last_time,
                )
                await stream.write(message.encode(encoding='ascii'))


async def main():
    # todo: объединить оба TCPServer'a в один tornado Application, так их будет удобнее связывать
    sender = MyTCPSenderToListeners()  # Рассылает слушателям порта 8889
    listener = MyTCPListenerFromSource(sender_server=sender)  # Получает сообщения от источников с порта 8888

    source_socket = bind_sockets(options.tcp_source_port)
    listener_sockets = bind_sockets(options.tcp_listener_port)

    sender.add_sockets(listener_sockets)
    listener.add_sockets(source_socket)


if __name__ == "__main__":
    AsyncIOMainLoop().install()
    asyncio.get_event_loop().create_task(main())
    asyncio.get_event_loop().run_forever()
