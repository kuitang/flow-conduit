"""
Nested write-once symbol tables.

Based on http://code.activestate.com/recipes/577434-nested-contexts-a-chain-of-mapping-objects/
"""

from collections import Mapping
from itertools import chain, imap

class SymbolTable(dict):
    def __init__(self, parent=None):
        'Create a new root context.'
        self.parent = parent
        self.map    = {}
        self.maps   = [ self.map ]
        if parent is not None:
            # Remember, it's a list of pointers.
            self.maps += parent.maps

    def new_child(self):
        'Make a child context.'
        return self.__class__(parent=self)

    def root(self):
        return self if self.parent is None else self.parent.root
    
    def __getitem__(self, key):
        for m in self.maps:
            if key in m: break
        return m[key]
    
    def add_symbol(key, value):
        for m in self.maps:
            if key in m:
                raise TypeError("Key %s already exists in dictionary %x"%
                                key, id(m))
        m[key] = value

    def __len__(self, len=len, sum=sum, imap=imap):
        return sum(imap(len, self.maps))

    def __iter__(self, chain_from_iterable=chain.from_iterable):
        return chain_from_iterable(self.maps)

    def __contains__(self, key, any=any):
        return any(key in m for m in self.maps)

    def __repr__(self, repr=repr):
        return ' -> '.join(imap(repr, self.maps))

