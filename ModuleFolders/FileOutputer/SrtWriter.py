from functools import partial
from itertools import count
from pathlib import Path
from typing import Callable, Iterator
import re # 导入 re 模块

from ModuleFolders.Cache.CacheFile import CacheFile
from ModuleFolders.Cache.CacheItem import CacheItem
from ModuleFolders.Cache.CacheProject import ProjectType
from ModuleFolders.FileOutputer.BaseWriter import (
    BaseBilingualWriter,
    BaseTranslatedWriter,
    OutputConfig,
    PreWriteMetadata
)


class SrtWriter(BaseBilingualWriter, BaseTranslatedWriter):
    def __init__(self, output_config: OutputConfig):
        super().__init__(output_config)

    def on_write_bilingual(
        self, translation_file_path: Path, cache_file: CacheFile,
        pre_write_metadata: PreWriteMetadata,
        source_file_path: Path = None,
    ):
        _yield_bilingual_block = partial(self._yield_bilingual_block, counter=count(1))
        self._write_translation_file(translation_file_path, cache_file, pre_write_metadata, _yield_bilingual_block)

    def on_write_translated(
        self, translation_file_path: Path, cache_file: CacheFile,
        pre_write_metadata: PreWriteMetadata,
        source_file_path: Path = None,
    ):
        self._write_translation_file(translation_file_path, cache_file, pre_write_metadata, self._yield_translated_block)

    def _write_translation_file(
        self, translation_file_path: Path, cache_file: CacheFile,
        pre_write_metadata: PreWriteMetadata,
        yield_block: Callable[[CacheItem], Iterator[list[str]]]
    ):
        output = []
        for item in cache_file.items:
            if not item.source_text or not item.translated_text:
                continue
            for block in yield_block(item):
                output.append("\n".join(block).strip())
        if output:
            translation_file_path.write_text("\n\n".join(output), encoding=pre_write_metadata.encoding)

    def _map_to_translated_item(self, item: CacheItem):
        translated_text = item.translated_text.strip()
        # 将所有目标标点和空格替换为单个空格
        translated_text = re.sub(r'[，,。.\s]+', ' ', translated_text)
        # 去除可能因替换产生的行首和行尾多余空格 (如果re.sub的目标是' '，则不需要再次strip)
        # translated_text = translated_text.strip() # 如果上面re.sub的目标是' '，则这行可以不需要
        block = [
            str(item.require_extra("subtitle_number")),
            item.require_extra("subtitle_time"),
            translated_text, # 使用替换后的文本
            "",
        ]
        return block

    def _yield_bilingual_block(self, item: CacheItem, counter: count):
        if self._strip_text(item.source_text):
            number = next(counter)
            # 对于双语模式，同样处理原文中的标点 (如果需要)
            # source_text_processed = re.sub(r'[，,。.\s]+', ' ', item.source_text.strip())
            # 为了保持原文的准确性，这里不对 source_text 进行标点替换，如有需要可以取消注释上方代码
            original_block = [
                str(number),
                item.require_extra("subtitle_time"),
                item.source_text.strip(), # 使用原始未处理的原文
                "",
            ]
            yield original_block
        if self._strip_text(item.translated_text):
            number = next(counter)
            translated_block = self._map_to_translated_item(item) # 调用已修改的方法处理译文
            translated_block[0] = str(number)
            yield translated_block

    def _strip_text(self, text: str):
        return (text or "").strip()

    def _yield_translated_block(self, item: CacheItem):
        yield self._map_to_translated_item(item)

    @classmethod
    def get_project_type(self):
        return ProjectType.SRT
