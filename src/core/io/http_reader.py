import asyncio

class HTTPPool:
    def __init__(self, url:str, interval:int, mapping:dict={"key":"key", "time":"time", "value":"value"}):
        self._signals = []
    
    @property
    def signals(self):
        if self._signals:
            return self._signals
    
    