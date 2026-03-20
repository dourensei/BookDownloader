#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project: BookDownloader
File: image_utils.py
Author: dourensei
Brief: 图片文件处理相关函数

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

from PIL import Image as PILImage
import common.logger_utils as log_utils

def _calculate_merged_image_size(tiles : list[PILImage.Image], rows : int, cols : int) -> tuple:
    """
    计算合并图片的宽度和高度

    :param tiles: 小图列表 (PIL.Image.Image 对象)
    :param rows: 行数
    :param cols: 列数
    :return: (总宽度, 总高度)
    """
    # 将小图按行分组
    rows_tiles : list[list[PILImage.Image]] = []
    row_tile : list[PILImage.Image] = []
    for tile in tiles:
        row_tile.append(tile)
        if len(row_tile) == cols:
            rows_tiles.append(row_tile[:])
            row_tile.clear()

            if len(rows_tiles) == rows:
                break
    
    if len(row_tile) > 0:
        # 小图铺不满最后一行的情况
        rows_tiles.append(row_tile)
    
    # 计算每行的宽度和高度
    row_widths = []   # 每行的宽度
    row_heights = []  # 每行的高度
    for row_tile in rows_tiles:
        # 计算宽度
        current_row_width = sum([tile.width for tile in row_tile])
        row_widths.append(current_row_width)
        
        # 计算高度
        current_row_height = max([tile.height for tile in row_tile])
        row_heights.append(current_row_height)
    
    # 计算总宽度和总高度
    total_width = max(row_widths)
    total_height = sum(row_heights)
    
    return total_width, total_height

def merge_images(tile_paths : list[str], rows : int, cols : int, output_path : str) -> bool:
    """
    将一组小图合并成大图

    :param tile_paths: 小图文件路径列表（必须按 R1C1, R1C2, ..., R2C1, ... 排序）
    :param rows: 行数
    :param cols: 列数
    :param output_path: 大图的保存路径
    """
    try:
        # 读取所有小图
        tiles : list[PILImage.Image] = []
        for path in tile_paths:
            image = PILImage.open(path).convert("RGB")
            tiles.append(image)
        
        # 计算合并后大图的宽度和高度
        big_width, big_height = _calculate_merged_image_size(tiles, rows, cols)
        
        # 创建空白大图（RGB，白色背景）
        big_img = PILImage.new("RGB", (big_width, big_height), (255, 255, 255))
        
        # 逐行合并小图
        current_x = 0
        current_y = 0
        max_row_height = 0

        for idx, tile in enumerate(tiles):
            tile_w, tile_h = tile.size
            
            # 将小图复制到大图
            big_img.paste(tile, (current_x, current_y))
            
            # 累加 x 坐标和行高
            current_x += tile_w
            max_row_height = max(max_row_height, tile_h)
            
            # 当一行达到列数，重置 x 坐标，累加 y 坐标
            if (idx + 1) % cols == 0:
                current_x = 0
                current_y += max_row_height
                max_row_height = 0
        
        # 保存大图
        big_img.save(output_path)

        log_utils.get_logger().info(f"图片合并成功（{output_path}）")
        return True
    except Exception:
        log_utils.get_logger().exception(f"图片合并异常（{output_path}）")
        return False