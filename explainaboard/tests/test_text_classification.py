import pathlib
import os
import unittest
from explainaboard import FileType, Source, TaskType, get_loader, get_processor
from explainaboard.tests.utils import load_file_as_str

artifacts_path = os.path.dirname(pathlib.Path(__file__)) + "/artifacts/"


class TestTextClassification(unittest.TestCase):
    def test_e2e(self):

        metadata = {
            "task_name": TaskType.text_classification.value,
            "metric_names": ["Accuracy", "F1score"],
        }
        loader = get_loader(
            TaskType.text_classification,
            Source.in_memory,
            FileType.tsv,
            load_file_as_str(f"{artifacts_path}sys_out1.tsv"),
        )
        data = list(loader.load())
        processor = get_processor(TaskType.text_classification)

        sys_info = processor.process(metadata, data)

        # analysis.write_to_directory("./")
        self.assertIsNotNone(sys_info.results.fine_grained)
        self.assertGreater(len(sys_info.results.overall), 0)

    def test_training_set_dependent_features(self):
        metadata = {
            "task_name": TaskType.text_classification.value,
            "metric_names": ["Accuracy", "F1score"],
            "dataset_name": "ag_news",
            "reload_stat": False,
        }
        loader = get_loader(
            TaskType.text_classification,
            Source.in_memory,
            FileType.tsv,
            load_file_as_str(f"{artifacts_path}sys_out1.tsv"),
        )
        data = list(loader.load())
        processor = get_processor(TaskType.text_classification)

        sys_info = processor.process(metadata, data)

        # analysis.write_to_directory("./")
        self.assertIsNotNone(sys_info.results.fine_grained)
        self.assertGreater(len(sys_info.results.overall), 0)
