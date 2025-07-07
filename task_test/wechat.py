import os
import json
import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin

def wechat_article_crawler(url, output_folder='wechat_articles'):
    # 创建保存文件夹
    os.makedirs(output_folder, exist_ok=True)
    img_folder = os.path.join(output_folder, 'images')
    os.makedirs(img_folder, exist_ok=True)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"请求失败，状态码：{response.status_code}")
            return
    except Exception as e:
        print(f"请求发生错误：{str(e)}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    article_content = soup.find('div', class_='rich_media_content')
    
    if not article_content:
        print("未找到文章内容")
        return

    # 图片位置记录列表
    image_positions = []
    # 带图片标记的文本内容
    marked_text = []
    # 图片序号
    img_counter = 1

    # 遍历所有子节点（Node6功能实现）
    for child in article_content.children:
        if isinstance(child, Tag) and child.name == 'img':
            # 处理图片节点
            img_url = child.get('data-src') or child.get('src')
            if img_url:
                img_url = urljoin(url, img_url)
                img_name = f"image_{img_counter}.jpg"
                img_path = os.path.join(img_folder, img_name)
                
                # 下载图片（Node5）
                try:
                    img_data = requests.get(img_url, headers=headers, stream=True).content
                    with open(img_path, 'wb') as img_file:
                        img_file.write(img_data)
                    print(f"图片已保存：{img_name}")
                except Exception as e:
                    print(f"下载图片失败：{img_url} - {str(e)}")
                    img_name = None

                # 记录位置信息
                position_info = {
                    "index": img_counter,
                    "marker": f"[Image_{img_counter}]",
                    "filename": img_name,
                    "original_url": img_url,
                    "status": "success" if img_name else "failed"
                }
                image_positions.append(position_info)
                
                # 在文本中插入标记
                marked_text.append(f"\n[Image_{img_counter}]\n")
                img_counter += 1
        else:
            # 处理文本节点
            text = child.get_text(separator='\n', strip=True)
            if text:
                marked_text.append(text)

    # 保存带标记的文本（Node3）
    text_filename = os.path.join(output_folder, 'article_with_markers.txt')
    with open(text_filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(marked_text))
    print(f"带图片标记的文本已保存到：{text_filename}")

    # 保存位置信息元数据（Node6）
    meta_filename = os.path.join(output_folder, 'image_positions.json')
    with open(meta_filename, 'w', encoding='utf-8') as f:
        json.dump(image_positions, f, ensure_ascii=False, indent=2)
    print(f"图片位置元数据已保存到：{meta_filename}")

if __name__ == "__main__":
    article_url = 'https://mp.weixin.qq.com/s/目标文章路径'
    wechat_article_crawler(article_url)