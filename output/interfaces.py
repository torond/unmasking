from conf.interfaces import Configurable
from input.interfaces import SamplePair

from abc import ABC, abstractmethod
from time import time
from typing import Any, Dict, List, Tuple


class Output(Configurable, ABC):
    """
    Base class for output handlers
    """
    
    @abstractmethod
    def save(self, output_dir: str):
        """
        Save object state to file in a given output directory

        :param output_dir: output directory
        """
        pass
    
    @abstractmethod
    def reset(self):
        """Reset output and clear all variable data"""
        pass
    
    def _get_output_filename_base(self) -> str:
        """
        Generate a base filename (without extension) containing a timestamp which
        can safely be used for writing output files.
        
        :return: filename base
        """
        return self.__class__.__name__ + "." + str(int(time()))


class Aggregator(Output, ABC):
    """
    Base class for unmasking curve aggregation.
    This can be used for building ensembles of multiple runs.
    """

    @abstractmethod
    def add_curve(self, identifier: str, cls: SamplePair.Class, values: List[float]):
        """
        Add curve to aggregation for given class.

        :param identifier: a common identifier for this and further instances of this curve
        :param cls: class of the pair
        :param values: curve points
        """
        pass

    @abstractmethod
    def get_aggregated_curves(self) -> Dict[Any, Tuple[Any, SamplePair.Class, List[float]]]:
        """
        Return aggregated curves for each sample pair.

        :return: tuple containing the identifier of the aggregated curve, its class and aggregated values
        """
        pass
