# General-purpose unmasking framework
# Copyright (C) 2017 Janek Bevendorff, Webis Group
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use, copy,
# modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

from abc import abstractmethod, ABCMeta
import os
import sys
from typing import Any, Dict


class ConfigLoader(metaclass=ABCMeta):
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

    @abstractmethod
    def get_config_path(self) -> str:
        """
        Get configuration base directory for resolving relative pathss.

        :return: directory path
        """
        pass

    def resolve_relative_path(self, path: str) -> str:
        """
        Try to resolve a path relative to the following directories (in order):

        - config directory
        - application directory
        - application config directory

        An absolute path will be returned unchanged if the file was found. Otherwise
        it will be resolved relatively as well. If after the last try the file could
        still not be found, a :class:: FileNotFoundError will be raised.

        :return: resolved path
        """
        if os.path.isabs(path) and os.path.isfile(path):
            return path

        rc_file = os.path.join(self.get_config_path(), path)
        if os.path.exists(rc_file):
            return os.path.realpath(rc_file)

        rc_file = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])), path)
        if os.path.exists(rc_file):
            return rc_file

        rc_file = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])), "etc", path)
        if not os.path.exists(rc_file):
            raise FileNotFoundError("No such file or directory: {}".format(path))

        return os.path.realpath(rc_file)


# noinspection PyPep8Naming
class path_property(property):
    """
    Decorator class for file path properties.
    This class inherits from property and can be used to annotate object properties
    whose values may be path-expanded. See :meth: Configurable.is_path_property
    """
    pass


# noinspection PyPep8Naming
class instance_property(property):
    """
    Decorator class for properties which expect another configured instance
    of a certain class instead of a base type.
    """

    def __init__(self, fget=None, fset=None, fdel=None, doc=None, delegate_args=False):
        """
        :param fget: getter function
        :param fset: setter function
        :param fdel: deleter function
        :param doc: doc string
        :param delegate_args: True to delegate __init__ arguments of the parent to instances
        """
        super().__init__(fget, fset, fdel, doc)
        self.delegate_args = delegate_args

    def __call__(self, fget=None, fset=None, fdel=None, doc=None):
        super().__init__(fget, fset, fdel, doc)
        return self

    def __get__(self, obj, objtype=None):
        obj = super().__get__(obj, objtype)
        if objtype is not None:
            objtype.delegate_args = self.delegate_args
        return obj

    def getter(self, fget):
        return type(self)(fget, self.fset, self.fdel, self.__doc__, self.delegate_args)

    def setter(self, fset):
        return type(self)(self.fget, fset, self.fdel, self.__doc__, self.delegate_args)

    def deleter(self, fdel):
        return type(self)(self.fget, self.fset, fdel, self.__doc__, self.delegate_args)


# noinspection PyPep8Naming
class instance_list_property(instance_property):
    """
    Decorator class for properties which expect a list configured instances
    of certain classes instead of a base type.
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
        :return: whether object has a given property
        """
        return hasattr(self.__class__, name) and isinstance(getattr(self.__class__, name), property)

    def is_path_property(self, name: str) -> bool:
        """
        Check whether a property is a path property.
        Values of path properties may be expanded to absolute paths.

        The property has to exist. Check with :meth: has_property first.

        :param name: property name
        :return: whether property is a path property
        """
        return isinstance(getattr(self.__class__, name), path_property)

    def is_instance_property(self, name: str) -> bool:
        """
        Check whether a property is a recursive instance property.

        The property has to exist. Check with :meth: has_property first.

        :param name: property name
        :return: whether property is a recursive instance property
        """
        return isinstance(getattr(self.__class__, name), instance_property)

    def is_instance_list_property(self, name: str) -> bool:
        """
        Check whether a property is a recursive instance list property.

        The property has to exist. Check with :meth: has_property first.

        :param name: property name
        :return: whether property is a recursive instance list property
        """
        return isinstance(getattr(self.__class__, name), instance_list_property)
