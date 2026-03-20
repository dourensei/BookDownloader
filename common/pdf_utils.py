#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project: BookDownloader
File: pdf_utils.py
Author: dourensei
Brief: PDF 文件处理函数

Copyright (c) 2026 dourensei

MIT License
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import img2pdf
from PyPDF2 import PdfReader, PdfWriter
import common.logger_utils as log_utils

def images_to_pdf(image_paths : list[str], pdf_path: str) -> bool:
    """
    将图片转为 PDF 文件

    :param image_paths: 图片文件路径列表（必须按页码排序）
    :param pdf_path: PDF 文件保存路径
    """
    if not image_paths:
        return False
    
    try:
        # 原先用 PILImage 进行转换在图片较多较大时可能会导致内存不足，因此改用 img2pdf
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(image_paths))

        log_utils.get_logger().info(f"创建 PDF 文件成功（{pdf_path}）")
        return True
    except Exception:
        log_utils.get_logger().exception(f"创建 PDF 文件异常（{pdf_path}）")
        return False

def add_pdf_outline(pdf_temp_path, pdf_final_path, outline_items) -> bool:
    """
    为 PDF 文件添加目录

    :param pdf_temp_path: 无目录 PDF 文件路径
    :param pdf_final_path: 添加目录后的 PDF 文件保存路径
    :param outline_items: 目录信息列表，格式为：
        [
            {"title": "1", "page": 1, "level": 0},
            {"title": "2", "page": 2, "level": 0},
            {"title": "2-1", "page": 2, "level": 1},
        ]
    """
    try:
        # 读取无目录 PDF 文件
        reader = PdfReader(pdf_temp_path)
        writer = PdfWriter()
        
        # 复制所有页
        for page in reader.pages:
            writer.add_page(page)
        
        # 创建目录
        parent_map = {0: None}  # 记录每级目录的父书签（level: 父书签对象）
        for item in outline_items:
            title = item["title"]
            page_num = item["page"] - 1  # PyPDF2 页码从 0 开始
            level = item.get("level", 0)
            
            # 添加书签
            bookmark = writer.add_outline_item(
                title=title,
                page_number=page_num,
                parent=parent_map.get(level - 1)
            )
            
            # 记录书签，作为下一级目录的父书签
            parent_map[level] = bookmark
        
        # 保存 PDF 文件
        with open(pdf_final_path, "wb") as f:
            writer.write(f)
        
        log_utils.get_logger().info(f"创建 PDF 文件成功（{pdf_final_path}）")
        return True
    except Exception:
        log_utils.get_logger().exception(f"创建 PDF 文件异常（{pdf_final_path}）")
        return False