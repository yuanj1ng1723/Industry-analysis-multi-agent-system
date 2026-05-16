import os
import requests
from typing import TypedDict, Dict, Any, List
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from ddgs import DDGS

# ==========================================
# 0. 环境与 API 密钥配置 (请在终端或环境变量中设置)
# ==========================================
os.environ["ANTHROPIC_API_KEY"] = "sk-Your own API key"
os.environ["ANTHROPIC_BASE_URL"] = "https://api.kimi.com/coding/" # 如果使用代理或中转

# 初始化大模型 (你可以换成你常用的模型，比如 DeepSeek, Qwen 等)
llm = ChatAnthropic(model="kimi-k2.5", temperature=0.3)

# ==========================================
# 1. 定义状态 (State) - Agent 之间共享的"记忆字典"
# ==========================================
class ResearchState(TypedDict):
    topic: str              # 用户想研究的主题，例如 "最新的 AI Agent 框架"
    target_url: str         # 需要爬取的目标网址
    raw_data: str           # 爬虫抓取回来的原始内容
    draft_report: str       # 分析师写的初稿
    feedback: str           # 人类审核给出的修改意见
    final_report: str       # 最终定稿

# ==========================================
# 2. 定义核心工具 (Tools) - 用 Jina 解决反爬痛点
# ==========================================
def fetch_web_content(url: str) -> str:
    """使用 Jina Reader 抓取网页并返回纯净的 Markdown"""
    print(f"🕵️ [Researcher] 正在悄悄抓取网页: {url}")
    jina_url = f"https://r.jina.ai/{url}"
    headers = {"X-Return-Format": "markdown"}
    
    try:
        response = requests.get(jina_url, headers=headers)
        response.raise_for_status()
        # 截断数据以防上下文超载 (可根据你的模型上下文窗口调整)
        return response.text[:15000] 
    except Exception as e:
        return f"抓取失败: {str(e)}"

# ==========================================
# 3. 定义节点 (Nodes) - 每个 Node 就像是一个员工
# ==========================================
def search_web(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """使用 DuckDuckGo 搜索相关网页"""
    print(f"🔍 [Researcher] 正在搜索: {query}")
    results = []
    try:
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("body", "")[:200]
                })
                if len(results) >= max_results:
                    break
        print(f"✅ [Researcher] 找到 {len(results)} 个相关结果")
    except Exception as e:
        print(f"⚠️ [Researcher] 搜索失败: {str(e)}")
    return results

def researcher_node(state: ResearchState) -> Dict[str, Any]:
    """信息搜集员：负责搜索和抓取数据"""
    topic = state.get("topic")
    
    # 1. 先根据主题搜索前 3 个相关网页
    search_results = search_web(topic, max_results=3)
    
    if not search_results:
        print("⚠️ [Researcher] 搜索无结果，尝试抓取默认 URL")
        url = state.get("target_url")
        if url:
            scraped_content = fetch_web_content(url)
        else:
            scraped_content = "无法获取内容：搜索和 URL 都失败"
        return {"raw_data": scraped_content}
    
    # 2. 抓取这 3 个网页的 Markdown 内容
    all_content = []
    for i, result in enumerate(search_results, 1):
        print(f"🕵️ [Researcher] 正在抓取 [{i}/{len(search_results)}]: {result['title']}")
        content = fetch_web_content(result['url'])
        all_content.append(f"## 来源 {i}: {result['title']}\n{result['snippet']}\n\n{content}")
    
    # 3. 拼接所有内容
    combined_content = "\n\n---\n\n".join(all_content)
    
    # 将抓取到的数据保存到 state 的 raw_data 中，传递给下一个节点
    return {"raw_data": combined_content}

def analyst_node(state: ResearchState) -> Dict[str, Any]:
    """数据分析师：负责阅读 raw_data 并生成/修改分析报告"""
    print("✍️ [Analyst] 正在笔耕不辍地撰写分析报告...")
    topic = state.get("topic")
    raw_data = state.get("raw_data")
    feedback = state.get("feedback", "")
    
    # 优化的 Prompt - 强制结构化输出
    base_instructions = f"""你是一个资深的行业分析师。请根据以下资料，撰写一篇关于【{topic}】的深度分析报告。

## 必须包含的内容（结构化 Markdown 格式）：

### 1. 核心摘要 (Executive Summary)
- 用 2-3 句话概括主题的核心要点
- 说明这个主题为什么重要

### 2. 优缺点对比 (Pros & Cons)
#### ✅ 优点
- 列出至少 3 个主要优点

#### ❌ 缺点
- 列出至少 3 个主要缺点

### 3. 适合的应用场景 (Use Cases)
- 列出 3-5 个典型的应用场景
- 简要说明每个场景的价值

### 4. 发展趋势与建议
- 分析未来发展趋势
- 给出实施建议

---
## 参考资料：
{raw_data}

请严格按照上述结构输出，确保每个部分都有实质内容。"""

    if not feedback:
        system_prompt = base_instructions
    else:
        system_prompt = f"""你是一个资深的行业分析师。你的初稿被老板打回了，需要修改。

## 老板的修改意见：
【{feedback}】

## 原资料：
{raw_data}

请根据修改意见，重新修改报告。必须保留以下结构：
1. 核心摘要
2. 优缺点对比（✅优点 / ❌缺点）
3. 适合的应用场景
4. 发展趋势与建议

请严格按照上述结构输出，确保每个部分都有实质内容。"""
    
    # 调用大模型生成报告
    response = llm.invoke(system_prompt)
    
    return {"draft_report": response.content}

def human_review_node(state: ResearchState) -> Dict[str, Any]:
    """审核主编：负责在终端打印报告，并等待你(人类)的审核"""
    print("\n" + "="*50)
    print("📑 【分析报告初稿】")
    print(state.get("draft_report"))
    print("="*50 + "\n")
    
    # 终端交互，获取人类反馈
    user_input = input("🙋 [主编/你] 请审核。如果满意请输入 'Y'，如果不满意请输入修改意见：")
    
    if user_input.strip().upper() == 'Y':
        print("✅ 审核通过，准备发布！")
        return {"feedback": "APPROVED", "final_report": state.get("draft_report")}
    else:
        print("❌ 审核不通过，打回重写！")
        return {"feedback": user_input}

def publisher_node(state: ResearchState) -> Dict[str, Any]:
    """排版发布员：负责将报告翻译成英文并加上精美 Emoji 排版"""
    print("📝 [Publisher] 正在翻译并美化排版...")
    final_report = state.get("final_report", "")
    
    system_prompt = f"""你是一个专业的技术文档排版师。请将以下中文报告翻译成英文，并添加精美的 Emoji 排版。

## 要求：
1. 完整翻译成英文
2. 添加合适的 Emoji 来增强可读性（每个章节标题前加 Emoji，列表项适当加 Emoji）
3. 保持 Markdown 格式
4. 保持专业语气
5. 适当增加装饰性的分隔线和格式

## 原文：
{final_report}

请输出翻译并排版后的完整报告。"""

    response = llm.invoke(system_prompt)
    
    return {"final_report": response.content}

# ==========================================
# 4. 定义条件边逻辑 (Conditional Edges)
# ==========================================
def review_decision(state: ResearchState) -> str:
    """根据审核结果决定下一步去哪"""
    if state.get("feedback") == "APPROVED":
        return "publisher" # 审核通过，进入 Publisher
    else:
        return "rewrite" # 打回给分析师重写

# ==========================================
# 5. 构建工作流图 (Graph) - 组装流水线
# ==========================================
workflow = StateGraph(ResearchState)

# 添加节点
workflow.add_node("Researcher", researcher_node)
workflow.add_node("Analyst", analyst_node)
workflow.add_node("Human_Review", human_review_node)
workflow.add_node("Publisher", publisher_node)

# 画边 (定义流程走向)
workflow.add_edge(START, "Researcher")
workflow.add_edge("Researcher", "Analyst")
workflow.add_edge("Analyst", "Human_Review")

# 添加条件边：Human_Review 结束后，根据 review_decision 的结果决定去向
workflow.add_conditional_edges(
    "Human_Review",
    review_decision,
    {
        "publisher": "Publisher", # 新增：审核通过后进入 Publisher
        "rewrite": "Analyst"       # 形成了一个循环 (Loop)
    }
)

# Publisher 节点结束后直接结束
workflow.add_edge("Publisher", END)

# 编译图
app = workflow.compile()

# ==========================================
# 6. 主程序运行 (Main)
# ==========================================
if __name__ == "__main__":
    print("🚀 自动化行业研究系统启动...")
    
    # 初始化输入状态
    initial_state = {
        "topic": "LangGraph 与 CrewAI 的对比分析",
        "target_url": "https://www.langchain.com/langgraph", # 随便找一个相关的测试网址
        "raw_data": "",
        "draft_report": "",
        "feedback": "",
        "final_report": ""
    }
    
    # 运行工作流
    final_state = app.invoke(initial_state)
    
    # 保存最终结果到本地文件
    if final_state.get("final_report"):
        with open("research_report.md", "w", encoding="utf-8") as f:
            f.write(final_state["final_report"])
        print("\n🎉 任务完成！报告已保存至 research_report.md")