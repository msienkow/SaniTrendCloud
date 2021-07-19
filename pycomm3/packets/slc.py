from .ethernetip import SendUnitDataRequestPacket, SendUnitDataResponsePacket


class SLCResponsePacket(SendUnitDataResponsePacket):

    ...


class SLCRequestPacket(SendUnitDataRequestPacket):
    def __init__(self):
        super().__init__()

    def _setup_message(self):
        super()._setup_message()

        self._msg += []
