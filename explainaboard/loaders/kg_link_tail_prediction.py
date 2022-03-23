from typing import Dict, Iterable, List
from explainaboard.constants import FileType
from explainaboard.loaders.file_loader import JSONFileLoader
from explainaboard.tasks import TaskType
from .loader import register_loader
from .loader import Loader


@register_loader(TaskType.kg_link_tail_prediction)
class KgLinkTailPredictionLoader(Loader):
    """
    Validate and Reformat system output file with json format:
    "head \t relation \t trueTail": [predTail1, predTail2, predTail3, predTail4, predTail5],

    usage:
        please refer to `test_loaders.py`
    """

    _default_file_type = FileType.json
    _default_file_loaders = {FileType.json: JSONFileLoader(None, False)}

    def load(self) -> Iterable[Dict]:
        """
        :param path_system_output: the path of system output file with following format:
        "head \t relation \t trueTail": [predTail1, predTail2, predTail3, predTail4, predTail5],

        :return: class object
        """
        data: List[Dict] = []
        if self._file_type == FileType.json:
            raw_data = self._default_file_loaders[FileType.json].load_raw(
                self._data, self._source
            )
            if self.user_defined_features_configs:  # user defined features are present
                for id, (link, features_dict) in enumerate(raw_data.items()):

                    data_i = {
                        "id": str(id),  # should be string type
                        "link": link.strip(),
                        "relation": link.split('\t')[1].strip(),
                        "true_head": link.split('\t')[0].strip(),
                        "true_tail": link.split('\t')[-1].strip(),
                        "predicted_tails": features_dict["predictions"],
                    }

                    # additional user-defined features
                    data_i.update(
                        {
                            feature_name: features_dict[feature_name]
                            for feature_name in self.user_defined_features_configs
                        }
                    )

                    data.append(data_i)
            else:
                for id, (link, predictions) in enumerate(raw_data.items()):
                    data.append(
                        {
                            "id": str(id),  # should be string type
                            "link": link.strip(),
                            "relation": link.split('\t')[1].strip(),
                            "true_head": link.split('\t')[0].strip(),
                            "true_tail": link.split('\t')[-1].strip(),
                            "predicted_tails": predictions,
                        }
                    )
        else:
            raise NotImplementedError
        return data
