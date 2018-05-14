# -*- coding: utf-8 -*-

import logging
log = logging.getLogger(__name__)


from tornado.options import define

define("tcp_listener_host", default="localhost", type=str)
define("tcp_source_port", default=8888, type=int)
define("tcp_listener_port", default=8889, type=int)
