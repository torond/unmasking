from event import EventBroadcaster, ProgressEvent

from abc import ABC, abstractmethod
from enum import Enum, unique
from typing import Iterable, List


class Tokenizer(ABC):
    """
    Base class for tokenizers.
    """
    
    @abstractmethod
    def tokenize(self, text: str) -> Iterable[str]:
        """
        Tokenize given input text.

        :param t: input text
        :return: iterable of tokens generated from ``t``
        """
        pass


class SamplePair:
    """
    Pair of sample text sets.
    
    Events published by this class:
    
    * `onProgress`: [type: ProgressEvent]
                    fired during chunk generation to indicate current progress
    """
    
    @unique
    class Class(Enum):
        UNSPECIFIED = -1
        DIFFERENT_AUTHORS = 0
        SAME_AUTHOR = 1
        
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
            return self.value
    
    def __init__(self, a: List[str], b: List[str], cls: Class, chunk_tokenizer: Tokenizer):
        """
        Initialize pair of sample texts. Expects a set of main texts ``a`` and one
        or more texts ``b`` to compare with.
        Texts in ``a`` and ``b`` will be chunked individually before adding them
        sequentially to the chunk list.

        :param a: list of texts to verify
        :param b: list of other texts to compare with
        :param cls: class of the pair
        :param chunk_tokenizer: chunk tokenizer
        """
        
        self._cls = cls
        self._chunk_tokenizer = chunk_tokenizer
        
        self._progress_event = ProgressEvent(len(a) + len(b))
        EventBroadcaster.publish("onProgress", self._progress_event, self.__class__)
        
        self._chunks_a = []
        for t in a:
            self._chunks_a.extend(self._chunk_tokenizer.tokenize(t))
            self._progress_event.increment()
            EventBroadcaster.publish("onProgress", self._progress_event, self.__class__)
        
        self._chunks_b = []
        for t in b:
            self._chunks_b.extend(self._chunk_tokenizer.tokenize(t))
            self._progress_event.increment()
            EventBroadcaster.publish("onProgress", self._progress_event, self.__class__)
    
    @property
    def cls(self) -> Class:
        """Class (same author|different authors|unspecified)"""
        return self._cls
    
    @property
    def chunks_a(self) -> List[str]:
        """Chunks of first text (text to verify)"""
        return self._chunks_a
    
    @property
    def chunks_b(self) -> List[str]:
        """Chunks of texts to compare the first text (a) with"""
        return self._chunks_b


class CorpusParser(ABC):
    """
    Base class for corpus parsers.
    """
    
    def __init__(self, corpus_path: str, chunk_tokenizer: Tokenizer):
        """
        :param corpus_path: path to the corpus directory
        :param chunk_tokenizer: chunk tokenizer
        """
        self.corpus_path = corpus_path
        self.chunk_tokenizer = chunk_tokenizer
    
    @abstractmethod
    def __iter__(self) -> Iterable[SamplePair]:
        """
        Iterable or generator returning author pairs. This method is abstract and needs
        to be implemented by all concrete CorpusParsers.

        :return: iterable of SamplePairs
        """
        pass
    
    def get_all_pairs(self) -> List[SamplePair]:
        """
        :return: list of all pairs in the current corpus
        """
        pairs = []
        for p in self:
            pairs.append(p)
        return pairs
