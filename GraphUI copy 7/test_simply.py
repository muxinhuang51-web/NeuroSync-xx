import re, json, pprint
llm_response=""" 
 <｜begin▁of▁sentence｜>


        ### Intent Tree:
        ```json
        {
            "写一个微信爬虫程序爬取微信公众号内容": {
            "爬取文章内容并保存到本地": {},
            "爬取图像内容并保存到本地": {},
            "爬取视频内容并保存到本地": {},
            "爬取音频内容并保存到本地": {}
            }
        }
        ```
        ### Task Graph:
        ```json
        {
            "nodes": [
            {"id": "Node1", "description": "初始化并配置爬虫环境，包括处理Cookie和User-Agent"},
            {"id": "Node2", "description": "导入必要的库，包括BeautifulSoup、urllib、requests、multi_threading","},
            {"id": "Node3", "description": "创建一个会话对象以处理微信API和Cookies"},
            {"id": "Node4", "description": "发送HTTP请求以获取目标网页的内容"},
            {"id": "Node5", "description": "使用BeautifulSoup解析HTML文档，提取标题、内容和发布时间"},
            {"id": "Node6", "description": "提取文本内容并保存到本地文件中"},
            {"id": "Node7", "description": "检查图片URL并下载图片到本地文件夹中"},
            {"id": "Node8", "description": "检查视频URL并下载视频到本地文件夹中"},
            {"id": "Node9", "description": "检查音频URL并下载音频到本地文件夹中"},
            {"id": "Node10", "description": "创建保存内容的本地文件夹（如果不存在）"},
            {"id": "Node11", "description": "处理异常情况，包括网络错误和错误提醒"}
            ],
            "links": [
            {"source": "Node1", "target": "Node2", "type": "setup"},
            {"source": "Node2", "target": "Node3", "type": "configureSession"},
            {"source": "Node3", "target": "Node4", "type": "sessionRequest"},
            {"source": "Node4", "target": "Node5", "type": "parseContent"},
            {"source": "Node5", "target": "Node6", "type": "saveText"},
            {"source": "Node5", "target": "Node7", "type": "findImages"},
            {"source": "Node7", "target": "Node8", "type": "downloadImages"},
            {"source": "Node7", "target": "Node9", "type": "downloadImages"},
            {"source": "Node5", "target": "Node10", "type": "saveToFolder"},
            {"source": "Node7", "target": "Node10", "type": "saveToFolder"},
            {"source": "Node8", "target": "Node10", "type": "saveToFolder"},
            {"source": "Node9", "target": "Node10", "type": "saveToFolder"},
            {"source": "Node11", "target": "Node2", "type": "exceptionHandling"},
            {"source": "Node11", "target": "Node3", "type": "exceptionHandling"},
            {"source": "Node11", "target": "Node4", "type": "exceptionHandling"},
            {"source": "Node11", "target": "Node5", "type": "exceptionHandling"},
            {"source": "Node11", "target": "Node6", "type": "exceptionHandling"},
            {"source": "Node11", "target": "Node7", "type": "exceptionHandling"},
            {"source": "Node11", "target": "Node8", "type": "exceptionHandling"},
            {"source": "Node11", "target": "Node9", "type": "exceptionHandling"},
            {"source": "Node10", "target": "Node11", "type": "folderCheck"}
            ]
        }
        ### Mapping:
        ```json
        {
            "写一个微信爬虫程序爬取微信公众号内容": {
            "nodes": ["Node1", "Node2", "Node3", "Node4", "Node5", "Node6", "Node7", "Node8", "Node9", "Node10", "Node11"]
            },
            "爬取文章内容并保存到本地": {
            "nodes": ["Node1", "Node2", "Node3", "Node4", "Node5", "Node6", "Node10", "Node11"]
            },
            "爬取图像内容并保存到本地": {
            "nodes": ["Node1", "Node2", "Node3", "Node4", "Node7", "Node10", "Node11"]
            },
            "爬取视频内容并保存到本地": {
            "nodes": ["Node1", "Node2", "Node3", "Node4", "Node8", "Node10", "Node11"]
            },
            "爬取音频内容并保存到本地": {
            "nodes": ["Node1", "Node2", "Node3", "Node4", "Node9", "Node10", "Node11"]
            }
        }
 
        """

def extract_json_section(text, section_header):
    # Find all occurrences of the section header
    header_matches = list(re.finditer(f"{section_header}:\\s*```json\\s*", text, re.DOTALL))
    if not header_matches:
        return None
    
    # Use only the first occurrence
    start_match = header_matches[0]
    start_idx = start_match.end()
    json_text = text[start_idx:]
    
    # Count braces to find complete JSON object
    brace_count = 0
    end_idx = 0
    in_string = False
    escape_char = False
    
    for i, char in enumerate(json_text):
        if char == '"' and not escape_char:
            in_string = not in_string
        elif not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
        
        escape_char = (char == '\\' and not escape_char)
    
    return json_text[:end_idx] if end_idx > 0 else None

# Extract each section using the modified function
intent_tree_json = extract_json_section(llm_response, "### Intent Tree")
task_graph_json = extract_json_section(llm_response, "### Task Graph")
mapping_json = extract_json_section(llm_response, "### Mapping")

# Add error handling for JSON parsing
try:
    intent_tree = json.loads(intent_tree_json) if intent_tree_json else {}
    graph = json.loads(task_graph_json) if task_graph_json else {"nodes": [], "links": []}
    mapping = json.loads(mapping_json) if mapping_json else {}

    print("intent_tree_json is: ")
    print(intent_tree_json)
    print("\ntask_graph_json is: ")
    print(task_graph_json)
    print("\nmapping_json is: ")
    print(mapping_json)

    print("==========================================Data==========================================")
    print("\nnew intent_tree is: ")
    pprint.pprint(intent_tree)
    print("\nnew graph is: ")
    pprint.pprint(graph)
    print("\nnew mapping is: ")
    pprint.pprint(mapping)
except json.JSONDecodeError as e:
    print(f"Error parsing JSON: {e}")
    print("Check the extracted JSON sections:")
    print(f"Intent Tree JSON valid: {intent_tree_json is not None}")
    print(f"Task Graph JSON valid: {task_graph_json is not None}")
    print(f"Mapping JSON valid: {mapping_json is not None}")
