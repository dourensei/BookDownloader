#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project: BookDownloader
File: main.py
Author: dourensei
Brief: 主函数

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

import argparse
import atexit
import json
import logging
import sys
import os
import common.driver_utils as drv_utils
import common.logger_utils as log_utils
import common.utils as utils
from library.base import BaseLibrary
from library.tianyige import TianyigeLibrary

def _parse_args():
    """解析命令行参数"""

    if hasattr(sys, '_MEIPASS'):
        execute_info = "BookDownloader.exe"
    else:
        execute_info = "python main.py"

    parser = argparse.ArgumentParser(
        description="BookDownloader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
示例用法：
  {execute_info} -w "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" -d "D:\\chromedriver.exe" -b "D:\\book.json"
        """
    )

    prog_path = os.environ.get("PROGRAMFILES", "C:\\Program Files")

    # 浏览器 EXE 路径
    parser.add_argument(
        '-w', '--browser',
        type=str,
        default=os.path.join(prog_path, "Google\\Chrome\\Application\\chrome.exe"),
        help='浏览器 EXE 文件路径（默认：%%ProgramFiles%%\\Chrome\\Application\\chrome.exe）'
    )

    # WebDriver EXE 路径
    parser.add_argument(
        '-d', '--driver',
        type=str,
        default="chromedriver.exe",
        help='浏览器适配 WebDriver EXE 文件路径（默认：.\\chromedriver.exe）'
    )

    # 下载书籍信息文件路径
    parser.add_argument(
        '-b', '--book',
        type=str,
        default="book.json",
        help='下载书籍信息文件路径（默认：.\\book.json）'
    )

    # 书籍下载文件夹路径
    parser.add_argument(
        '-s', '--save',
        type=str,
        default="download",
        help='书籍下载文件夹路径（默认：.\\download）'
    )

    # 下载缓存文件夹路径
    parser.add_argument(
        '-c', '--cache',
        type=str,
        default="cache",
        help='书籍下载缓存文件夹路径（默认：.\\cache）'
    )

    # 补丁文件夹路径
    parser.add_argument(
        '-p', '--patch',
        type=str,
        default="patch",
        help='补丁文件夹路径（默认：.\\patch）'
    )

    # 自动重试
    parser.add_argument(
        '-n', '--no-retry',
        action='store_true',
        help='下载失败时不自动重试（默认会自动重试直至书籍全部下载成功）'
    )

    # 保留重复页
    parser.add_argument(
        '-k', '--keep-duplicate',
        action='store_true',
        help='生成 PDF 文件时保留重复页（默认会自动删除重复页）'
    )

    # 创建全书 PDF 文件
    parser.add_argument(
        '-f', '--book-pdf',
        action='store_true',
        help='创建全书 PDF 文件（默认只生成拆分的 PDF 文件）'
    )

    args = parser.parse_args()

    return args

def _main():
    """
    主函数
    """
    try:
        driver = None

        # 初始化日志器（仅在此处执行一次）
        logger = log_utils.setup_logger()

        # 启动防休眠
        utils.keep_awake()
        # 程序退出时自动停止
        atexit.register(utils.stop_keep_awake)

        # 解析命令行参数
        args = _parse_args()
        log_utils.logger_pprint(args,
                                level=logging.INFO,
                                msg_prefix="本次运行参数如下：")

        driver_path : str = os.path.abspath(args.driver)
        browser_path : str  = os.path.abspath(args.browser)
        book_info_file : str  = args.book
        download_path : str  = args.save
        cache_path : str  = args.cache
        patch_path : str  = args.patch
        no_retry : bool  = args.no_retry
        skip_duplicate : bool = not args.keep_duplicate
        create_book_pdf : bool = args.book_pdf

        # 初始化 WebDriver
        try:
            if "chrome" in driver_path.lower() and "chrome" in browser_path.lower():
                driver = drv_utils.get_driver(drv_utils.DriverType.CHROME, driver_path, browser_path)
            else:
                logger.error("不支持该浏览器")
                return
        except Exception:
            logger.exception("WebDriver 初始化异常")
            return

        # 加载书籍信息文件
        try:
            with open(book_info_file, "r", encoding="utf8") as f:
                book_info = json.load(f)

            book_url = book_info["url"]
        except Exception:
            logger.exception("加载书籍信息文件异常")
            return

        # 判断书库
        library : BaseLibrary = None
        if "tianyige.com.cn" in book_url:
            library = TianyigeLibrary(driver, 
                                      cache_path=cache_path, 
                                      patch_path=patch_path, 
                                      skip_duplicate=skip_duplicate,
                                      create_book_pdf=create_book_pdf)
        else:
            logger.error("不支持该书库")
            return

        # 下载书籍
        while True:
            # 浏览器进程已异常退出时，重新启动
            if not drv_utils.is_browser_alive(driver):
                logger.warning("浏览器异常退出，重新启动 WebDriver")
                try:
                    driver = drv_utils.get_driver(drv_utils.DriverType.CHROME, driver_path, browser_path)
                    library.update_driver(driver)
                except Exception:
                    logger.exception("WebDriver 初始化异常")
                    return

            logger.info("开始下载书籍")

            if library.get_book(book_info, download_path):
                logger.info("下载书籍成功")
                break
            else:
                logger.error("下载书籍失败")
                if no_retry:
                    break
    except Exception:
        logger.exception("主函数异常")
    finally:
        # 停止防休眠
        utils.stop_keep_awake()

        # 退出 WebDriver
        if driver is not None:
            driver.quit()

if __name__ == "__main__":
    # 强制将当前工作目录切换到程序基础目录
    base_path = utils.get_base_path(__file__)
    os.chdir(base_path)
    print(base_path)

    # 确保子模块能被导入（兼容exe打包）
    sys.path.append(base_path)

    # 主函数
    _main()