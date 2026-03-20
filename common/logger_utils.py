#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project: BookDownloader
File: logger_utils.py
Author: dourensei
Brief: 日志相关函数

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

import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import pprint
from typing import Any

# 定义全局默认日志器名称
DEFAULT_LOGGER_NAME = "app_main_logger"

def setup_logger(
    name: str = DEFAULT_LOGGER_NAME,
    log_file: str = "logs/log.txt",
    max_bytes: int = 50 * 1024 * 1024,  # 50MB
    backup_count: int = 5,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG
) -> logging.Logger:
    """
    初始化日志器：支持控制台+文件输出、按大小拆分、分级输出
    """
    # 获取日志器实例（单例）
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # 总等级需低于所有处理器
    logger.handlers.clear()  # 清空重复处理器，避免日志重复输出

    # 定义日志格式（包含模块、行号，便于定位问题）
    formatter = logging.Formatter(
        "[%(asctime)s] | %(levelname)-7s | %(module)-15s | %(lineno)-5d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. 配置文件处理器（按大小拆分）
    # 自动创建日志目录（兼容exe打包后的路径）
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"  # 避免中文乱码
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 2. 配置控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

def get_logger(name: str = DEFAULT_LOGGER_NAME) -> logging.Logger:
    """
    获取已初始化的日志器实例
    """
    return logging.getLogger(name)

def logger_pprint(
    obj: Any,
    name: str = DEFAULT_LOGGER_NAME,
    level: int = logging.INFO,
    msg_prefix: str = "",
    indent: int = 2,
    ensure_ascii: bool = False
) -> None:
    """
    封装pprint功能，将美观格式化的对象输出到日志
    :param obj: 要格式化的对象（字典/列表/对象等）
    :param name: 日志器名称
    :param level: 日志等级（整数，如logging.INFO/logging.DEBUG等）
    :param msg_prefix: 日志前缀提示语
    :param indent: 缩进空格数
    :param ensure_ascii: 是否强制ASCII（False支持中文）
    """
    # 校验等级合法性，默认降级为INFO
    valid_levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
    if level not in valid_levels:
        level = logging.INFO
        logger.warning(f"无效的日志等级 {level}，已自动降级为 INFO")
    
    # 将对象转为美观的字符串
    pretty_str = pprint.pformat(obj, indent=indent)

    # 拼接前缀信息
    log_msg = f"{msg_prefix}\n{pretty_str}" if msg_prefix else pretty_str
    
    # 根据等级输出日志
    logger = get_logger(name)
    logger.log(level, log_msg)
