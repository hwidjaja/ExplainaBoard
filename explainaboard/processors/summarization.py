from __future__ import annotations

from collections.abc import Iterator, Sequence
from functools import lru_cache
import itertools

from datalabs import aggregating
from datalabs.operations.featurize.plugins.summarization.sum_attribute import (
    SUMAttribute,
)
from datalabs.operations.featurize.summarization import get_oracle_summary
import numpy

from explainaboard import TaskType
from explainaboard.analysis import feature
from explainaboard.analysis.analyses import Analysis, AnalysisLevel, BucketAnalysis
from explainaboard.analysis.feature_funcs import accumulate_vocab_from_samples
from explainaboard.info import SysOutputInfo
from explainaboard.processors.conditional_generation import (
    ConditionalGenerationProcessor,
)
from explainaboard.processors.processor_registry import register_processor
from explainaboard.utils.py_utils import hash_dict
from explainaboard.utils.typing_utils import unwrap

sum_attr = SUMAttribute()


@hash_dict
@lru_cache(maxsize=10)
def get_oracle(existing_features: dict):
    """
    oracle_info =
        {
        "source":src,
        "reference":ref,
        "oracle_summary":oracle,
        "oracle_labels":labels,
        "oracle_score":max_score
        }
    """

    sample = {
        "text": existing_features["source"],
        "summary": existing_features["reference"],
    }
    oracle_info = get_oracle_summary.func(sample)

    index_of_oracles = [i for i, e in enumerate(oracle_info["oracle_labels"]) if e != 0]
    oracle_position = numpy.mean(index_of_oracles)

    return {
        "oracle_position": oracle_position,
        "oracle_score": oracle_info["oracle_score"],
    }


@register_processor(TaskType.summarization)
class SummarizationProcessor(ConditionalGenerationProcessor):
    @classmethod
    def task_type(cls) -> TaskType:
        return TaskType.summarization

    def default_analyses(self) -> list[AnalysisLevel]:
        f = super().default_analyses()
        new_examp_features = {
            "sum_attributes": feature.Value(
                dtype="dict",
                func=lambda info, x, c: sum_attr.cal_attributes_each(
                    x["source"], x["reference"]
                ),
            ),
            "attr_compression": feature.Value(
                dtype="float",
                description="compression",
                func=lambda info, x, c: c.features['sum_attributes'][
                    "attr_compression"
                ],
            ),
            "attr_copy_len": feature.Value(
                dtype="float",
                description="copy length",
                func=lambda info, x, c: c.features['sum_attributes']["attr_copy_len"],
            ),
            "attr_coverage": feature.Value(
                dtype="float",
                description="coverage",
                func=lambda info, x, c: c.features['sum_attributes']["attr_coverage"],
            ),
            "attr_novelty": feature.Value(
                dtype="float",
                description="novelty",
                func=lambda info, x, c: c.features['sum_attributes']["attr_novelty"],
            ),
        }
        new_examp_cont_features = [
            k for k, v in new_examp_features.items() if ('float' in unwrap(v.dtype))
        ]
        new_examp_analyses: Sequence[Analysis] = [
            BucketAnalysis(
                description=new_examp_features[x].description,
                feature=x,
                method="continuous",
            )
            for x in new_examp_cont_features
        ]
        f[0].features.update(new_examp_features)
        f[0].analyses = list(itertools.chain(f[0].analyses, new_examp_analyses))
        return f

    @classmethod
    def _get_default_eaas_strs(cls):
        return ['rouge1', 'rouge2', 'rougeL', 'length_ratio']

    @aggregating()
    def _statistics_func(self, samples: Iterator, sys_info: SysOutputInfo):
        source_vocab, source_vocab_rank = accumulate_vocab_from_samples(
            samples, lambda x: x['text'], unwrap(sys_info.source_tokenizer)
        )

        target_vocab, target_vocab_rank = accumulate_vocab_from_samples(
            samples, lambda x: x['summary'], unwrap(sys_info.target_tokenizer)
        )
        return {
            'source_vocab': source_vocab,
            'source_vocab_rank': source_vocab_rank,
            'target_vocab': target_vocab,
            'target_vocab_rank': target_vocab_rank,
        }
