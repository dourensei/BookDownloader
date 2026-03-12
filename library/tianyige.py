from collections import defaultdict
from io import TextIOWrapper
import json
import logging
import os
from typing import Any
from selenium.webdriver.remote.webdriver import BaseWebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import common.driver_utils as drv_utils
import common.image_utils as img_utils
import common.logger_utils as log_utils
import common.pdf_utils as pdf_utils
import common.utils as utils
from library.base import BaseLibrary

class TianyigeLibrary(BaseLibrary):
    """
    天一阁书库类
    """

    _url_cache_file_name : str
    _url_duplicate_file_name : str
    _split_image_min_size : int
    _split_image_rows : int
    _split_image_cols : int
    _split_image_count : int
    _image_url_cache : Any
    _failed_download_list : list
    _warned_download_list : list
    _last_opened_page_url : str
    _last_failed_page_url : str
    _last_fascicle_id : str
    _last_fascicle_name : str
    _last_fascicle_path : str

    def __init__(self, 
                 driver: BaseWebDriver,
                 driver_timeout: int=20,
                 cache_path: str="cache",
                 patch_path: str="patch"):
        """
        构造函数
        """
        super().__init__(driver, driver_timeout, cache_path, patch_path)

        self._url_cache_file_name = "url.json"
        self._url_duplicate_file_name = "url_duplicate.txt"
        self._split_image_min_size = 1024 * 50
        self._split_image_rows = 2
        self._split_image_cols = 4
        self._split_image_count = self._split_image_rows * self._split_image_cols
        self._image_url_cache = None

    def get_book(self, book_info, save_path : str) -> bool:
        """
        下载书籍到指定路径

        :param book_info: 书籍信息
        :param save_path: 保存路径
        """
        # 下载相关成员变量重置
        self._failed_download_list = []
        self._warned_download_list = []
        self._last_opened_page_url = ""
        self._last_failed_page_url = ""
        self._last_fascicle_id = ""
        self._last_fascicle_name = ""
        self._last_fascicle_path = ""

        # 下载书籍
        result = super().get_book(book_info, save_path)

        try:
            # 输出具体下载错误信息
            if len(self._warned_download_list) > 0:
                print("[Warning] The following images maybe incorrect.")
                info_list = [f'Page:{info["pageNum"]}, index:{info["index"]}, url:{info["url"]}'
                            for info in self._warned_download_list]
                log_utils.logger_pprint(info_list,
                                        level=logging.WARNING,
                                        msg_prefix="以下图片可能没有下载完整：")

            if len(self._failed_download_list) > 0:
                info_list = [f'Page:{info["pageNum"]}, index:{info["index"]}, url:{info["url"]}'
                            for info in self._failed_download_list]
                log_utils.logger_pprint(info_list,
                                        level=logging.ERROR,
                                        msg_prefix="以下图片下载失败：")

            # 检查是否存在图片相同的页
            url_duplicate_file = os.path.join(self._cache_path, self._url_duplicate_file_name)
            duplicate_list = self._check_duplicate_image_url(book_info)
            if len(duplicate_list) > 0:
                log_utils.logger_pprint(duplicate_list,
                                        level=logging.WARNING,
                                        msg_prefix="以下书籍页的内容相同：")
                duplicate_info = "\n".join(duplicate_list)
                with open(url_duplicate_file, "w+", encoding="utf8") as f:
                    f.write(duplicate_info)
            else:
                os.remove(url_duplicate_file)
        except Exception:
            self._logger.exception("下载书籍异常")

        return result

    def _analyze_book_info(self, book_info) -> bool:
        """
        解析书籍信息

        :param book_info: 书籍信息
        """
        # 获取基本信息
        book_name = utils.get_valid_path_name(book_info["name"])
        book_author = book_info["author"]
        book_id = book_info["catalogId"]
        book_fascicles = book_info["fascicle"]
        book_directories = book_info["directory"]
        book_images = book_info["image"]
        book_info["name"] = book_name
        book_info["pageCount"] = len(book_images)
        book_info["maxPageNumLen"] = len(str(len(book_images)))
        self._logger.info(f"书名: {book_name}")
        self._logger.info(f"作者: {book_author}")
        self._logger.info(f"分卷数: {len(book_fascicles)}")
        self._logger.info(f"总页数: {len(book_images)}")

        # 检查是否存在重复
        if not self._check_duplicate_data(book_fascicles, book_directories, book_images):
            print("请确认书籍信息文件是否正确。")
            answer = input("是否忽略并继续？(y/n):").lower()
            if not (answer == "y" or answer == "yes"):
                return False

        # 解析层级关系（书籍 -> 分卷 -> 章节 -> 页）
        page_num = 1
        used_fascicle_names = []
        fascicle_list = [f for f in book_fascicles if f["catalogId"] == book_id]
        for fascicle in fascicle_list:
            page_count = 0

            # 更新分卷名，防止重名和存在无效字符
            fascicle["name"] = utils.get_valid_path_name(fascicle["name"], used_fascicle_names)
            used_fascicle_names.append(fascicle["name"])

            # 记录分卷起始页
            fascicle["pageNum"] = page_num

            # 获取章节列表
            dir_list = [d for d in book_directories 
                        if d["catalogId"] == book_id
                        and d["fascicleId"] == fascicle["fascicleId"]]
            
            # 解析章节
            used_dir_names = []
            for dir in dir_list:
                # 更新章节名，防止重名和存在无效字符
                dir["name"] = utils.get_valid_path_name(dir["name"], used_dir_names)
                used_dir_names.append(dir["name"])

                # 记录章节起始页
                dir["pageNum"] = page_num

                # 获取页列表
                image_list = [i for i in book_images
                            if i["catalogId"] == book_id
                            and i["fascicleId"] == fascicle["fascicleId"]
                            and i["directoryId"] == dir["directoryId"]]
                
                # 添加页属性
                for image in image_list:
                    image["catalogName"] = book_name
                    image["fascicleName"] = fascicle["name"]
                    image["directoryName"] = dir["name"]
                    image["pageNum"] = page_num
                    page_num += 1
                
                # 将页列表添加为章节的属性
                # dir["image"] = image_list

                # 记录章节页数
                dir["pageCount"] = len(image_list)
                page_count += len(image_list)
            
            # 记录分卷页数
            fascicle["pageCount"] = page_count
            if page_count != fascicle["imageCount"]:
                self._logger.warning(f'书籍信息中{fascicle["name"]}的页数不正确')

            # 将章节列表添加为分卷的属性
            # fascicle["directory"] = dir_list
        
        return True
    
    def _get_book_name(self, book_info) -> str:
        """
        获取书籍名

        :param book_info: 书籍信息
        """
        return book_info["name"]
    
    def _get_book_page_count(self, book_info) -> int:
        """
        获取书籍总页数

        :param book_info: 书籍信息
        """
        return book_info["pageCount"]
    
    def _output_book_contents(self, book_info, file : TextIOWrapper=None) -> bool:
        """
        输出书籍目录

        :param book_info: 书籍信息
        :param file: 输出文件对象，省略时输出到控制台
        """
        book_contents = self._generate_book_contents(book_info)
        utils.print_tree_structure(book_contents, file)

        return True
    
    def _init_cache(self, book_info) -> bool:
        """
        初始化缓存

        :param book_info: 书籍信息
        """
        try:
            book_id = book_info["catalogId"]
            max_page_num_len = book_info["maxPageNumLen"]

            # 创建 URL 缓存
            url_cache_file = os.path.join(self._cache_path, self._url_cache_file_name)
            if utils.is_valid_file(url_cache_file, 1):
                # 加载已存在的缓存文件
                with open(url_cache_file, "r", encoding="utf8") as f:
                    self._image_url_cache = json.load(f)
                    if not book_id in self._image_url_cache.keys():
                        self._image_url_cache[book_id] = {}

                    # 确保页码位数统一，以便于保存时进行正确排序
                    url_dict = self._image_url_cache[book_id]
                    old_keys = [ k for k in self._image_url_cache[book_id].keys()]
                    new_keys = [ str(int(k)).zfill(max_page_num_len) for k in old_keys]
                    for i, k in enumerate(old_keys):
                        if k != new_keys[i]:
                            url_dict[new_keys[i]] = url_dict.pop(k)
            else:
                self._image_url_cache = { book_id: {} }
            
            return True
        except Exception:
            self._logger.exception("初始化缓存异常")
            return False
    
    def _update_cache(self, book_info) -> bool:
        """
        更新缓存

        :param book_info: 书籍信息
        """
        try:
            # 保存 URL 缓存
            url_cache_file = os.path.join(self._cache_path, self._url_cache_file_name)
            with open(url_cache_file, "w", encoding="utf8") as file:
                json.dump(self._image_url_cache, file, indent=4, sort_keys=True)

            return True
        except Exception:
            self._logger.exception("更新缓存异常")
            return False
    
    def _check_duplicate_image_url(self, book_info) -> list:
        """
        检查是否存在重复的图片 URL
        """
        book_id = book_info["catalogId"]
        duplicate_list = []

        if self._image_url_cache is not None:
            url_to_index = defaultdict(list)
            for index, url in self._image_url_cache[book_id].items():
                url_to_index[url].append(index)

            for url, index_list in url_to_index.items():
                if len(index_list) > 1:
                    index_list.sort()
                    duplicate_list.append("图片相同的页：" + ", ".join(index_list))

            duplicate_list.sort()

        return duplicate_list
    
    def _pre_open_book_page(self, book_info, page : int, book_path : str) -> bool:
        """
        打开书籍页预处理

        :param book_info: 书籍信息
        :param page: 页码（从 1 开始）
        :param book_path: 书籍下载路径
        """
        try:
            max_page_num_len = book_info["maxPageNumLen"]
            book_fascicles = book_info["fascicle"]
            book_directories = book_info["directory"]
            book_images = book_info["image"]
            image = book_images[page - 1]

            # 获取下载路径
            filled_page_num = str(image["pageNum"]).zfill(max_page_num_len)
            fascicle_path = os.path.join(book_path, image["fascicleName"])
            page_path = os.path.join(fascicle_path, image["directoryName"], filled_page_num)

            # 已发生书籍分卷切换
            if self._last_fascicle_path != "" and fascicle_path != self._last_fascicle_path:
                # 创建书籍分卷 PDF 文件
                last_fascicle_info = [f for f in book_fascicles if f["fascicleId"] == self._last_fascicle_id][0]
                pdf_page_count = last_fascicle_info["pageCount"]
                min_pdf_size = self._split_image_min_size * self._split_image_count * pdf_page_count
                if utils.is_valid_file(self._last_fascicle_path + ".pdf", min_pdf_size):
                    self._logger.info(f"跳过已生成 PDF 文件的分卷“{self._last_fascicle_name}”")
                else:
                    self._logger.info(f"正在生成分卷“{self._last_fascicle_name}” PDF 文件...")
                    dir_list = [d for d in book_directories if d["fascicleId"] == self._last_fascicle_id]
                    if not self._create_fascicle_pdf(self._last_fascicle_path, dir_list):
                        self._logger.error(f"生成分卷“{self._last_fascicle_name}” PDF 文件失败")

            self._last_fascicle_id = image["fascicleId"]
            self._last_fascicle_name = image["fascicleName"]
            self._last_fascicle_path = fascicle_path

            return True
        except Exception:
            self._logger.exception(f"打开第 {page} 页预处理异常")
            return False
    
    def _open_book_page(self, book_info, page : int, book_path : str) -> bool:
        """
        打开书籍页

        :param book_info: 书籍信息
        :param page: 页码（从 1 开始）
        :param book_path: 书籍下载路径
        """
        try:
            book_directories = book_info["directory"]
            book_images = book_info["image"]
            image = book_images[page - 1]

            # 根据页码，打开书籍章节页
            new_url = book_info["url"].format(image["catalogId"], image["fascicleId"], image["directoryId"])
            if new_url != self._last_opened_page_url:
                """
                如果此章节页已打开失败过，则直接返回失败。
                当打开某章节的第一页失败时，此章节的所有页都不用再尝试，可节省时间。
                以上错误会在某章节的第一页和上一章节的最后一页内容相同时发生。
                """
                if new_url == self._last_failed_page_url or not self._open_book_directory(new_url, (self._last_opened_page_url == "")):
                    self._last_failed_page_url = new_url
                    return False

                self._last_opened_page_url = new_url

            # 切换到指定书籍页
            directory = [d for d in book_directories if d["directoryId"] == image["directoryId"]][0]
            if directory["pageNum"] != image["pageNum"]:
                if not self._switch_book_page(image["pageNum"]):
                    return False

            # 检查页面显示的总页数
            page_count = self._get_displayed_book_page_count()
            if page_count != len(book_images):
                self._logger.error(f'书籍《{image["catalogName"]}》总页数不一致')
                return False

            # 检查页面显示的当前页码
            page_num = self._get_displayed_book_page_num()
            if page_num != image["pageNum"]:
                self._logger.error(f'书籍页“{image["fascicleName"]}/{image["directoryName"]}/{image["imageName"]}”页码不一致')
                return False
        
            # 输出已打开页面信息
            self._logger.info(f"已打开 {page_num}/{page_count} 页")
            return True
        except Exception:
            self._logger.exception(f"打开第 {page} 页异常")
            return False
    
    def _get_book_page(self, book_info, page : int, book_path : str) -> bool:
        """
        下载书籍页

        :param book_info: 书籍信息
        :param page: 页码（从 1 开始）
        :param book_path: 书籍下载路径
        """
        try:
            max_page_num_len = book_info["maxPageNumLen"]
            book_images = book_info["image"]
            image = book_images[page - 1]
            page_count = len(book_images)

            # 获取下载路径
            filled_page_num = str(image["pageNum"]).zfill(max_page_num_len)
            fascicle_path = os.path.join(book_path, image["fascicleName"])
            page_path = os.path.join(fascicle_path, image["directoryName"], filled_page_num)

            # 创建书籍页存放目录
            if not os.path.isdir(page_path):
                os.makedirs(page_path, exist_ok=True)

            # 记录当前页图片 URL（因为每张小图的 URL 仅后缀不同，所以记录第一张图即可）
            url_list = self._get_book_page_image_url_list()
            self._image_url_cache[image["catalogId"]][filled_page_num] = url_list[0]

            # 下载所有分割小图
            index = 1
            for url in url_list:
                file_path = os.path.join(page_path, "{}.jpg".format(index))

                if utils.is_valid_file(file_path, self._split_image_min_size):
                    self._logger.info(f"跳过已下载的图片（{url}）")
                else:
                    info = {}
                    info["url"] = url
                    info["index"] = index
                    info["pageNum"] = page
                    if not drv_utils.download_image(url, file_path):
                        self._logger.error(f"下载图片失败（{url}）")
                        self._failed_download_list.append(info)
                    else:
                        if not utils.is_valid_file(file_path, self._split_image_min_size):
                            self._logger.warning(f"图片大小过小（{file_path}）")
                            self._warned_download_list.append(info)

                index += 1

            # 合并分割小图
            merged_file_path = page_path + ".jpg"
            if utils.is_valid_file(merged_file_path, self._split_image_min_size * self._split_image_count):
                self._logger.info(f'跳过合并第 {image["pageNum"]}/{page_count} 页图片')
            else:
                tile_paths = [os.path.join(page_path, f) for f in os.listdir(page_path) if f.endswith(".jpg")]
                if len(tile_paths) != self._split_image_count:
                    self._logger.error(f'下载第 {image["pageNum"]}/{page_count} 页图片失败')
                    self._failed_page_list.append(image["pageNum"])
                    return False
                else:
                    if not img_utils.merge_images(tile_paths, 
                                                  self._split_image_rows, 
                                                  self._split_image_cols, 
                                                  merged_file_path):
                        self._logger.error(f'合并第 {image["pageNum"]}/{page_count} 页图片失败')
                        self._failed_page_list.append(image["pageNum"])
                        return False

            self._logger.info(f"下载第 {page} 页成功")
            return True
        except Exception:
            self._logger.exception(f"下载第 {page} 页异常")
            return False
    
    def _check_duplicate_data(self, fascicles : list, directories : list, images : list) -> bool:
        """
        检查书籍内容是否存在重复

        对于所有分卷、章节和页，ID 必须唯一。
        """
        # Check duplicated contents
        # The ID of each fascicle, directory and image must be unique.
        # If the name of some fascicle, directory and image is not unique, it will be renamed with suffix like "xxx_1"
        duplicate_exist = False
        duplicate_list = []

        # 检查重复分卷
        duplicate_list.clear()
        for fascicle in fascicles:
            id_list = [f["fascicleId"] 
                        for f in fascicles 
                        if f["catalogId"] == fascicle["catalogId"]]
            if id_list.count(fascicle["fascicleId"]) > 1:
                duplicate_list.append(fascicle)

        if (len(duplicate_list) > 0):
            duplicate_exist = True
            log_utils.logger_pprint(duplicate_list,
                                    level=logging.ERROR,
                                    msg_prefix="以下分卷存在重复：")
        
        # 检查重复章节
        duplicate_list.clear()
        for dir in directories:
            id_list = [d["directoryId"] 
                        for d in directories 
                        if d["catalogId"] == dir["catalogId"]
                        and d["fascicleId"] == dir["fascicleId"]]
            if id_list.count(dir["directoryId"]) > 1:
                duplicate_list.append(dir)
        
        if (len(duplicate_list) > 0):
            duplicate_exist = True
            log_utils.logger_pprint(duplicate_list,
                                    level=logging.ERROR,
                                    msg_prefix="以下章节存在重复：")

        # 检查重复页
        duplicate_list.clear()
        for image in images:
            id_list = [i["imageId"] 
                        for i in images 
                        if i["catalogId"] == image["catalogId"]
                        and i["fascicleId"] == image["fascicleId"]
                        and i["directoryId"] == image["directoryId"]]
            if id_list.count(image["imageId"]) > 1:
                duplicate_list.append(image)
        
        if (len(duplicate_list) > 0):
            duplicate_exist = True
            log_utils.logger_pprint(duplicate_list,
                                    level=logging.ERROR,
                                    msg_prefix="以下页存在重复：")

        return not duplicate_exist
    
    def _generate_book_contents(self, book_info) -> dict:
        """
        生成书籍目录信息

        :param book_info: 书籍信息
        """
        book_name = book_info["name"]
        book_id = book_info["catalogId"]
        book_fascicles = book_info["fascicle"]
        book_directories = book_info["directory"]
        book_images = book_info["image"]

        # 创建目录根节点
        book_contents = {
        "name": "{} (1 - {})".format(book_name, len(book_images)),
        "children": []}
    
        # 解析目录（书籍 -> 分卷 -> 章节 -> 页）
        page_num = 1
        fascicle_list = [f for f in book_fascicles if f["catalogId"] == book_id]
        for fascicle in fascicle_list:
            page_count = 0
            # 创建分卷节点
            node_fascicle = {
                "name": "",
                "children": []}

            # 获取章节列表
            dir_list = [d for d in book_directories 
                        if d["catalogId"] == book_id 
                        and d["fascicleId"] == fascicle["fascicleId"]]
            
            for dir in dir_list:
                # 添加章节节点
                if dir["pageCount"] > 1:
                    node_dir = { "name": "{} ({} - {})".format(dir["name"], dir["pageNum"], dir["pageNum"] + dir["pageCount"] - 1) }
                else:
                    node_dir = { "name": "{} ({})".format(dir["name"], dir["pageNum"]) }
                node_fascicle["children"].append(node_dir)

            # 添加分卷节点
            if fascicle["pageCount"] > 1:
                node_fascicle["name"] = "{} ({} - {})".format(fascicle["name"], fascicle["pageNum"], fascicle["pageNum"] + fascicle["pageCount"] - 1)
            else:
                node_fascicle["name"] = "{} ({})".format(fascicle["name"], fascicle["pageNum"])
            book_contents["children"].append(node_fascicle)

        return book_contents
    
    def _is_book_page_downloaded(self, book_info, page : int, book_path : str) -> bool:
        """
        检查书籍页是否已下载

        :param book_info: 书籍信息
        :param page: 页码（从 1 开始）
        :param book_path: 书籍下载路径
        """
        need_download = False
        book_images = book_info["image"]
        image = book_images[page - 1]
        max_page_num_len = book_info["maxPageNumLen"]
        filled_page_num = str(image["pageNum"]).zfill(max_page_num_len)
        fascicle_path = os.path.join(book_path, image["fascicleName"])
        page_path = os.path.join(fascicle_path, image["directoryName"], filled_page_num)

        for i in range(1, self._split_image_count + 1):
            file_path = os.path.join(page_path, "{}.jpg".format(i))
            if not utils.is_valid_file(file_path, self._split_image_min_size):
                need_download = True
                break

        if not filled_page_num in self._image_url_cache[image["catalogId"]].keys():
            need_download = True
        
        return not need_download

    def _wait_book_page_image_loaded(self):
        """
        等待书籍页图片加载完成
        """
        # 等待所有分割小图加载完成
        split_images = self._get_book_page_image_list()
        for image in split_images:
            drv_utils.wait_image_loaded(self._driver, image, self._driver_timeout)

    def _wait_book_page_loaded(self, old_image_url : str):
        """
        等待书籍页加载完成
        """
        # 等待页面加载中提示消失
        wait = WebDriverWait(self._driver, timeout=self._driver_timeout)
        wait.until(EC.visibility_of_element_located((By.ID, "bigimgsplit")))
        wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "ant-spin-text")))

        # 等待图片加载完成
        self._wait_book_page_image_loaded()

        if old_image_url != "":
            # 当切换页时，等待原图片消失，确保已开始加载新页面
            xpath = "//div[@id='bigimgsplit']/img[@authsrc='{}']".format(old_image_url)
            wait.until(EC.invisibility_of_element_located((By.XPATH, xpath)))

            # 等待新页面的图片加载完成
            self._wait_book_page_image_loaded()

    def _get_displayed_book_page_num(self) -> int:
        """
        获取显示的当前页码
        """
        page_choose = self._driver.find_element(By.CLASS_NAME, "choose-box")
        page_num = page_choose.find_element(By.CLASS_NAME, "page-num")
        return (int)(page_num.get_attribute("value"))

    def _get_displayed_book_page_count(self) -> int:
        """
        获取显示的总页数
        """
        page_choose = self._driver.find_element(By.CLASS_NAME, "choose-box")
        page_total = page_choose.find_element(By.CLASS_NAME, "page-total")
        return (int)(page_total.text)

    def _get_book_page_image_list(self) -> list:
        """
        获取分割小图元素列表
        """
        image_root = self._driver.find_element(By.ID, "bigimgsplit")
        split_images = image_root.find_elements(By.XPATH, "./img")
        return split_images

    def _get_book_page_image_url_list(self) -> list:
        """
        获取分割小图源地址列表
        """
        split_images = self._get_book_page_image_list()
        return [image.get_attribute("authsrc") for image in split_images]

    def _get_book_page_image_url_first(self) -> str:
        """
        获取第一张分割小图源地址
        """
        url = ""
        url_list = self._get_book_page_image_url_list()
        if len(url_list) > 0:
            url = url_list[0]
        return url

    def _open_book_directory(self, url : str, is_first : bool) -> bool:
        """
        打开书籍指定章节的首页
        """
        try:
            if is_first:
                old_image_url = ""
            else:
                old_image_url = self._get_book_page_image_url_first()
            self._driver.get(url)
            self._wait_book_page_loaded(old_image_url)
            return True
        except Exception:
            self._logger.exception(f"打开章节异常（{url}）")
            return False

    def _switch_book_page(self, page: int) -> bool:
        """
        切换到书籍当前章节的某一页
        
        注意：如果指定其它章节的页，会自动跳转到目标章节的第一页，从而导致错误
        """
        try:
            page_choose = self._driver.find_element(By.CLASS_NAME, "choose-box")
            page_num = page_choose.find_element(By.CLASS_NAME, "page-num")
            old_image_url = self._get_book_page_image_url_first()
            page_num.send_keys(Keys.BACKSPACE + Keys.BACKSPACE + Keys.BACKSPACE + Keys.BACKSPACE + str(page) + Keys.TAB)
            self._wait_book_page_loaded(old_image_url)
            return True
        except Exception:
            self._logger.exception(f"切换到第 {page} 页异常")
            return False

    def _create_fascicle_pdf(self, fascicle_path : str, dir_info_list : list) -> bool:
        """
        生成分卷 PDF 文件
        """
        outline = []
        image_paths = []

        is_error = False
        first_page = dir_info_list[0]["pageNum"]
        for dir_info in dir_info_list:
            dir_name = dir_info["name"]
            dir_path = os.path.join(fascicle_path, dir_name)
            if os.path.exists(dir_path):
                dir_pages = [f for f in os.listdir(dir_path) if f.endswith(".jpg")]
            else:
                dir_pages = []
            if len(dir_pages) != dir_info["pageCount"]:
                self._logger.error(f"章节“{dir_name}”下载未完成")
                is_error = True
                break

            page_files = [os.path.join(dir_path, f) for f in dir_pages]
            for f in page_files:
                image_paths.append(f)

            page = dir_info["pageNum"] - first_page + 1
            bookmark = {"title": dir_name, "page": page, "level": 0}
            outline.append(bookmark)

        if is_error:
            self._logger.error("因缺页取消生成分卷 PDF 文件")
            return False

        # 生成无目录的分卷 PDF 临时文件
        tmp_file_path = fascicle_path + "_tmp.pdf"
        if not pdf_utils.images_to_pdf(image_paths, tmp_file_path):
            return False
        
        # 生成分卷 PDF 文件
        pdf_file_path = fascicle_path + ".pdf"
        if not pdf_utils.add_pdf_outline(tmp_file_path, pdf_file_path, outline):
            return False
        
        # 删除分卷 PDF 临时文件
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)

        return True
    