import pprint

intent_tree = {
    "写一个爬虫程序，爬取指定URL的内容并保存到本地": {
        "创建文件夹以保存内容": {},
        "爬取文本内容并保存": {
            "提取微信公众号特定标签的文本内容": {
                "提取不同级别的标题并标注": {
                    "提取小标题": {}
                },
                "调整正文格式以确保段落一致性": {}
            },
            "仅保存文本内容": {
                "仅保存纯文本内容": {}
            }
        },
        "爬取图像内容并保存": {
            "提取微信公众号特定标签的图像URL": {},
            "处理动态加载的图像URL": {},
            "保存文本与图片的完整内容": {}
        }
    }
}

task_graph = {
    "nodes": [
        {"id": "Node1", "description": "发起HTTP请求以获取目标网页的内容"},
        {"id": "Node2", "description": "使用BeautifulSoup解析HTML文档"},
        {"id": "Node3", "description": "提取微信公众号特定标签的文本内容"},
        {"id": "Node4", "description": "提取不同级别的标题并标注"},
        {"id": "Node5", "description": "提取小标题"},
        {"id": "Node6", "description": "调整正文格式以确保段落一致性"},
        {"id": "Node7", "description": "保存仅文本内容到文件中"},
        {"id": "Node8", "description": "查找微信公众号特定标签的图像URL"},
        {"id": "Node9", "description": "处理动态加载的图像URL"},
        {"id": "Node10", "description": "下载图像并保存到本地文件夹中"},
        {"id": "Node11", "description": "保存文本与图片的完整内容到Markdown文件中"},
        {"id": "Node12", "description": "创建保存内容的本地文件夹（如果不存在）"},
        {"id": "Node13", "description": "保存纯文本内容到单独的TXT文件中"}
    ],
    "links": [
        {"source": "Node1", "target": "Node2", "type": "parse"},
        {"source": "Node2", "target": "Node3", "type": "extractText"},
        {"source": "Node3", "target": "Node4", "type": "annotateHeadings"},
        {"source": "Node4", "target": "Node5", "type": "extractSubHeadings"},
        {"source": "Node5", "target": "Node6", "type": "formatParagraphs"},
        {"source": "Node6", "target": "Node7", "type": "saveToFolder"},
        {"source": "Node2", "target": "Node8", "type": "findImages"},
        {"source": "Node8", "target": "Node9", "type": "processDynamicURLs"},
        {"source": "Node9", "target": "Node10", "type": "downloadImages"},
        {"source": "Node6", "target": "Node11", "type": "saveToFolder"},
        {"source": "Node10", "target": "Node11", "type": "saveToFolder"},
        {"source": "Node12", "target": "Node7", "type": "saveToFolder"},
        {"source": "Node12", "target": "Node11", "type": "saveToFolder"},
        {"source": "Node6", "target": "Node13", "type": "saveToFolder"}
    ]
}


mapping = {
    "写一个爬虫程序，爬取指定URL的内容并保存到本地": {
        "nodes": ["Node1", "Node2", "Node3", "Node4", "Node5", "Node6", "Node7", "Node8", "Node9", "Node10", "Node11", "Node12", "Node13"]
    },
    "创建文件夹以保存内容": {
        "nodes": ["Node12"]
    },
    "爬取文本内容并保存": {
        "nodes": ["Node1", "Node2", "Node3", "Node4", "Node5", "Node6", "Node7", "Node12", "Node13"]
    },
    "提取微信公众号特定标签的文本内容": {
        "nodes": ["Node2", "Node3", "Node4", "Node5", "Node6"]
    },
    "提取不同级别的标题并标注": {
        "nodes": ["Node3", "Node4", "Node5"]
    },
    "提取小标题": {
        "nodes": ["Node4", "Node5"]
    },
    "调整正文格式以确保段落一致性": {
        "nodes": ["Node5", "Node6"]
    },
    "仅保存文本内容": {
        "nodes": ["Node6", "Node7", "Node12", "Node13"]
    },
    "仅保存纯文本内容": {
        "nodes": ["Node6", "Node13"]
    },
    "爬取图像内容并保存": {
        "nodes": ["Node1", "Node2", "Node8", "Node9", "Node10", "Node11", "Node12"]
    },
    "提取微信公众号特定标签的图像URL": {
        "nodes": ["Node2", "Node8"]
    },
    "处理动态加载的图像URL": {
        "nodes": ["Node8", "Node9"]
    },
    "保存文本与图片的完整内容": {
        "nodes": ["Node6", "Node10", "Node11", "Node12"]
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