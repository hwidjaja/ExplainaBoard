from explainaboard.constants import FileType
from explainaboard.loaders.file_loader import (
    DatalabFileLoader,
    FileLoader,
    FileLoaderField,
    JSONFileLoader,
)
from explainaboard.loaders.loader import Loader
from explainaboard.loaders.loader_registry import register_loader
from explainaboard.tasks import TaskType


@register_loader(TaskType.question_answering_extractive)
class QAExtractiveLoader(Loader):
    @classmethod
    def default_dataset_file_type(cls) -> FileType:
        return FileType.json

    @classmethod
    def default_output_file_type(cls) -> FileType:
        return FileType.json

    @classmethod
    def default_dataset_file_loaders(cls) -> dict[FileType, FileLoader]:
        target_field_names = ["context", "question", "answers", "predicted_answers"]
        return {
            FileType.json: JSONFileLoader(
                [
                    FileLoaderField(
                        target_field_names[0],
                        target_field_names[0],
                        str,
                        strip_before_parsing=False,
                    ),
                    FileLoaderField(
                        target_field_names[1],
                        target_field_names[1],
                        str,
                        strip_before_parsing=False,
                    ),
                    FileLoaderField(target_field_names[2], target_field_names[2]),
                ]
            ),
            FileType.datalab: DatalabFileLoader(
                [
                    FileLoaderField(
                        "context",
                        target_field_names[0],
                        str,
                        strip_before_parsing=False,
                    ),
                    FileLoaderField(
                        "question",
                        target_field_names[1],
                        str,
                        strip_before_parsing=False,
                    ),
                    FileLoaderField("answers", target_field_names[2]),
                ]
            ),
        }

    @classmethod
    def default_output_file_loaders(cls) -> dict[FileType, FileLoader]:
        return {
            FileType.json: JSONFileLoader(
                [FileLoaderField("predicted_answers", "predicted_answers")]
            )
        }
