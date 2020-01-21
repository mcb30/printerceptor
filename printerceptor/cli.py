"""Command line interface"""

import argparse
from dataclasses import dataclass, field
import logging
from typing import Collection, ClassVar, Optional
from .daemon import InterceptorDaemon
from .plugins import plugins


@dataclass
class InterceptorArgument:
    """Interceptor command-line argument"""

    name: str
    port: Optional[str] = None

    @classmethod
    def parse(cls, value):
        """Parse argument"""
        args = value.split(':', maxsplit=1)
        name = args[0]
        port = args[1] if len(args) > 1 else None
        return cls(name, port)


@dataclass
class Command:
    """Printer interceptor daemon"""

    argv: Optional[Collection[str]] = None
    args: argparse.Namespace = field(init=False)

    loglevels: ClassVar = [
        logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG
    ]

    def __post_init__(self):
        self.args = self.parser().parse_args(self.argv)

    @classmethod
    def parser(cls):
        """Create argument parser"""
        parser = argparse.ArgumentParser(
            description=cls.__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.description += "\n\nAvailable interceptor types:\n" + "\n".join(
            "    %s" % x for x in plugins.keys()
        )
        parser.add_argument('--output', '-o', help="Output directory",
                            required=True)
        parser.add_argument('--user', '-u', help="Run as user")
        parser.add_argument('--group', '-g', help="Run as group")
        parser.add_argument('--verbose', '-v', action='count', default=0)
        parser.add_argument('--quiet', '-q', action='count', default=0)
        parser.add_argument(
            'interceptor', type=InterceptorArgument.parse, nargs='+',
            help="Interceptor type[:port] (e.g. 'lpd' or 'lpd:515')",
        )
        return parser

    @property
    def verbosity(self):
        """Verbosity level"""
        return (self.loglevels.index(logging.INFO) +
                self.args.verbose - self.args.quiet)

    @property
    def loglevel(self):
        """Log level"""
        return (self.loglevels[self.verbosity]
                if self.verbosity < len(self.loglevels) else logging.NOTSET)

    def execute(self):
        """Execute command"""
        logging.basicConfig(level=self.loglevel)
        daemon = InterceptorDaemon(path=self.args.output,
                                   user=self.args.user, group=self.args.group)
        for interceptor in self.args.interceptor:
            daemon.add(interceptor.name, port=interceptor.port)
        daemon.run()

    @classmethod
    def main(cls):
        """Execute command (as main entry point)"""
        cls().execute()
