from enum import Enum
import os
import time
import requests
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.webdriver import WebDriver as ChromWebDriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.remote.webdriver import BaseWebDriver
from selenium.webdriver.remote.webelement import WebElement
import common.logger_utils as log_utils

class DriverType(Enum):
    """ WebDriver 类型 """
    CHROME = 1

def get_driver(type : DriverType, driver_bin : str, browser_bin : str):
    """
    初始化 WebDriver
    """
    if (type == DriverType.CHROME):
        return _get_chrome_driver(driver_bin, browser_bin)
    
    return None

def is_browser_alive(driver: BaseWebDriver) -> bool:
    """
    判断 WebDriver 启动的浏览器是否存活（未被手动关闭）
    :param driver: WebDriver 实例
    :return: True=浏览器存活，False=浏览器已关闭
    """
    try:
        # 尝试获取浏览器标题
        driver.title
        return True
    except WebDriverException:
        # 捕获到 WebDriver 异常，说明连接已断开（浏览器被关闭）
        return False

def wait_image_loaded(driver : BaseWebDriver, image : WebElement, wait_time : int):
    """
    等待图片加载完成
    """
    script = "return arguments[0].naturalWidth > 0 && arguments[0].naturalHeight > 0;"
    end_time = time.monotonic() + wait_time
    while True:
        if (driver.execute_script(script, image)):
            break
        if time.monotonic() > end_time:
            raise TimeoutException("")
        time.sleep(1)

def download_image(url : str, file_path : str) -> bool:
    """
    下载图片
    """
    try:
        # Request image (add request headers, simulate a browser, to avoid being detected by anti-scraping measures)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # Use streaming requests to prevent large images from occupying too much memory
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()  # Raise HTTP request exception（Such as 404/500）
        
        # Create save directory
        save_dir = os.path.dirname(file_path)
        if save_dir and not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)
        
        # Write to file
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        log_utils.get_logger().info(f"图片下载成功（{file_path}）")
        return True
    except Exception:
        log_utils.get_logger().exception(f"图片下载异常（{url}）")
        return False

def _get_chrome_driver(chromedriver_bin : str, chrome_bin : str) -> ChromWebDriver:
    """
    初始化 Chrome 浏览器 WebDriver
    """
    options: ChromeOptions = _get_default_chrome_options()
    options.binary_location = chrome_bin
    service: ChromeService = webdriver.ChromeService(executable_path=chromedriver_bin)
    driver:ChromWebDriver = webdriver.Chrome(service=service, options=options)
    return driver

def _get_default_chrome_options() -> ChromeOptions:
    """
    获取 Chrome 浏览器 WebDriver 默认设置
    """
    options: ChromeOptions = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    return options