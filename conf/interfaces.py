from abc import abstractmethod, ABC
from typing import Any, Dict


class ConfigLoader(ABC):
    @abstractmethod
    def load(self, filename: str):
        """
        Load configuration from given file.

        :param filename: configuration file name
        """
        pass

    @abstractmethod
    def set(self, cfg: Dict[str, Any]):
        """
        Set configuration from given dictionary.

        :param cfg: configuration dict
        """
        pass

    @abstractmethod
    def get(self, name: str = None) -> Any:
        """
        Get configuration option.

        :param name: name of the option, None to get full config dict
        :return: option value
        :raise: KeyError if option not found
        """
        pass

    @abstractmethod
    def save(self, file_name: str) -> Any:
        """
        Save a copy of the current configuration to the given file

        :param file_name: name of the target file (without extension)
        """
        pass


class Configurable:
    """
    Base class for classes which are configurable at runtime via @properties.
    """
    
    def set_property(self, name: str, value: Any):
        """
        Dynamically set a given configuration property.
        
        :param name: property name
        :param value: property value
        :raise: KeyError if property does not exist
        """
        if not self.has_property(name):
            raise KeyError("{}@{}: No such configuration property".format(self.__class__.__name__, name))

        setattr(self, name, value)
    
    def has_property(self, name: str) -> bool:
        """
        Check whether a class has a given property and if is of type property.
        
        :param name: property name
        :return: Whether object has a given property
        """
        return hasattr(self.__class__, name) and isinstance(getattr(self.__class__, name), property)