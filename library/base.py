#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project: BookDownloader
File: base.py
Author: dourensei
Brief: 书库虚基类

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

from abc import ABC, abstractmethod
from io import TextIOWrapper
import logging
import os
from selenium.webdriver.remote.webdriver import BaseWebDriver
import common.logger_utils as log_utils

class BaseLibrary(ABC):
    """
    书库虚基类
    """

    _logger : logging.Logger
    _driver : BaseWebDriver
    _driver_timeout : int
    _cache_path : str
    _patch_path : str # TODO 增加补丁机制，替换下载图片
    _skip_duplicate : bool
    _book_pdf : bool

    def __init__(self, 
                 driver : BaseWebDriver,
                 driver_timeout : int=20,
                 cache_path : str="cache",
                 patch_path : str="patch",
                 skip_duplicate : bool=True,
                 book_pdf : bool=False):
        """
        构造函数
        """
        self._logger = log_utils.get_logger()
        self._driver = driver
        self._driver_timeout = driver_timeout
        self._cache_path = cache_path
        self._patch_path = patch_path
        self._skip_duplicate = skip_duplicate
        self._book_pdf = book_pdf

    def update_driver(self, driver: BaseWebDriver):
        """
        用于原进程异常退出时更新 WebDriver 对象
        """
        self._driver = driver

    def get_book(self, book_info, save_path : str) -> bool:
        """
        下载书籍到指定路径

        :param book_info: 书籍信息
        :param save_path: 保存路径
        """
        try:
            # 解析书籍信息
            if not self._analyze_book_info(book_info):
                self._logger.error("解析书籍信息失败")
                return False
            
            # 创建书籍存放目录
            book_name = self._get_book_name(book_info)
            book_path = os.path.join(save_path, book_name)
            if not os.path.isdir(book_path):
                os.makedirs(book_path, exist_ok=True)

            # 初始化缓存
            if not os.path.isdir(self._cache_path):
                os.makedirs(self._cache_path, exist_ok=True)
            if not self._init_cache(book_info):
                self._logger.error("缓存初始化失败")
                return False

            # 逐页下载书籍
            failed_page_list = []
            book_page_count = self._get_book_page_count(book_info)
            for i in range(1, 1 + book_page_count):
                skip = False
                # 跳过已下载完成的书籍页
                if not skip and self._is_book_page_downloaded(book_info, i, book_path):
                    self._logger.info(f"跳过已下载的第 {i}/{book_page_count} 页")
                    skip = True

                # 打开书籍页
                if not skip and not self._open_book_page(book_info, i, book_path):
                    self._logger.error(f"打开第 {i} 页失败")
                    failed_page_list.append(i)
                    skip = True
                
                # 下载书籍页
                if not skip and not self._get_book_page(book_info, i, book_path):
                    self._logger.error(f"下载第 {i} 页失败")
                    failed_page_list.append(i)
                    skip = True

                # 下载书籍页收尾处理
                if not self._post_get_book_page(book_info, i, book_path):
                    self._logger.error(f"下载第 {i} 页收尾处理失败")

            # 检查结果
            if len(failed_page_list) > 0:
                log_utils.logger_pprint(failed_page_list,
                                        level=logging.ERROR,
                                        msg_prefix="以下书籍页未能成功获取：")
                return False
            
            # 生成全书 PDF 文件
            if self._book_pdf:
                self._logger.info(f'正在生成“{book_name}” 全书 PDF 文件...')
                if not self._create_book_pdf(book_info, book_path):
                    self._logger.error("生成全书 PDF 文件失败")
                    # return False  # 到这一步说明下载已全部完成，自动重试的意义不大

            # 生成书籍目录文件
            if not self._output_book_contents(book_info, book_path):
                self._logger.error("生成书籍目录文件失败")
            else:
                self._logger.info("生成书籍目录文件成功")

            return True
        except Exception:
            self._logger.exception("下载书籍异常")
            return False
        finally:
            # 更新缓存
            if not self._update_cache(book_info):
                self._logger.error("缓存更新失败")

    @abstractmethod
    def _analyze_book_info(self, book_info) -> bool:
        """
        解析书籍信息

        :param book_info: 书籍信息
        """
        return False
    
    @abstractmethod
    def _get_book_name(self, book_info) -> str:
        """
        获取书籍名

        :param book_info: 书籍信息
        """
        return ""
    
    @abstractmethod
    def _get_book_page_count(self, book_info) -> int:
        """
        获取书籍总页数

        :param book_info: 书籍信息
        """
        return 0
    
    @abstractmethod
    def _output_book_contents(self, book_info, save_path : str="") -> bool:
        """
        输出书籍目录

        :param book_info: 书籍信息
        :param save_path: 输出文件保存文件夹路径，省略时输出到控制台
        """
        return False
    
    @abstractmethod
    def _init_cache(self, book_info) -> bool:
        """
        初始化缓存

        :param book_info: 书籍信息
        """
        return False
    
    @abstractmethod
    def _update_cache(self, book_info) -> bool:
        """
        更新缓存

        :param book_info: 书籍信息
        """
        return False
    
    @abstractmethod
    def _post_get_book_page(self, book_info, page : int, book_path : str) -> bool:
        """
        下载书籍页后处理

        :param book_info: 书籍信息
        :param page: 页码（从 1 开始）
        :param book_path: 书籍下载路径
        """
        return False
    
    @abstractmethod
    def _open_book_page(self, book_info, page : int, book_path : str) -> bool:
        """
        打开书籍页

        :param book_info: 书籍信息
        :param page: 页码（从 1 开始）
        :param book_path: 书籍下载路径
        """
        return False
    
    @abstractmethod
    def _get_book_page(self, book_info, page : int, book_path : str) -> bool:
        """
        下载书籍页

        :param book_info: 书籍信息
        :param page: 页码（从 1 开始）
        :param book_path: 书籍下载路径
        """
        return False
    
    @abstractmethod
    def _is_book_page_downloaded(self, book_info, page : int, book_path : str) -> bool:
        """
        检查书籍页是否已下载

        :param book_info: 书籍信息
        :param page: 页码（从 1 开始）
        :param book_path: 书籍下载路径
        """
        return False

    @abstractmethod
    def _create_book_pdf(self, book_info, book_path : str) -> bool:
        """
        生成全书 PDF 文件

        :param book_info: 书籍信息
        :param book_path: 书籍下载路径
        """
        return False