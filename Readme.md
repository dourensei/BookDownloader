# BookDownloader

## 简介
- 本脚本通过 selenium 操作浏览器实现自动下载书籍
- 仅为自己资料备份使用，请勿用于任何违法违规用途
- 代码写得较随意，纯属自娱自乐，随缘更新

## 主要功能

- 从以下特定网站下载书籍：
    - 天一阁 （gj.tianyige.com.cn）
- 自动按书籍->分卷->章节下载所有原始图片
- 自动按分卷生成 PDF 文件（默认）
- 自动生成全书 PDF 文件（可选）
- 自动剔除连续重复页（默认）

## 使用方法

- 通过 `python main.py` 运行
- 通过 build.bat 打包成 EXE，然后使用命令行调用运行 BookDownloader.exe
- 两种方式都可带参数，具体如下：
```
usage: BookDownloader.exe [-h] [-w BROWSER] [-d DRIVER] [-b BOOK] [-s SAVE] [-c CACHE] [-p PATCH] [-n] [-k] [-f]

BookDownloader

options:
  -h, --help            show this help message and exit
  -w BROWSER, --browser BROWSER
                        浏览器 EXE 文件路径（默认：%ProgramFiles%\Chrome\Application\chrome.exe）
  -d DRIVER, --driver DRIVER
                        浏览器适配 WebDriver EXE 文件路径（默认：.\chromedriver.exe）
  -b BOOK, --book BOOK  下载书籍信息文件路径（默认：.\book.json）
  -s SAVE, --save SAVE  书籍下载文件夹路径（默认：.\download）
  -c CACHE, --cache CACHE
                        书籍下载缓存文件夹路径（默认：.\cache）
  -p PATCH, --patch PATCH
                        补丁文件夹路径（默认：.\patch）
  -n, --no-retry        下载失败时不自动重试（默认会自动重试直至书籍全部下载成功）
  -k, --keep-duplicate  生成 PDF 文件时保留重复页（默认会自动删除重复页）
  -f, --book-pdf        创建全书 PDF 文件（默认只生成拆分的 PDF 文件）

示例用法：
  BookDownloader.exe -w "C:\Program Files\Google\Chrome\Application\chrome.exe" -d "D:\chromedriver.exe" -b "D:\book.json"
```

## 运行环境

### Python 依赖包

记不清了，根据运行错误提示一个个安装吧 -_-b

### Web 浏览器

目前仅支持 Chrome，自行下载安装

### WebDriver

和 Web 浏览器强相关，具体参考官方说明：
[ChromeDriver 版本选择](https://developer.chrome.google.cn/docs/chromedriver/downloads/version-selection?hl=zh-cn&authuser=8)

## 必要的输入

- Web 浏览器 EXE 路径
    - 需自行安装，目前仅支持 Chrome
- Web 浏览器对应 WebDriver EXE 路径
    - 需自行下载，**必须与浏览器版本对应**，具体参考浏览器的官方说明
- 下载书籍信息 JSON 文件
    - 需自行制作，具体参考下文

## 主要的输出

- 下载的原始图片和生成的 PDF 文件（默认在 download 文件夹下）

## 下载书籍信息 JSON 文件制作

这个稍微有点繁琐，需要会调试，懂 JSON 文件格式。

但因为是自己用的，懒得再研究怎么自动抓取了。

- 天一阁
    - 复制模板 `library/book_tianyige.json`，推荐存为 `根目录/book.json`
    - 用文本编辑器打开进行修改：
        - 第3行的 `书名` 改成要下载的书名
        - 第4行的 `作者` 改成要下载的书作者
        - 第5行的 `catalogIdxxx` 改成要下载的书的 ID：
            - 手动打开书的任意一页，网址 `...Book?catalogId=xxx&...` 中的 `xxx`
        - 第6行的 `fasicle` 和第54行的 `image`：
            - 按 F12，切换到源代码，打开 `index.xxx.chunk.js`
            - 找到 `Xe = ["10", "20", "30", "40", "50", "60", "70", "80", "90", "100", "120", "130", "140", "150", "160", "170", "180", "190", "200"], Ue = function(e) {`
            - 在此函数内部任意位置设置断点
            - 手动切换到书的任意一页，会在断点处停止
            - 添加变量 `e` 到 Watch，点开查看
            - 右击 `fascicle` 选择 `Copy object`，再粘贴替换 `fasicle` 后面的列表
            - 右击 `imgList` 选择 `Copy object`，再粘贴替换 `image` 后面的列表
            - 点击上方按钮继续运行
        - 第24行的 `directory`：
            - 依次打开书的每个分卷
            - 重复以上相同操作，在断点处停止
            - 右击 `Muludata` 选择 `Copy object`，再粘贴追加到 `directory` 后面的列表中
            - 点击上方按钮继续运行

## 问题记录

- Q：为啥用 Selenium 操作网页的方式下载？
  A：刚开始想直接通过 `https://gj.tianyige.com.cn/g/sw-anb/api/queryXXX` 直接获取相关信息，但是会返回提示要用户登录。由于本人网络知识匮乏，遂放弃 T-T 

     改用 Selenium 主要是很多年前用过比较熟悉。而且虽然这种方式比较费时，但是属于模拟手动操作，应该不容易被服务器反爬毙掉。

- Q：天一阁的坑有哪些？
  A：
  1. 网址仅包含书ID、分卷ID和章节ID，不包含页数。所以在一个章节内的翻页，只能通过输入页码来实现。而且要注意给的页码不能超出当前章节范围，不然会导致自动跳转到另一个章节的第一页。
  2. 每一页的图片，被分割成了4x2共8张小图，必须依次下载下来在进行拼接。
  3. 每张小图的源地址是js代码用每一页对应的imageID通过api向服务器获取到的，返回的实际是存放在服务器上的jpg文件ID。这玩意儿只能一页一页地获取，很花时间。
  4. 图片加载时快时慢，有时甚至会失败，代码必须作精确等待和出错重试处理。
  5. 最大的坑是，会出现连续几页显示内容相同的情况。我判断翻页完成的逻辑是，页面图片加载完成且源地址和上一页的不一样。遇到这种情况就会导致脚本认为翻页超时报错。
  暂时没想到更好的方法，只能通过多次重试来解决。
  6. 正因为上面的坑，在生成 PDF 时需要额外过滤连续重复页，在处理书签对应的页码时要特别小心防止错位。

## TODO

- 增加 patch 功能，在生成 PDF 时用指定内容替换原图片
- 增加压缩功能
- 增加浏览器支持
- 增加网站支持
