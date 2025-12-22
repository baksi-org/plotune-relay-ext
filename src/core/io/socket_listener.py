
class SocketListener:
    def __init__(self, url:str, auto_reconnect:bool, mapping:dict={"key":"key", "time":"time", "value":"value"}):
        self._signals = []
    
    @property
    def signals(self):
        if self._signals:
            return self._signals
        