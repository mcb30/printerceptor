"""Print interceptor"""

from abc import abstractmethod
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import hashlib
import logging
from pathlib import Path
import socket
from typing import ClassVar, Collection, Optional, Type, Union

__all__ = [
    'SocketPair',
    'Interception',
    'Interceptor',
]


@dataclass
class SocketPair:
    """A StreamReader/StreamWriter socket pair"""

    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self):
        """Close stream"""
        self.writer.close()
        await self.writer.wait_closed()

    @property
    def sock(self):
        """Underlying socket"""
        return self.writer.get_extra_info('socket')


@dataclass
class Interception:
    """An interception of a single print job"""

    server: SocketPair
    path: Path
    name: Optional[str] = None
    logger: logging.Logger = field(init=False, repr=False)

    bufsize: ClassVar[int] = 4096
    default_port: ClassVar[Union[int, str, None]] = None

    def __post_init__(self):
        if self.name is None:
            self.name = "[%s:%d]-[%s:%d]" % (*self.peername[0:2],
                                             *self.sockname[0:2])
        self.logger = logging.getLogger(self.name)

    @property
    def sock(self):
        """Server socket"""
        return self.server.sock

    @property
    def peername(self):
        """Server socket remote name"""
        return self.sock.getpeername()

    @property
    def sockname(self):
        """Server socket local name"""
        return self.sock.getsockname()

    async def output(self, data):
        """Write output to directory"""
        checksum = hashlib.sha256()
        checksum.update(data)
        name = checksum.hexdigest()
        self.logger.info("intercepted %s", name)
        with open(self.path / name, 'wb') as f:
            f.write(data)

    @abstractmethod
    async def intercept(self, reader: asyncio.StreamReader):
        """Intercept print data"""

    async def intercept_then_discard(self, reader: asyncio.StreamReader):
        """Intercept data, discarding any remainder"""
        try:
            await self.intercept(reader)
            while True:
                data = await reader.read(self.bufsize)
                if not data:
                    break
        except Exception as exc:  # pylint: disable=broad-except
            self.logger.exception(exc)

    @classmethod
    async def tee(cls, source: asyncio.StreamReader,
                  writers: Collection[asyncio.StreamWriter] = (),
                  readers: Collection[asyncio.StreamReader] = ()):
        """Copy data from source to destination(s)"""
        try:
            while True:
                data = await source.read(cls.bufsize)
                if not data:
                    break
                for reader in readers:
                    reader.feed_data(data)
                for writer in writers:
                    writer.write(data)
                    await writer.drain()
        finally:
            for reader in readers:
                reader.feed_eof()
            for writer in writers:
                writer.close()
                await writer.wait_closed()

    @asynccontextmanager
    async def connect(self):
        """Connect to original socket destination"""
        with socket.socket(self.sock.family,
                           (self.sock.type | socket.SOCK_NONBLOCK),
                           self.sock.proto) as sock:
            await asyncio.get_running_loop().sock_connect(sock, self.sockname)
            reader, writer = await asyncio.open_connection(sock=sock)
            async with SocketPair(reader, writer) as client:
                yield client

    async def serve(self):
        """Serve incoming connection"""
        self.logger.info("opened")
        async with self.connect() as client:
            copy = asyncio.StreamReader()
            await asyncio.gather(
                self.tee(client.reader, [self.server.writer]),
                self.tee(self.server.reader, [client.writer], [copy]),
                self.intercept_then_discard(copy),
            )
        self.logger.info("closed")


@dataclass
class Interceptor:
    """A print job interceptor"""

    interception: Type[Interception]
    path: Path
    port: Union[int, str, None] = None
    name: Optional[str] = None
    logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self):
        if self.port is None:
            self.port = self.interception.default_port
        if self.name is None:
            self.name = '%s[%s]' % (self.interception.__name__, self.port)
        self.logger = logging.getLogger(self.name)

    async def accept(self, reader: asyncio.StreamReader,
                     writer: asyncio.StreamWriter):
        """Accept a new incoming connection"""
        async with SocketPair(reader, writer) as server:
            await self.interception(server, path=self.path).serve()

    async def start(self, **kwargs):
        """Start interceptor"""
        self.logger.info("starting")
        server = await asyncio.start_server(self.accept, port=self.port,
                                            **kwargs)
        for sock in server.sockets:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_TRANSPARENT, 1)
        self.logger.info("started")
