# -*- coding: utf-8 -*-

""" An iteratable interface for spotipy results """

__all__ = ["SpotifyIterator"]

import re

import inflect
from spotipy import Spotify, SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials

class SpotipyIterator:
    """Make an iterator to use with Spotify API results"""

    INFLECT = inflect.engine()
    SEARCH_REGEXP = re.compile('^https?://[^/]+/v1/search\\b')
    SEARCH_MAX_OFFSET = 1000
 
    def __init__(self, *args, **kwargs):
        self._client = None
        if kwargs:
            if 'client' in kwargs:
                self._client = kwargs['client']
                del kwargs['client']
        if not self._client:
            self._client = Spotify(auth_manager=SpotifyClientCredentials(), 
                                   requests_session=True)
        self._collection = None
        if kwargs:
            if 'collection' in kwargs:
                self._collection = kwargs['collection']
                del kwargs['collection']
            else:
                if 'type' in kwargs:
                    self._collection = self.INFLECT.plural(kwargs['type'])
        result, *args = args
        if callable(result):
            result = result(self._client, *args, **kwargs)
        self._page = result
        if self._page and 'total' not in self._page:
            if not self._collection:
                self._collection, *_ = self._page.keys()
        self._set_page_size_and_row()

    def __iter__(self):
        return self

    def __next__(self):
        if self._row >= self._page_size:
            if self._page and 'next' in self._page and self._page['next']:
                if self._search_endpoint_and_offset_limit_reached:
                    raise StopIteration
                self._page = self._client.next(self._page)
                self._set_page_size_and_row()
                if self._row >= self._page_size:
                    raise StopIteration
            else:
                raise StopIteration
        this_row = self._row
        self._row = this_row + 1
        return self._page['items'][this_row]
    
    def _set_page_size_and_row(self):
        if self._collection:
            self._page = self._page[self._collection]
        if self._page and 'items' in self._page:
            self._page_size = len(self._page['items'])
        else:
            self._page_size = 0
        self._row = 0
        return self

    def _search_endpoint_and_offset_limit_reached(self):
        if self.SEARCH_REGEXP.match(self._page['next']):
            if self._page['offset'] + self._page['limit'] >= self.SEARCH_MAX_OFFSET:
                return True
        return False
