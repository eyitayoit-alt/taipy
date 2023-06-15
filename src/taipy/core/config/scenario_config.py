# Copyright 2023 Avaiga Private Limited
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.

from collections import defaultdict
from copy import copy
from typing import Any, Callable, Dict, List, Optional, Set, Union

from taipy.config._config import _Config
from taipy.config.common._template_handler import _TemplateHandler as _tpl
from taipy.config.common._validate_id import _validate_id
from taipy.config.common.frequency import Frequency
from taipy.config.config import Config
from taipy.config.section import Section

from .data_node_config import DataNodeConfig
from .pipeline_config import PipelineConfig
from .task_config import TaskConfig


class ScenarioConfig(Section):
    """
    Configuration fields needed to instantiate an actual `Scenario^`.

    Attributes:
        id (str): Identifier of the scenario config. It must be a valid Python variable name.
        tasks (Optional[Union[TaskConfig, List[TaskConfig]]]): List of task configs.<br/>
            The default value is None.
        additional_data_nodes (Optional[Union[DataNodeConfig, List[DataNodeConfig]]]): <br/>
            List of additional data node configs. The default value is None.
        frequency (Optional[Frequency]): The frequency of the scenario's cycle. The default value is None.
        comparators: Optional[Dict[str, Union[List[Callable], Callable]]]: Dictionary of the data node <br/>
            config id as key and a list of Callable used to compare the data nodes as value.
        **properties (dict[str, any]): A dictionary of additional properties.
    """

    name = "SCENARIO"

    _PIPELINES_KEY = "pipelines"
    _TASKS_KEY = "tasks"
    _ADDITIONAL_DATA_NODES_KEY = "additional_data_nodes"
    _FREQUENCY_KEY = "frequency"
    _COMPARATOR_KEY = "comparators"

    def __init__(
        self,
        id: str,
        tasks: Optional[Union[TaskConfig, List[TaskConfig]]] = None,
        additional_data_nodes: Optional[Union[DataNodeConfig, List[DataNodeConfig]]] = None,
        frequency: Optional[Frequency] = None,
        comparators: Optional[Dict[str, Union[List[Callable], Callable]]] = None,
        **properties,
    ):

        if tasks:
            self._tasks = [tasks] if isinstance(tasks, TaskConfig) else copy(tasks)
        else:
            self._tasks = []  # TODO: should this be a set instead???

        if additional_data_nodes:
            self._additional_data_nodes = (
                [additional_data_nodes]
                if isinstance(additional_data_nodes, DataNodeConfig)
                else copy(additional_data_nodes)
            )
        else:
            self._additional_data_nodes = []  # TODO: should this be a set instead???

        self.frequency = frequency
        self.comparators = defaultdict(list)
        if comparators:
            for k, v in comparators.items():
                if isinstance(v, list):
                    self.comparators[_validate_id(k)].extend(v)
                else:
                    self.comparators[_validate_id(k)].append(v)
        super().__init__(id, **properties)

    def __copy__(self):
        comp = None if self.comparators is None else self.comparators
        return ScenarioConfig(
            self.id,
            copy(self._tasks),
            copy(self._additional_data_nodes),
            self.frequency,
            copy(comp),
            **copy(self._properties),
        )

    def __getattr__(self, item: str) -> Optional[Any]:
        return _tpl._replace_templates(self._properties.get(item))  # type: ignore

    @property
    def task_configs(self) -> List[TaskConfig]:
        return self._tasks

    @property
    def tasks(self) -> List[TaskConfig]:
        return self._tasks

    @property
    def additional_data_node_configs(self) -> List[DataNodeConfig]:
        return self._additional_data_nodes

    @property
    def additional_data_nodes(self) -> List[DataNodeConfig]:
        return self._additional_data_nodes

    @property
    def data_node_configs(self) -> Set[DataNodeConfig]:
        return self.__get_all_unique_data_nodes()

    @property
    def data_nodes(self) -> Set[DataNodeConfig]:
        return self.__get_all_unique_data_nodes()

    def __get_all_unique_data_nodes(self) -> set[DataNodeConfig]:
        data_node_configs = set(self._additional_data_nodes)
        for task in self._tasks:
            data_node_configs.update(task.inputs)
            data_node_configs.update(task.outputs)

        return data_node_configs

    @classmethod
    def default_config(cls):
        return ScenarioConfig(cls._DEFAULT_KEY, [], [], None, dict())

    def _clean(self):
        self._tasks = []
        self._additional_data_nodes = []
        self.frequency = None
        self.comparators = dict()
        self._properties.clear()

    def _to_dict(self):
        return {
            self._COMPARATOR_KEY: self.comparators,
            self._TASKS_KEY: self._tasks,
            self._ADDITIONAL_DATA_NODES_KEY: self._additional_data_nodes,
            self._FREQUENCY_KEY: self.frequency,
            **self._properties,
        }

    @classmethod
    def _from_dict(cls, as_dict: Dict[str, Any], id: str, config: Optional[_Config]) -> "ScenarioConfig":  # type: ignore
        as_dict.pop(cls._ID_KEY, id)

        tasks = []
        additional_data_nodes = []

        if cls._TASKS_KEY in as_dict or cls._ADDITIONAL_DATA_NODES_KEY in as_dict:
            if task_ids := as_dict.pop(cls._TASKS_KEY, None):
                task_configs = config._sections[TaskConfig.name]  # type: ignore
                for task_id in task_ids:
                    if task_config := task_configs.get(task_id, None):
                        tasks.append(task_config)
            if additional_data_node_ids := as_dict.pop(cls._ADDITIONAL_DATA_NODES_KEY, None):
                data_node_configs = config._sections[DataNodeConfig.name]  # type: ignore
                for additional_data_node_id in additional_data_node_ids:
                    if additional_data_node_config := data_node_configs.get(additional_data_node_id, None):
                        additional_data_nodes.append(additional_data_node_config)
        else:
            # Check if pipeline configs exist, if yes, migrate by getting all task configs and ignore pipeline configs
            if pipeline_ids := as_dict.pop(cls._PIPELINES_KEY, None):
                pipeline_configs = config._sections[PipelineConfig.name]  # type: ignore
                for p_id in pipeline_ids:
                    if pipeline_config := pipeline_configs.get(p_id, None):
                        tasks.extend(pipeline_config.tasks)

        frequency = as_dict.pop(cls._FREQUENCY_KEY, None)
        comparators = as_dict.pop(cls._COMPARATOR_KEY, dict())

        return ScenarioConfig(
            id=id,
            tasks=tasks,
            additional_data_nodes=additional_data_nodes,
            frequency=frequency,
            comparators=comparators,
            **as_dict,
        )

    def _update(self, as_dict: Dict[str, Any], default_section=None):
        self._tasks = as_dict.pop(self._TASKS_KEY, self._tasks)
        if self._tasks is None and default_section:
            self._tasks = default_section._tasks

        self._additional_data_nodes = as_dict.pop(self._ADDITIONAL_DATA_NODES_KEY, self._additional_data_nodes)
        if self._additional_data_nodes is None and default_section:
            self._additional_data_nodes = default_section._additional_data_nodes

        self.frequency = as_dict.pop(self._FREQUENCY_KEY, self.frequency)
        if self.frequency is None and default_section:
            self.frequency = default_section.frequency

        self.comparators = as_dict.pop(self._COMPARATOR_KEY, self.comparators)
        if self.comparators is None and default_section:
            self.comparators = default_section.comparators

        self._properties.update(as_dict)  # type: ignore
        if default_section:
            self._properties = {**default_section.properties, **self._properties}  # type: ignore

    def add_comparator(self, dn_config_id: str, comparator: Callable):
        self.comparators[dn_config_id].append(comparator)

    def delete_comparator(self, dn_config_id: str):
        if dn_config_id in self.comparators:
            del self.comparators[dn_config_id]

    @staticmethod
    def _configure(
        id: str,
        task_configs: Optional[List[TaskConfig]] = None,
        additional_data_node_configs: Optional[List[DataNodeConfig]] = None,
        frequency: Optional[Frequency] = None,
        comparators: Optional[Dict[str, Union[List[Callable], Callable]]] = None,
        **properties,
    ) -> "ScenarioConfig":
        """Configure a new scenario configuration.

        Parameters:
            id (str): The unique identifier of the new scenario configuration.
            task_configs (Optional[List[TaskConfig^]]): The list of task configurations used by this
                scenario configuration. The default value is None.
            additional_data_node_configs (Optional[List[DataNodeConfig^]]): The list of additional data nodes
                related to this scenario configuration. The default value is None.
            frequency (Optional[Frequency^]): The scenario frequency.<br/>
                It corresponds to the recurrence of the scenarios instantiated from this
                configuration. Based on this frequency each scenario will be attached to the
                relevant cycle.
            comparators (Optional[Dict[str, Union[List[Callable], Callable]]]): The list of
                functions used to compare scenarios. A comparator function is attached to a
                scenario's data node configuration. The key of the dictionary parameter
                corresponds to the data node configuration id. During the scenarios'
                comparison, each comparator is applied to all the data nodes instantiated from
                the data node configuration attached to the comparator. See
                `(taipy.)compare_scenarios()^` more more details.
            **properties (dict[str, any]): A keyworded variable length list of additional arguments.

        Returns:
            The new scenario configuration.
        """
        section = ScenarioConfig(
            id, task_configs, additional_data_node_configs, frequency=frequency, comparators=comparators, **properties
        )
        Config._register(section)
        return Config.sections[ScenarioConfig.name][id]

    @staticmethod
    def _configure_default(
        task_configs: Optional[List[TaskConfig]] = None,
        additional_data_node_configs: List[DataNodeConfig] = None,
        frequency: Optional[Frequency] = None,
        comparators: Optional[Dict[str, Union[List[Callable], Callable]]] = None,
        **properties,
    ) -> "ScenarioConfig":
        """Configure the default values for scenario configurations.

        This function creates the *default scenario configuration* object,
        where all scenario configuration objects will find their default
        values when needed.

        Parameters:
            task_configs (Optional[List[TaskConfig^]]): The list of task configurations used by this
                scenario configuration.
            additional_data_node_configs (Optional[List[DataNodeConfig^]]): The list of additional data nodes
                related to this scenario configuration.
            frequency (Optional[Frequency^]): The scenario frequency.
                It corresponds to the recurrence of the scenarios instantiated from this
                configuration. Based on this frequency each scenario will be attached to
                the relevant cycle.
            comparators (Optional[Dict[str, Union[List[Callable], Callable]]]): The list of
                functions used to compare scenarios. A comparator function is attached to a
                scenario's data node configuration. The key of the dictionary parameter
                corresponds to the data node configuration id. During the scenarios'
                comparison, each comparator is applied to all the data nodes instantiated from
                the data node configuration attached to the comparator. See
                `taipy.compare_scenarios()^` more more details.
            **properties (dict[str, any]): A keyworded variable length list of additional arguments.

        Returns:
            The new default scenario configuration.
        """
        section = ScenarioConfig(
            _Config.DEFAULT_KEY,
            task_configs,
            additional_data_node_configs,
            frequency=frequency,
            comparators=comparators,
            **properties,
        )
        Config._register(section)
        return Config.sections[ScenarioConfig.name][_Config.DEFAULT_KEY]
