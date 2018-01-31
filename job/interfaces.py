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

from conf.interfaces import ConfigLoader, Configurable
from event.dispatch import EventBroadcaster
from event.interfaces import EventHandler
from features.interfaces import FeatureSet
from output.interfaces import Output, Aggregator

from abc import abstractmethod, ABCMeta
from importlib import import_module
from time import time
from typing import Any, Dict, Iterable, List, Tuple

import os
import yaml


class JobExecutor(metaclass=ABCMeta):
    """
    Generic job executor.
    """

    def __init__(self):
        self._outputs = []
        self._aggregators = []
        self._config = None     # type: ConfigLoader

    @property
    def outputs(self) -> List[Output]:
        """Get configured outputs"""
        return self._outputs

    @property
    def aggregators(self) -> List[Aggregator]:
        """Get configured aggregators"""
        return self._aggregators

    def _init_job_output(self, conf: ConfigLoader, output_dir: str = None) -> Tuple[str, str]:
        """
        Initialize job output directory and return job ID.
        If `output_dir` is not set, the `job.output_dir` directive provided by
        the given :class:: ConfigLoader will be used.

        :param conf: config loader
        :param output_dir: base directory to save job outputs to
        :return: tuple of generated job ID and absolute output directory path
        """
        job_id = "job_" + str(int(time()))
        output_dir = conf.get("job.output_dir") if not output_dir else output_dir
        if not os.path.isabs(output_dir):
            output_dir = os.path.join(conf.get_config_path(), output_dir)

        output_dir = os.path.relpath(os.path.join(output_dir, job_id))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if not os.path.isdir(output_dir):
            raise IOError("Failed to create output directory '{}', maybe it exists already?".format(output_dir))

        conf.save(os.path.join(output_dir, "job"))

        return job_id, output_dir

    def _load_class(self, name: str):
        """
        Dynamically load a class based on its fully-qualified module path
        
        :param name: class name
        :return: class
        """
        modules = name.split(".")
        return getattr(import_module(".".join(modules[0:-1])), modules[-1])

    def _configure_instance(self, cfg: Dict[str, Any], assert_type: type = None, ctr_args: Iterable[Any] = None):
        """
        Dynamically configure an instance of a class based on the parameters
        defined in the job configuration.
        
        :param cfg: object configuration parameters
        :param assert_type: raise exception if object is not of this type
        :param ctr_args: constructor arguments
        :return: configured instance
        """
        cls = self._load_class(cfg["name"])
        if ctr_args is None:
            obj = cls()
        else:
            obj = cls(*ctr_args)

        if assert_type is not None:
            self._assert_type(obj, assert_type)

        if "rc_file" in cfg and cfg["rc_file"] is not None:
            rc_file = self._config.resolve_relative_path(cfg["rc_file"])
            with open(rc_file, "r") as f:
                rc_contents = yaml.safe_load(f)

            for rc in rc_contents:
                obj.set_property(rc, rc_contents[rc])

        if "parameters" in cfg and cfg["parameters"] is not None:
            for p in cfg["parameters"]:
                val = cfg["parameters"][p]
                if type(val) is str and obj.has_property(p) and obj.is_path_property(p):
                    val = self._config.resolve_relative_path(val)
                obj.set_property(p, val)
        return obj

    def _subscribe_to_events(self, obj: EventHandler, events: List[Dict[str, Any]]):
        """
        Subscribe an object to events for the given job.

        :param obj: EventHandler object to subscribe
        :param events: list of dicts containing a name key and an optional
                       senders key with a list of allowed senders
        """
        self._assert_type(obj, EventHandler)

        for event in events:
            senders = None
            if "senders" in event and type(event["senders"]) is list:
                senders = {self._load_class(s) if type(s) is str else s for s in event["senders"]}
            EventBroadcaster.subscribe(event["name"], obj, senders)

    def _load_outputs(self, outputs: List[Dict[str, Any]]):
        """
        Load job output modules.

        :param outputs: output settings list
        """
        for output in outputs:
            output_obj = self._configure_instance(output, assert_type=Output)

            if "events" in output and output["events"]:
                self._subscribe_to_events(output_obj, output["events"])

            self._outputs.append(output_obj)

    def _load_aggregators(self, aggs: List[Dict[str, Any]]):
        """
        Load job aggregator modules.

        :param aggs: aggregator settings list
        """
        for agg in aggs:
            agg_obj = self._configure_instance(agg, assert_type=Aggregator)

            if "events" in agg and agg["events"]:
                self._subscribe_to_events(agg_obj, agg["events"])

            self._aggregators.append(agg_obj)

    def _assert_type(self, obj: object, t: type):
        """
        Assert an object to be an instance of a certain class, otherwise raise an exception.

        :param obj: object
        :param t: type
        """
        if not isinstance(obj, t):
            raise ValueError("'{}.{}' is not a subclass of {}".format(
                obj.__class__.__module__, obj.__class__.__name__, t.__name__))

    @abstractmethod
    def run(self, conf: ConfigLoader, output_dir: str = None):
        """
        Execute job with given job configuration.

        :param conf: job configuration loader
        :param output_dir: output directory
        """
        pass


class ConfigurationExpander(metaclass=ABCMeta):
    """
    Base class for configuration expanders.
    """

    @abstractmethod
    def expand(self, configuration_vectors: Iterable[Tuple]) -> Iterable[Tuple]:
        """
        Expand the given configuration vectors based on a certain expansion strategy.

        Generates an iterable sequence of n-dimensional vectors from an input
        Iterable of n configuration vectors where each vector represents a
        single configuration.

        :param configuration_vectors: input vectors with configuration values
        :return: generator of expanded configuration vectors
        """
        pass


class Strategy(Configurable, metaclass=ABCMeta):
    """
    Base class for execution strategies.
    """

    @abstractmethod
    async def run(self, fs: FeatureSet):
        """
        Run execution strategy.

        :param fs: parametrized feature set to execute on
        """
