"""Interceptor daemon"""

import asyncio
from dataclasses import dataclass, field
import grp
import logging
import os
from pathlib import Path
import pwd
from typing import Collection, Optional, Union
from .base import Interceptor
from . import plugins

__all__ = [
    'InterceptorDaemon',
]


@dataclass
class InterceptorDaemon:
    """A print job interceptor daemon"""

    path: Union[str, Path]
    user: Optional[str] = None
    group: Optional[str] = None
    interceptors: Collection[Interceptor] = field(default_factory=list)
    logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self):
        self.path = Path(self.path)
        self.logger = logging.getLogger(self.__class__.__name__)

    def add(self, name, port=None):
        """Add specified interceptor"""
        plugin = getattr(plugins, name)
        self.interceptors.append(Interceptor(plugin, port=port,
                                             path=self.path))

    async def start(self, **kwargs):
        """Start all interceptors"""
        await asyncio.gather(*(x.start(**kwargs) for x in self.interceptors))

    def run(self):
        """Run daemon"""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        if self.group is not None:
            os.setgroups([])
            os.setgid(grp.getgrnam(self.group).gr_gid)
        if self.user is not None:
            os.setuid(pwd.getpwnam(self.user).pw_uid)
        self.logger.info("started as uid=%d(%s) gid=%d(%s)",
                         os.getuid(), pwd.getpwuid(os.getuid()).pw_name,
                         os.getgid(), grp.getgrgid(os.getgid()).gr_name)
        self.path.mkdir(parents=True, exist_ok=True)
        loop.run_forever()
        self.logger.info("stopped")
