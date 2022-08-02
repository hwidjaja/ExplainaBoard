from __future__ import annotations

import dataclasses

from eaas.endpoint import EndpointConfig

from explainaboard.metrics.eaas import EaaSMetricConfig
from explainaboard.metrics.metric import MetricConfig

_metric_config_registry: dict[str, type[MetricConfig]] = {}


def register_metric_config(cls):
    """
    a register for task specific processors.
    example usage: `@register_processor()`
    """

    _metric_config_registry[cls.__name__] = cls
    if cls.__name__.endswith('Config'):
        _metric_config_registry[cls.__name__[:-6]] = cls
    return cls


def get_metric_config_class(name) -> type[MetricConfig]:
    config_cls = _metric_config_registry.get(name)
    if config_cls is not None:
        return config_cls

    # TODO(odashi): Avoid EaaS completely from this module.
    if name in EndpointConfig().valid_metrics:
        return EaaSMetricConfig

    raise ValueError(f'Invalid Metric {name}')


def metric_config_from_dict(dikt: dict):
    type = dikt.pop('cls_name')
    config_cls = get_metric_config_class(type)
    field_names = set(f.name for f in dataclasses.fields(config_cls))
    return config_cls(
        **{k: config_cls.dict_conv(k, v) for k, v in dikt.items() if k in field_names}
    )
