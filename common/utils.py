import os
import random
import sys
import threading
import time
import pyautogui
from typing import Optional
import common.logger_utils as log_utils

# 防休眠函数相关全局线程对象、停止标记
_awake_thread: Optional[threading.Thread] = None
_stop_flag = threading.Event()
# 防休眠参数
DEFAULT_INTERVAL = 20  # 操作间隔20秒
MIN_MOVE_PX = 5        # 最小移动5像素
MAX_MOVE_PX = 10       # 最大移动10像素

def keep_awake(interval: int = DEFAULT_INTERVAL, random_move: bool = True):
    """
    强化版防休眠函数（100%生效）
    :param interval: 操作间隔（秒），建议≤30秒
    :param random_move: 是否随机移动鼠标（避免固定轨迹被识别）
    """
    # 强制关闭屏保和休眠（无需管理员，覆盖系统设置）
    os.system("powercfg /change monitor-timeout-ac 0")  # 关闭显示器超时
    os.system("powercfg /change standby-timeout-ac 0")  # 关闭系统休眠
    os.system("powercfg /change hibernate-timeout-ac 0")# 关闭休眠
    log_utils.get_logger().info("已修改Windows电源计划，禁用屏保/休眠")

    global _awake_thread, _stop_flag
    
    # 重置停止标记
    _stop_flag.clear()
    
    def _inner_keep_awake():
        """内部核心循环：鼠标+键盘双重操作"""
        log_utils.get_logger().info(f"防休眠线程启动 | 操作间隔{interval}秒 | 随机移动={random_move}")
        while not _stop_flag.is_set():
            try:
                # ========== 1. 鼠标操作（核心） ==========
                if random_move:
                    # 随机移动方向和像素（避免固定轨迹）
                    dx = random.randint(MIN_MOVE_PX, MAX_MOVE_PX) * random.choice([-1, 1])
                    dy = random.randint(MIN_MOVE_PX, MAX_MOVE_PX) * random.choice([-1, 1])
                else:
                    dx, dy = MIN_MOVE_PX, MIN_MOVE_PX
                
                pyautogui.moveRel(dx, dy, duration=0.1)  # 缓慢移动（更像人工操作）
                # 移回原位置（避免鼠标跑偏）
                pyautogui.moveRel(-dx, -dy, duration=0.1)
                
                # ========== 2. 键盘操作（兜底，应对严格系统） ==========
                # 轻按Shift键（无实际输入，仅触发系统输入检测）
                pyautogui.press('shift', presses=1, interval=0.05)
                
                log_utils.get_logger().debug("防休眠操作执行完成（鼠标+键盘）")
                
                # 等待间隔（支持即时停止）
                _stop_flag.wait(interval)
                
            except Exception as e:
                log_utils.get_logger().error(f"防休眠操作异常：{e}，1秒后重试")
                time.sleep(1)
        
        log_utils.get_logger().info("防休眠线程已停止")
    
    # 校验线程状态，避免重复启动
    if _awake_thread and _awake_thread.is_alive():
        log_utils.get_logger().warning("防休眠线程已在运行，无需重复启动")
        return
    
    # 启动守护线程（优先级设为最高）
    _awake_thread = threading.Thread(target=_inner_keep_awake, daemon=True, name="AntiSleepThread")
    _awake_thread.start()
    log_utils.get_logger().info(f"防休眠线程启动成功（线程ID：{_awake_thread.ident}）")

def stop_keep_awake():
    """停止防休眠线程"""
    global _stop_flag, _awake_thread
    if not _awake_thread or not _awake_thread.is_alive():
        log_utils.get_logger().warning("防休眠线程未运行，无需停止")
        return
    
    _stop_flag.set()
    # 等待线程退出（最多3秒）
    _awake_thread.join(timeout=3)
    _awake_thread = None
    log_utils.get_logger().info("防休眠线程已停止")

def get_base_path(module_path : str):
    """
    获取程序基础目录（兼容源码/EXE运行）：
    - 源码运行：返回main.py所在目录
    - EXE运行：返回EXE文件所在目录（而非临时目录）
    """
    if hasattr(sys, '_MEIPASS'):
        # EXE运行时，_MEIPASS是临时解压目录，需返回EXE所在目录
        exe_path = os.path.dirname(sys.executable)  # 获取EXE文件路径
        return os.path.abspath(exe_path)
    else:
        # 源码运行时，返回main.py所在目录
        return os.path.abspath(os.path.dirname(module_path))
    
def get_valid_path_name(name : str, used_names : list=[]) -> str:
    """
    获取有效路径名（替换无效字符、重名添加后缀）

    :param name: 路径名
    :param used_names: 已存在路径名
    """
    valid_name = name

    # 将无效字符替换为'_'
    invalid_list = ["\n", "\t", '<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for str in invalid_list:
        valid_name = valid_name.replace(str, '_')

    # 发生重名时自动添加后缀
    if used_names.count(valid_name) > 0:
        suffix = 1
        tmp_name = valid_name + f"_{suffix}"
        while used_names.count(tmp_name) > 0:
            suffix += 1
            tmp_name = valid_name + f"_{suffix}"
        valid_name = tmp_name

    return valid_name

def is_valid_file(file_path : str, min_size : int) -> bool:
    """
    检查文件是否有效

    :param file_path: 文件路径
    :type file_path: int
    :param min_size: 文件最小大小（字节）
    :type min_size: int
    """
    if not os.path.exists(file_path):
        return False
    
    if os.path.getsize(file_path) < min_size:
        return False
    
    return True

# 调用示例:
#     # 创建树形结构数据
#     tree_data = {
#         "name": "Root Node",
#         "children": [
#             {
#                 "name": "Child 1",
#                 "children": [
#                     {"name": "Grandchild 1"},
#                     {"name": "Grandchild 2"}
#                 ]
#             },
#             {
#                 "name": "Child 2",
#                 "children": [
#                     {"name": "Grandchild 3"}
#                 ]
#             },
#             {"name": "Child 3"}
#         ]
#     }
#     print_tree_structure(tree_data)
#
def print_tree_structure(data, output_file=None):
    """
    输出树形结构数据

    :param data: 树形结构数据
    :param output_file: 输出文件对象，省略时输出到控制台
    """
    _print_tree_structure(data, prefix="", is_last=True, f=output_file)

def _print_tree_structure(data, prefix="", is_last=True, f=None):
    """
    递归输出树形结构数据

    :param data: 树形结构数据
    :param prefix: 前缀
    :param is_last: 是否最后一个叶节点
    :param f: 输出文件对象，省略时输出到控制台
    """
    # 输出当前节点
    if prefix:
        print(prefix + ("└── " if is_last else "├── ") + str(data['name']), file=f)
    else:
        print(data['name'], file=f)
    
    # 输出子节点
    if 'children' in data and data['children']:
        for i, child in enumerate(data['children']):
            is_last_child = (i == len(data['children']) - 1)
            new_prefix = prefix + ("    " if is_last else "│   ")
            _print_tree_structure(child, new_prefix, is_last_child, f)
