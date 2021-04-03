# Copyright (C) 2017-2019 Janek Bevendorff, Webis Group
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from authorship_unmasking.conf.interfaces import Configurable, path_property
from authorship_unmasking.util.util import lru_cache, get_base_path

from abc import ABCMeta, abstractmethod
from enum import Enum, unique
from typing import Any, AsyncGenerator, Iterable, List
from uuid import UUID

import os


class Tokenizer(Configurable, metaclass=ABCMeta):
    """
    Base class for tokenizers.

    Tokenizer properties with setters defined via @property.setter
    can be set at runtime via job configuration.
    """

    @abstractmethod
    def tokenize(self, text: str) -> Iterable[str]:
        """
        Tokenize given input text.

        This method will be called a lot and should therefore be as fast as possible.
        If your tokenizer creates deterministic tokens, you should therefore consider returning
        cached results by this method into :function:: util.util.lru_cache().

        :param text: input text
        :return: Iterable of tokens generated from ``text`` (may be a generator)
        """
        pass

    async def await_tokens(self, text: str) -> AsyncGenerator[str, None]:
        """
        Return async generator for the tokens generated by :meth:: tokenize().

        :param text: input text
        :return: async generator for tokens generated from ``text``
        """
        for t in self.tokenize(text):
            yield t


class Chunker(Configurable, metaclass=ABCMeta):
    """
    Base class for chunkers.

    Tokenizer properties with setters defined via @property.setter
    can be set at runtime via job configuration.
    """
    def __init__(self, chunk_size: int = 500):
        """
        :param chunk_size: maximum chunk size
        """
        self._chunk_size = chunk_size

    @abstractmethod
    def chunk(self, text: str) -> Iterable[Any]:
        """
        Chunk a given text into several smaller parts.
        An individual chunk does not have to be text, but something that is readable by
        a suitable :class::FeatureSet.

        This method will be called a lot and should therefore be as fast as possible.
        If your chunker creates deterministic tokens, you should therefore consider returning
        cached results by this method into :function:: util.util.lru_cache().

        :param text: input text
        :return: Iterable of chunks from ``text`` (may be a generator)
        """
        pass

    async def await_chunks(self, text: str) -> AsyncGenerator[Any, None]:
        """
        Return async generator for the chunks generated by :meth:: chunk().

        :param text: input text
        :return: async generator for chunks generated from ``text``
        """
        for t in self.chunk(text):
            yield t

    @property
    def chunk_size(self) -> int:
        """Get chunk size"""
        return self._chunk_size

    @chunk_size.setter
    def chunk_size(self, chunk_size: int):
        """Set chunk size"""
        self._chunk_size = chunk_size


@unique
class SamplePairClass(Enum):
    """
    Base enumeration type for pairs. Members designating specific pair classes can be
    defined in sub-types of this enum type.
    """

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        if other is None and self.value == -1:
            return True
        elif isinstance(other, self.__class__):
            return other.value == self.value
        elif isinstance(other, str):
            return other.upper() == self.__str__()
        elif isinstance(other, int):
            return other == self.value
        elif isinstance(other, bool):
            if self.value == -1:
                return False
            else:
                return bool(self.value) == other

    def __hash__(self):
        return self.__repr__().__hash__()


class SamplePair(metaclass=ABCMeta):
    """
    Pair of sample text sets.

    Events published by this class:

    * `onProgress`:          [type ProgressEvent]
                             fired to indicate pair chunking progress
    """

    SAMPLE_PAIR_NS = UUID("412bd9f0-4c61-4bb7-a7f2-c88be2f9555c")

    def __init__(self, cls: SamplePairClass, chunker: Chunker):
        """
        Initialize pair of sample texts. Expects a set of main texts ``a`` and one
        or more texts ``b`` to compare with.
        Texts in ``a`` and ``b`` will be chunked individually before adding them
        sequentially to the chunk list.

        :param a: list of texts to verify
        :param b: list of other texts to compare with
        :param cls: class of the pair
        :param chunker: chunker for splitting input text
        """
        self._cls = cls
        self._chunker = chunker

    @abstractmethod
    def chunk(self, a: List[str], b: List[str]):
        """
        Create chunks from inputs.

        :param a: input texts one
        :param b: input texts two
        """
        pass

    @property
    @abstractmethod
    def cls(self) -> SamplePairClass:
        """Class (same author|different authors|unspecified)"""
        pass

    @property
    @abstractmethod
    def pair_id(self) -> str:
        """UUID string identifying a pair based on its set of texts."""
        pass

    @pair_id.setter
    @abstractmethod
    def pair_id(self, pair_id: str):
        """Explicitly set a new pair ID"""
        pass

    @property
    @abstractmethod
    def chunks_a(self) -> List[str]:
        """Chunks of first text (text to verify)"""
        pass

    @property
    @abstractmethod
    def chunks_b(self) -> List[str]:
        """Chunks of texts to compare the first text (a) with"""
        pass

    @abstractmethod
    def replace_chunks(self, chunks_a, chunks_b):
        """Replace previously set chunks"""
        pass


class CorpusParser(Configurable, metaclass=ABCMeta):
    """
    Base class for corpus parsers.
    """

    def __init__(self, chunk_tokenizer: Tokenizer, corpus_path: str = None, system: str = 'original'):
        """
        :param corpus_path: path to the corpus directory
        :param chunk_tokenizer: chunk tokenizer
        """
        self._corpus_path = None
        self.corpus_path = corpus_path
        self.chunk_tokenizer = chunk_tokenizer
        self.system = system

    @path_property
    def corpus_path(self) -> str:
        """Get corpus path"""
        return self._corpus_path

    @corpus_path.setter
    def corpus_path(self, path: str):
        """Set corpus path"""
        self._corpus_path = os.path.join(get_base_path(), path) if path is not None else None

    @abstractmethod
    async def __aiter__(self) -> AsyncGenerator[SamplePair, None]:
        """
        Asynchronous generator for parsed SamplePairs.
        """
        pass

    async def await_file(self, file_name) -> str:
        """
        Caching helper coroutine for reading a file.

        :param file_name: name of the file
        :return: its contents
        """
        return self.read_file(file_name)

    @lru_cache(protected=True, maxsize=50)
    def read_file(self, file_name) -> str:
        """
        Caching helper method for reading a file.

        :param file_name: name of the file
        :return: its contents
        """
        with open(file_name, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().replace("\ufeff", "")

    async def await_lines(self, file_name) -> AsyncGenerator[str, None]:
        """
        Read file line by line.

        :param file_name: name of the file
        :return: its contents line by line
        """
        with open(file_name, "r", encoding="utf-8", errors="ignore") as f:
            first = True
            for line in f:
                if first and line.startswith("\ufeff"):
                    yield line.replace("\ufeff", "")
                    first = False
                else:
                    yield line
