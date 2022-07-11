from __future__ import annotations

from typing import Any, cast, List

from datalabs import aggregating
import numpy as np

from explainaboard import TaskType
from explainaboard.analysis import feature
from explainaboard.analysis.analyses import Analysis, AnalysisLevel, BucketAnalysis
from explainaboard.analysis.case import AnalysisCase, AnalysisCaseSpan
from explainaboard.analysis.feature import FeatureType
from explainaboard.analysis.feature_funcs import (
    cap_feature,
    count_tokens,
    feat_freq_rank,
    feat_length_freq,
    feat_num_oov,
)
from explainaboard.info import SysOutputInfo
from explainaboard.metrics.log_prob import LogProbConfig
from explainaboard.metrics.metric import MetricConfig, MetricStats
from explainaboard.processors.processor import Processor
from explainaboard.processors.processor_registry import register_processor
from explainaboard.utils.logging import progress
from explainaboard.utils.typing_utils import unwrap


@register_processor(TaskType.language_modeling)
class LanguageModelingProcessor(Processor):
    @classmethod
    def task_type(cls) -> TaskType:
        return TaskType.language_modeling

    def default_analyses(self) -> list[AnalysisLevel]:
        examp_features: dict[str, FeatureType] = {
            "text": feature.Value("string"),
            "log_probs": feature.Value("string"),
            "text_length": feature.Value(
                dtype="float",
                description="text length in tokens",
                func=lambda info, x, c: count_tokens(info, x['text']),
            ),
            "text_chars": feature.Value(
                dtype="float",
                description="text length in characters",
                func=lambda info, x, c: len(x['text']),
            ),
            "num_oov": feature.Value(
                dtype="float",
                description="the number of out-of-vocabulary words",
                require_training_set=True,
                func=lambda info, x, c, stat: feat_num_oov(
                    info, x['text'], stat['vocab']
                ),
            ),
            "fre_rank": feature.Value(
                dtype="float",
                description=(
                    "the average rank of each word based on its frequency in "
                    "training set"
                ),
                require_training_set=True,
                func=lambda info, x, c, stat: feat_freq_rank(
                    info, x['text'], stat['vocab_rank']
                ),
            ),
            "length_fre": feature.Value(
                dtype="float",
                description="the frequency of text length in training set",
                require_training_set=True,
                func=lambda info, x, c, stat: feat_length_freq(
                    info, x['text'], stat['length_fre']
                ),
            ),
        }
        examp_continuous_features = [
            k for k, v in examp_features.items() if ('float' in unwrap(v.dtype))
        ]
        examp_analyses: list[BucketAnalysis] = [
            BucketAnalysis(x, method="continuous") for x in examp_continuous_features
        ]

        tok_features: dict[str, FeatureType] = {
            "tok_log_prob": feature.Value(
                dtype="float",
                description=("log probability of the token according to the LM"),
            ),
            "tok_capitalness": feature.Value(
                dtype="string",
                description=(
                    "The capitalness of an token. For example, "
                    "first_caps represents only the first character of "
                    "the token is capital. full_caps denotes all "
                    "characters of the token are capital"
                ),
                func=lambda info, x, c: cap_feature(c.text),
            ),
            "tok_position": feature.Value(
                dtype="float",
                description=("The relative position of a token in a sentence"),
                func=lambda info, x, c: c.token_span[0] / count_tokens(info, x['text']),
            ),
            "tok_chars": feature.Value(
                dtype="float",
                description="The number of characters in a token",
                func=lambda info, x, c: len(c.text),
            ),
            # TODO(gneubig): commented out because probably less important
            # "tok_test_freq": feature.Value(
            #     dtype="float",
            #     description="tok frequency in the test set",
            #     require_training_set=False,
            #     func=...
            # ),
            "tok_train_freq": feature.Value(
                dtype="float",
                description="tok frequency in the training set",
                require_training_set=True,
                func=lambda info, x, c, stat: stat['vocab'].get(c.text, 0.0),
            ),
        }
        tok_continuous_features = [
            k
            for k, v in tok_features.items()
            if ('float' in unwrap(v.dtype))
            if k != 'tok_log_prob'
        ]
        tok_analyses: list[BucketAnalysis] = [
            BucketAnalysis(x, method="continuous") for x in tok_continuous_features
        ]

        return [
            AnalysisLevel(
                name='example',
                features=examp_features,
                metric_configs=self.default_metrics(level='example'),
                analyses=cast(List[Analysis], examp_analyses),
            ),
            AnalysisLevel(
                name='tok',
                features=tok_features,
                metric_configs=self.default_metrics(level='tok'),
                analyses=cast(List[Analysis], tok_analyses),
            ),
        ]

    def _gen_cases_and_stats(
        self,
        sys_info: SysOutputInfo,
        sys_output: list[dict],
        statistics: Any,
        analysis_level: AnalysisLevel,
    ) -> tuple[list[AnalysisCase], list[MetricStats]]:
        if analysis_level.name == 'example':
            return super()._gen_cases_and_stats(
                sys_info, sys_output, statistics, analysis_level
            )
        elif analysis_level.name != 'tok':
            raise ValueError(f'{analysis_level.name}-level analysis not supported')
        # Do tok-level analysis
        cases: list[AnalysisCaseSpan] = []
        # Calculate features
        for i, output in progress(
            enumerate(sys_output), desc='calculating tok-level features'
        ):
            # get the tokens and scores from each sentence
            toks = output["text"].split(' ')
            probs = [float(x) for x in output["log_probs"].split(' ')]
            # analysis cases
            curr_char = 0
            for j, (tok, prob) in enumerate(zip(toks, probs)):
                next_char = curr_char + len(tok)
                case = AnalysisCaseSpan(
                    sample_id=i,
                    features={'tok_log_prob': prob},
                    token_span=(j, j + 1),
                    char_span=(curr_char, next_char),
                    text=tok,
                    orig_str="source",
                )
                curr_char = next_char + 1
                for feat_name, feat_spec in analysis_level.features.items():
                    if feat_spec.func is None:
                        pass
                    elif not feat_spec.require_training_set:
                        case.features[feat_name] = feat_spec.func(
                            sys_info, output, case
                        )
                    elif statistics is not None:
                        case.features[feat_name] = feat_spec.func(
                            sys_info, output, case, statistics
                        )
                cases.append(case)
        metric_stats = [
            MetricStats(np.array([x.features['tok_log_prob'] for x in cases]))
        ]
        return cast(List[AnalysisCase], cases), metric_stats

    @classmethod
    def default_metrics(
        cls, level='example', source_language=None, target_language=None
    ) -> list[MetricConfig]:
        return [
            LogProbConfig(name='Perplexity', ppl=True),
            LogProbConfig(name='LogProb', ppl=False),
        ]

    def _get_true_label(self, data_point: dict):
        return None

    def _get_predicted_label(self, data_point: dict):
        return [float(x) for x in data_point["log_probs"].split(' ')]

    @aggregating()
    def _statistics_func(self, samples, sys_info: SysOutputInfo):
        vocab: dict[str, float] = {}
        length_fre: dict[int, float] = {}
        total_samps = 0
        tokenizer = unwrap(sys_info.source_tokenizer)
        for sample in progress(samples):
            text = sample["text"]
            tokens = tokenizer(text)
            length = len(tokens)

            length_fre[length] = length_fre.get(length, 0.0) + 1.0

            # update vocabulary
            for w in tokens:
                vocab[w] = vocab.get(w, 0.0) + 1.0

            total_samps += 1

        # the rank of each word based on its frequency
        sorted_dict = {
            key: rank
            for rank, key in enumerate(sorted(set(vocab.values()), reverse=True), 1)
        }
        vocab_rank = {k: sorted_dict[v] for k, v in vocab.items()}

        for k, v in length_fre.items():
            length_fre[k] = v * 1.0 / total_samps

        return {"vocab": vocab, "vocab_rank": vocab_rank, "length_fre": length_fre}
