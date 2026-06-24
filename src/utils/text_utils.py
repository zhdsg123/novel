"""
文本处理工具模块
提供文本分片、字数统计、TXT 导出等功能。
"""

import re
from datetime import datetime


def count_words(text: str) -> int:
    """统计中文字数（中文字符 + 标点按字符数计）。"""
    if not text:
        return 0
    # 中文字符、中文标点、英文单词
    chinese_chars = len(re.findall(r'[一-鿿　-〿＀-￯]', text))
    english_words = len(re.findall(r'[a-zA-Z]+', text))
    return chinese_chars + english_words


def split_text(text: str, chunk_size: int = 500) -> list[str]:
    """
    将长文本按 chunk_size 字分片，尽量在段落边界切割。
    用于向量知识库的文本入库。
    """
    if not text:
        return []

    paragraphs = text.split('\n')
    chunks = []
    current_chunk = ""
    current_len = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_len = count_words(para)

        if current_len + para_len <= chunk_size:
            current_chunk += para + '\n'
            current_len += para_len
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # 如果单段落超过 chunk_size，强制按字符切分
            if para_len > chunk_size:
                sub_chunks = _force_split(para, chunk_size)
                chunks.extend(sub_chunks)
                current_chunk = ""
                current_len = 0
            else:
                current_chunk = para + '\n'
                current_len = para_len

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def _force_split(text: str, chunk_size: int) -> list[str]:
    """按固定长度强制切分文本。"""
    result = []
    for i in range(0, len(text), chunk_size):
        result.append(text[i:i + chunk_size])
    return result


def export_txt(content: str, filename: str = None) -> bytes:
    """
    将小说内容导出为 TXT 格式的字节流。
    自动添加 UTF-8 BOM 确保 Windows 记事本兼容。
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"小说章节_{timestamp}.txt"
    bom = '﻿'
    return (bom + content).encode('utf-8'), filename


def extract_title_hint(text: str) -> str:
    """从章节文本中提取可能的章节标题。"""
    lines = text.strip().split('\n')
    for line in lines[:5]:
        line = line.strip()
        if line and len(line) < 30:
            return line
    return f"章节_{datetime.now().strftime('%m%d')}"
