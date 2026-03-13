# main.py
import atexit
import json
import sys
import os
import common.driver_utils as drv_utils
import common.logger_utils as log_utils
import common.utils as utils
from library.base import BaseLibrary
from library.tianyige import TianyigeLibrary

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

        # TODO 支持命令行参数
        # Set browser driver path
        driver_path = "D:\\tools\\chromedriver-win64\\chromedriver.exe"
        # Set browser path
        browser_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        # Set book information file path
        book_info_file = os.path.join(os.path.curdir, "book.json")
        # Set downloading path
        download_path = os.path.join(os.path.curdir, "download")
        auto_retry = True

        # 初始化 WebDriver
        try:
            driver = drv_utils.get_driver(drv_utils.DriverType.CHROME, driver_path, browser_path)
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
            library = TianyigeLibrary(driver)
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
                if auto_retry:
                    logger.error("下载书籍失败")
                else:
                    logger.error("下载书籍失败")
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
    base_path = utils.get_base_path()
    os.chdir(base_path)

    # 确保子模块能被导入（兼容exe打包）
    sys.path.append(base_path)

    # 主函数
    _main()