"""LPD print interceptor"""

from .base import Interception

__all__ = [
    'LpdInterception',
]

LPD_OP_JOB = 0x02

LPD_OP_JOB_ABORT = 0x01
LPD_OP_JOB_CTRL = 0x02
LPD_OP_JOB_DATA = 0x03


class LpdInterception(Interception):
    """LPD socket interception

    The LPD protocol is defined in RFC 1179.
    """

    default_port = 'printer'

    async def intercept_command(self, reader):
        """Intercept LPD command"""
        opcode = await reader.read(1)
        if not opcode:
            return None, []
        string = await reader.readuntil(b'\n')
        return ord(opcode), string.rstrip().split(b' ')

    async def intercept(self, reader):
        """Intercept LPD print job"""

        # Ignore everything other than print jobs
        (opcode, _args) = await self.intercept_command(reader)
        if opcode != LPD_OP_JOB:
            self.logger.info("ignoring non-job opcode %d", opcode)
            return

        # Interpret job subcommands
        output = b''
        while True:
            (opcode, args) = await self.intercept_command(reader)
            if opcode is None:
                await self.output(output)
                return
            if opcode == LPD_OP_JOB_ABORT:
                self.logger.info("cancelled")
                return
            count = int(args.pop(0))
            data = await reader.readexactly(count)
            _nul = await reader.readexactly(1)
            if opcode == LPD_OP_JOB_DATA:
                output += data
            elif opcode == LPD_OP_JOB_CTRL:
                self.logger.debug("control file: %s",
                                  data.decode(errors='replace'))
            else:
                self.logger.error("unrecognised opcode %d", opcode)
