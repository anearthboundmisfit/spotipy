# -*- coding: utf-8 -*-

""" An iteratable interface for spotipy results """

__all__ = ["SpotifyIterator"]

import re

import inflect
from spotipy import Spotify, SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials

SEARCH_REGEXP = re.compile('^https?://[^/]+/v1/search\\b')
SEARCH_MAX_OFFSET = 1000

class SpotipyIterator:
    """Make an iterator to use with Spotify API results"""

    inflector = inflect.engine()
 
    def __init__(self, *args, **kwargs):
        self._client = None
        # An instance of the Spotify API client may be passed-in for the,
        # iterator to use, or one will created automatically.
        if kwargs:
            if 'client' in kwargs:
                self._client = kwargs['client']
                # Because we can pass-in a result OR a Spotify API function to
                # call (and its arguments), to generate such a result, we must
                # take care to remove any keyword arguments not expected by a
                # function we might pass-in.
                del kwargs['client']
        if not self._client:
            self._client = Spotify(auth_manager=SpotifyClientCredentials(), 
                                   requests_session=True)
        self._collection = None
        # The Spotify API's search endpoint produces a result containing one
        # or more subcollections depending on the type of records searched
        # for. We need to be able to identify (or infer) which collection
        # is to be scanned in the case of a search.
        if kwargs:
            if 'collection' in kwargs:
                self._collection = kwargs['collection']
                # Because we can pass-in a result OR a Spotify API function to
                # call (and its arguments), to generate such a result, we must
                # take care to remove any keyword arguments not expected by a
                # function we might pass-in.
                del kwargs['collection']
            else:
                # We can infer and inflect from the "type" argument, which
                # would be present when delegating the creation of the 
                # result.
                if 'type' in kwargs:
                    self._collection = self.inflector.plural(kwargs['type'])
        # If a function (and its arguments) was passed-in, we should call it
        # in order to get the results, otherwise we assume a page of results
        # was passed-in.
        result, *args = args
        if callable(result):
            result = result(self._client, *args, **kwargs)
        self._page = result
        # If, at this point, the result isn't recognisable as a page of data,
        # and the collection type is still unkown, then the collection may be
        # identified as the name of the result's first key.
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
        if SEARCH_REGEXP.match(self._page['next']):
            if self._page['offset'] + self._page['limit'] >= SEARCH_MAX_OFFSET:
                return True
        return False
