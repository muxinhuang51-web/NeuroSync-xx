import pprint

intent_tree = {
    "写一个爬虫程序，爬取指定URL的内容并保存到本地": {
        "爬取文本内容并保存": {
            "提取微信公众号文章的文本内容": {
                "区分并提取标题": {},
                "区分并提取正文内容": {
                    "调整正文内容的格式以避免过多换行": {}
                },
                "提取并区分不同级别的标题": {
                    "确保所有级别的标题都被正确提取和保存": {}
                }
            },
            "将文本保存到本地文件": {
                "保存纯文本内容": {},
                "保存完整内容中的文本部分": {
                    "将内容保存为文本文件（.txt）": {
                        "替换文本中的图像位置": {
                            "确保图片标题正确插入文本": {},
                            "确保图片被正确插入到文本文件中": {},
                            "确保图片名称写在原始URL对应的位置上": {}
                        }
                    }
                }
            }
        },
        "爬取图像内容并保存": {
            "查找微信公众号文章中的所有图像URL": {},
            "下载图像并保存到本地文件夹": {
                "下载并命名图像": {},
                "保存完整内容中的图像部分": {}
            }
        }
    }
}


task_graph = {
    "nodes": [
        {"id": "Node1", "description": "发起HTTP请求以获取目标网页的内容"},
        {"id": "Node2", "description": "使用BeautifulSoup解析HTML文档"},
        {"id": "Node3", "description": "提取微信公众号文章的标题"},
        {"id": "Node4", "description": "提取微信公众号文章的不同级别标题"},
        {"id": "Node5", "description": "提取微信公众号文章的正文内容"},
        {"id": "Node6", "description": "查找微信公众号文章中的所有图像URL"},
        {"id": "Node7", "description": "下载图像并保存到本地文件夹"},
        {"id": "Node8", "description": "替换文本中的图像位置"},
        {"id": "Node9", "description": "调整正文内容的格式以避免过多换行"},
        {"id": "Node10", "description": "保存文本内容到本地文件"},
        {"id": "Node11", "description": "创建保存内容的本地文件夹（如果不存在）"},
        {"id": "Node12", "description": "确保图片名称写在原始URL对应的位置上"}
    ],
    "links": [
        {"source": "Node1", "target": "Node2", "type": "parse"},
        {"source": "Node2", "target": "Node3", "type": "extractTitle"},
        {"source": "Node2", "target": "Node4", "type": "extractHeadings"},
        {"source": "Node2", "target": "Node5", "type": "extractBodyText"},
        {"source": "Node2", "target": "Node6", "type": "findImages"},
        {"source": "Node6", "target": "Node7", "type": "downloadImages"},
        {"source": "Node5", "target": "Node8", "type": "replaceImageTags"},
        {"source": "Node8", "target": "Node9", "type": "adjustFormatting"},
        {"source": "Node9", "target": "Node10", "type": "saveText"},
        {"source": "Node11", "target": "Node7", "type": "saveToFolder"},
        {"source": "Node11", "target": "Node10", "type": "saveToFolder"},
        {"source": "Node8", "target": "Node12", "type": "ensureOrder"}
    ]
}

mapping = {
    "写一个爬虫程序，爬取指定URL的内容并保存到本地": {
        "nodes": ["Node1", "Node2", "Node3", "Node4", "Node5", "Node6", "Node7", "Node8", "Node9", "Node10", "Node11", "Node12"],
        "links": [
            {"source": "Node1", "target": "Node2", "type": "parse"},
            {"source": "Node2", "target": "Node3", "type": "extractTitle"},
            {"source": "Node2", "target": "Node4", "type": "extractHeadings"},
            {"source": "Node2", "target": "Node5", "type": "extractBodyText"},
            {"source": "Node2", "target": "Node6", "type": "findImages"},
            {"source": "Node6", "target": "Node7", "type": "downloadImages"},
            {"source": "Node5", "target": "Node8", "type": "replaceImageTags"},
            {"source": "Node8", "target": "Node9", "type": "adjustFormatting"},
            {"source": "Node9", "target": "Node10", "type": "saveText"},
            {"source": "Node11", "target": "Node7", "type": "saveToFolder"},
            {"source": "Node11", "target": "Node10", "type": "saveToFolder"},
            {"source": "Node8", "target": "Node12", "type": "ensureOrder"}
        ]
    },
    "爬取文本内容并保存": {
        "nodes": ["Node1", "Node2", "Node3", "Node4", "Node5", "Node8", "Node9", "Node10", "Node11", "Node12"],
        "links": [
            {"source": "Node1", "target": "Node2", "type": "parse"},
            {"source": "Node2", "target": "Node3", "type": "extractTitle"},
            {"source": "Node2", "target": "Node4", "type": "extractHeadings"},
            {"source": "Node2", "target": "Node5", "type": "extractBodyText"},
            {"source": "Node5", "target": "Node8", "type": "replaceImageTags"},
            {"source": "Node8", "target": "Node9", "type": "adjustFormatting"},
            {"source": "Node9", "target": "Node10", "type": "saveText"},
            {"source": "Node11", "target": "Node10", "type": "saveToFolder"},
            {"source": "Node8", "target": "Node12", "type": "ensureOrder"}
        ]
    },
    "爬取图像内容并保存": {
        "nodes": ["Node1", "Node2", "Node6", "Node7", "Node11"],
        "links": [
            {"source": "Node1", "target": "Node2", "type": "parse"},
            {"source": "Node2", "target": "Node6", "type": "findImages"},
            {"source": "Node6", "target": "Node7", "type": "downloadImages"},
            {"source": "Node11", "target": "Node7", "type": "saveToFolder"}
        ]
    },
    "将内容保存为文本文件（.txt）": {
        "nodes": ["Node5", "Node8", "Node9", "Node10", "Node11", "Node12"],
        "links": [
            {"source": "Node5", "target": "Node8", "type": "replaceImageTags"},
            {"source": "Node8", "target": "Node9", "type": "adjustFormatting"},
            {"source": "Node9", "target": "Node10", "type": "saveText"},
            {"source": "Node11", "target": "Node10", "type": "saveToFolder"},
            {"source": "Node8", "target": "Node12", "type": "ensureOrder"}
        ]
    },
    "保存文本内容到本地文件": {
        "nodes": ["Node9", "Node10", "Node11", "Node12"],
        "links": [
            {"source": "Node9", "target": "Node10", "type": "saveText"},
            {"source": "Node11", "target": "Node10", "type": "saveToFolder"},
            {"source": "Node8", "target": "Node12", "type": "ensureOrder"}
        ]
    },
    "确保图片被正确插入到文本文件中": {
        "nodes": ["Node5", "Node8", "Node9", "Node10", "Node11", "Node12"],
        "links": [
            {"source": "Node5", "target": "Node8", "type": "replaceImageTags"},
            {"source": "Node8", "target": "Node9", "type": "adjustFormatting"},
            {"source": "Node9", "target": "Node10", "type": "saveText"},
            {"source": "Node11", "target": "Node10", "type": "saveToFolder"},
            {"source": "Node8", "target": "Node12", "type": "ensureOrder"}
        ]
    },
    "确保图片名称写在原始URL对应的位置上": {
        "nodes": ["Node8", "Node12"],
        "links": [
            {"source": "Node8", "target": "Node12", "type": "ensureOrder"}
        ]
    }
}

def print_demo_data():
    print("Intent Tree:")
    pprint.pprint(intent_tree)
    print("\nTask Graph:")
    pprint.pprint(task_graph)
    print("\nMapping:")
    pprint.pprint(mapping)


if __name__ == "__main__":
    print_demo_data()