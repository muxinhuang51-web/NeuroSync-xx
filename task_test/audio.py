import os
import speech_recognition as sr
from pydub import AudioSegment
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize
import re

nltk.download('punkt_tab')

# Download required NLTK resources at the beginning
def download_nltk_resources():
    """Download required NLTK resources if they're not already available"""
    resources = ['punkt', 'vader_lexicon']
    for resource in resources:
        try:
            nltk.data.find(f'tokenizers/{resource}')
            print(f"Resource '{resource}' already downloaded.")
        except LookupError:
            print(f"Downloading '{resource}'...")
            nltk.download(resource)
            print(f"Resource '{resource}' successfully downloaded.")

# Call this function at the beginning
download_nltk_resources()

def prepare_audio(audio_path):
    """
    准备音频文件：获取需要处理的音频并确保音频清晰可听
    """
    print(f"处理音频文件: {audio_path}")
    
    # 检查文件是否存在
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件 {audio_path} 不存在")
    
    # 使用pydub加载音频文件
    audio = AudioSegment.from_mp3(audio_path)
    
    # 简单处理以提高可听度（例如：标准化音量）
    normalized_audio = audio.normalize()
    
    # 将处理后的音频保存为临时WAV文件（因为识别器通常需要WAV格式）
    temp_wav = "temp_processed.wav"
    normalized_audio.export(temp_wav, format="wav")
    
    print("音频预处理完成")
    return temp_wav

def extract_speech_to_text(audio_path):
    """
    提取音频中的语音内容：将语音转换为文本
    """
    recognizer = sr.Recognizer()
    
    print("开始语音识别...")
    
    # 使用音频文件作为输入源
    with sr.AudioFile(audio_path) as source:
        # 调整噪音水平
        recognizer.adjust_for_ambient_noise(source)
        audio_data = recognizer.record(source)
    
    try:
        # 使用Google Speech Recognition API进行识别
        text = recognizer.recognize_google(audio_data, language="zh-CN")
        print("语音识别完成")
        return text
    except sr.UnknownValueError:
        print("Google Speech Recognition无法理解音频")
        return ""
    except sr.RequestError as e:
        print(f"无法从Google Speech Recognition服务请求结果; {e}")
        return ""

def save_extracted_text(text, output_file="extracted_text.txt"):
    """
    保存所有识别出的文字，包括标题和正文内容
    """
    print(f"正在保存提取的文本到 {output_file}")
    
    # 尝试识别标题（假设标题通常是较短的语句，以句号或问号结束）
    lines = text.split('。')
    titles = []
    content = []
    
    for i, line in enumerate(lines):
        # 简单的启发式方法：较短的句子更可能是标题
        if len(line.strip()) < 30 and line.strip():
            titles.append(line.strip())
        else:
            content.append(line.strip())
    
    # 将提取的文本写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        # 写入主标题（如果有）
        if titles:
            f.write("# " + titles[0] + "\n\n")
            
            # 写入其他标题（如果有）
            for i, title in enumerate(titles[1:], 1):
                f.write("## " + title + "\n\n")
        
        # 写入正文内容
        f.write("\n".join(content))
    
    print(f"文本已保存至 {output_file}")
    return titles, content

def analyze_sentiment(text):
    """
    分析语音中的关键词情感：找出重要关键词并判断情感倾向
    """
    print("开始情感分析...")
    
    # 分词 - removed the download checks since we do it at the beginning
    words = word_tokenize(text)
    
    # 过滤掉常见停用词和标点符号
    stop_words = set(['的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己'])
    filtered_words = [word for word in words if word.isalnum() and word not in stop_words]
    
    # 提取关键词（简单用词频）
    from collections import Counter
    word_counts = Counter(filtered_words)
    keywords = [word for word, count in word_counts.most_common(20)]
    
    # 使用NLTK的情感分析器
    sia = SentimentIntensityAnalyzer()
    
    # 分析每个关键词的情感
    positive_words = []
    negative_words = []
    neutral_words = []
    
    for word in keywords:
        sentiment = sia.polarity_scores(word)
        if sentiment['compound'] >= 0.05:
            positive_words.append(word)
        elif sentiment['compound'] <= -0.05:
            negative_words.append(word)
        else:
            neutral_words.append(word)
    
    print("情感分析完成")
    return {
        "关键词": keywords,
        "积极情感词": positive_words,
        "消极情感词": negative_words,
        "中性情感词": neutral_words
    }

def save_sentiment_analysis(sentiment_data, output_file="sentiment_analysis.txt"):
    """
    保存情感分析结果
    """
    print(f"正在保存情感分析结果到 {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 情感分析结果\n\n")
        
        f.write("## 关键词\n")
        f.write(", ".join(sentiment_data["关键词"]) + "\n\n")
        
        f.write("## 积极情感词\n")
        f.write(", ".join(sentiment_data["积极情感词"]) + "\n\n")
        
        f.write("## 消极情感词\n")
        f.write(", ".join(sentiment_data["消极情感词"]) + "\n\n")
        
        f.write("## 中性情感词\n")
        f.write(", ".join(sentiment_data["中性情感词"]))
    
    print(f"情感分析结果已保存至 {output_file}")

def process_audio_file(audio_path):
    """
    处理音频文件并提取文字和情感
    """
    print("开始处理音频文件...")
    
    # 准备音频文件
    processed_audio = prepare_audio(audio_path)
    
    # 提取语音内容为文本
    text = extract_speech_to_text(processed_audio)
    
    # 保存提取的文本
    titles, content = save_extracted_text(text)
    
    # 分析文本的情感
    sentiment_data = analyze_sentiment(text)
    
    # 保存情感分析结果
    save_sentiment_analysis(sentiment_data)
    
    # 清理临时文件
    if os.path.exists(processed_audio):
        os.remove(processed_audio)
    
    print("音频处理完成！")
    
    return {
        "文本": text,
        "标题": titles,
        "正文": content,
        "情感分析": sentiment_data
    }

if __name__ == "__main__":
    # 用户输入音频文件路径
    input_audio = "/home/wzhangeb/lancet/task_test/test.mp3"     # input("请输入要处理的MP3文件路径: ")
    results = process_audio_file(input_audio)
    
    print("\n处理完成！")
    print(f"提取的文本已保存到 extracted_text.txt")
    print(f"情感分析结果已保存到 sentiment_analysis.txt")