import os
import requests
from typing import TypedDict, Dict, Any, List
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from ddgs import DDGS
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.embeddings import ZhipuAIEmbeddings
from langgraph.checkpoint.memory import MemorySaver

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

os.environ["ANTHROPIC_API_KEY"] = "your anthropic api key"
os.environ["ANTHROPIC_BASE_URL"] = "https://api.kimi.com/coding/"
os.environ["ZHIPUAI_API_KEY"] = "your zhipuai api key"

llm = ChatAnthropic(model="your model", temperature=0.3)


class ResearchState(TypedDict):
    topic: str
    target_url: str
    raw_data: str
    local_doc_path: str
    draft_report: str
    feedback: str
    final_report: str
    review_comments: str
    revision_count: int


def fetch_web_content(url: str) -> str:
    print(f"🕵️ [Researcher] 正在悄悄抓取网页: {url}")
    jina_url = f"https://r.jina.ai/{url}"
    headers = {"X-Return-Format": "markdown"}

    try:
        response = requests.get(jina_url, headers=headers)
        response.raise_for_status()
        return response.text[:15000]
    except Exception as e:
        return f"抓取失败: {str(e)}"


def query_private_knowledge(query: str, file_path: str) -> str:
    print(f"🔍 [DEBUG] query_private_knowledge 被调用了!")
    print(f"🔍 [DEBUG] file_path = {file_path}")
    print(f"🔍 [DEBUG] os.path.exists(file_path) = {os.path.exists(file_path)}")
    print(f"🔍 [DEBUG] os.getcwd() = {os.getcwd()}")
    print(f"🔍 [DEBUG] os.path.abspath(file_path) = {os.path.abspath(file_path)}")

    if not file_path or not os.path.exists(file_path):
        print(f"⚠️ [DEBUG] 文件不存在，直接返回空字符串")
        return ""

    print(f"📚 [Researcher] 正在翻阅本地私密档案: {file_path}")

    try:
        if file_path.lower().endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding='utf-8')
        docs = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        splits = text_splitter.split_documents(docs)

        print("🧠 [Researcher] 正在建立/读取本地向量大脑...")
        embeddings = ZhipuAIEmbeddings(
            zhipuai_api_key=os.environ.get("ZHIPUAI_API_KEY", "")
        )
        vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)

        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        relevant_docs = retriever.invoke(query)

        result = "\n\n".join(f"...{doc.page_content}..." for doc in relevant_docs)
        print(f"🔍 [DEBUG] 检索到的相关文档数量: {len(relevant_docs)}")
        print(f"🔍 [DEBUG] 检索结果内容: {result[:200]}...")
        vectorstore.delete_collection()

        print(f"🔍 [DEBUG] RAG 查询完成，返回结果长度: {len(result)}")
        return result
    except Exception as e:
        print(f"⚠️ [Researcher] 翻阅本地档案失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return ""


def search_web(query: str, max_results: int = 3) -> List[Dict[str, str]]:
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
    """信息搜集员：负责搜索网络和翻阅本地私有知识库"""
    topic = state.get("topic")
    local_doc_path = state.get("local_doc_path")

    print(f"🔍 [DEBUG] researcher_node 被调用了!")
    print(f"🔍 [DEBUG] topic = {topic}")
    print(f"🔍 [DEBUG] local_doc_path = {local_doc_path}")

    # --- 动作 1：翻阅本地私有知识库 (RAG) ---
    local_data = ""
    if local_doc_path:
        print(f"🔍 [DEBUG] 准备调用 query_private_knowledge...")
        local_data = query_private_knowledge(topic, local_doc_path)
        print(f"🔍 [DEBUG] query_private_knowledge 返回结果长度: {len(local_data)}")
    else:
        print(f"🔍 [DEBUG] local_doc_path 为空，跳过 RAG 查询")

    # --- 动作 2：网络搜索与抓取 ---
    search_results = search_web(topic, max_results=3)

    web_content_list = []
    if search_results:
        for i, result in enumerate(search_results, 1):
            print(f"🕵️ [Researcher] 正在抓取网络 [{i}/{len(search_results)}]: {result['title']}")
            content = fetch_web_content(result['url'])
            web_content_list.append(f"## 网络来源 {i}: {result['title']}\n{content}")
    else:
        url = state.get("target_url")
        if url:
            web_content_list.append(f"## 默认指定来源\n{fetch_web_content(url)}")

    web_data = "\n\n---\n\n".join(web_content_list)

    # --- 动作 3：双剑合璧 ---
    final_raw_data = ""
    if local_data:
        final_raw_data += f"【本地私密资料检索结果】\n{local_data}\n\n====================\n\n"
    final_raw_data += f"【网络公开资料】\n{web_data}"

    return {"raw_data": final_raw_data}


def analyst_node(state: ResearchState) -> Dict[str, Any]:
    """行业分析师：负责撰写 / 修改研究报告"""
    topic = state.get("topic", "")
    raw_data = state.get("raw_data", "")
    comments = state.get("review_comments", "")

    base_prompt = f"""你是一个资深的行业分析师。请根据以下参考资料，撰写一篇关于【{topic}】的深度分析报告。

## 参考资料（来自网络搜索 & 本地知识库）：
{raw_data if raw_data else "（无参考资料，请基于你的知识撰写）"}

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

请严格按照上述结构输出，确保每个部分都有实质内容。"""

    if comments and comments != "PASS":
        system_prompt = f"""你是一个资深的行业分析师。你的初稿被主编打回了，需要修改。

## 主编的修改意见：
{comments}

## 原报告（参考）：
{state.get("draft_report", "")}

## 参考资料：
{raw_data if raw_data else "（无参考资料）"}

请根据修改意见，重新修改报告。必须保留以下结构：
1. 核心摘要
2. 优缺点对比（✅优点 / ❌缺点）
3. 适合的应用场景
4. 发展趋势与建议

请严格按照上述结构输出，确保每个部分都有实质内容。"""
    else:
        system_prompt = base_prompt

    print("📝 [行业分析师] 正在撰写/修改研究报告...")
    response = llm.invoke(system_prompt)
    return {"draft_report": response.content}


def reviewer_node(state: ResearchState) -> Dict[str, Any]:
    """毒舌审查官：负责审核分析师的初稿"""
    print("🧐 [毒舌审查官] 正在审阅初稿...")
    draft = state.get("draft_report", "")

    prompt = f"""你是一个极其严苛的研究主编。你的任务是审查分析师写的初稿。
    初稿内容：
    {draft}

    请严格按以下格式输出你的审查结果：
    如果你觉得质量很好，请直接回复（不要加别的废话）："DECISION: PASS"
    如果你觉得很差，请回复："DECISION: REJECT" 换行后写上具体的修改意见。
    """

    response = llm.invoke(prompt).content
    current_count = state.get("revision_count", 0)

    if "DECISION: PASS" in response:
        print("✅ [毒舌审查官] 审核通过，放行给人类主编！")
        return {"review_comments": "PASS", "revision_count": current_count + 1}
    else:
        comments = response.replace("DECISION: REJECT", "").strip()
        print(f"❌ [毒舌审查官] 打回重写！意见：{comments[:30]}...")
        return {"review_comments": comments, "revision_count": current_count + 1}


def route_after_review(state: ResearchState) -> str:
    """条件路由：AI 审查官审核后，决定是打回重写还是交给人类终审"""
    comments = state.get("review_comments", "")
    count = state.get("revision_count", 0)

    if comments == "PASS" or count >= 2:
        return "Human_Review"
    else:
        return "Analyst"


def human_review_node(state: ResearchState) -> Dict[str, Any]:
    """人工审核主编：负责在用户确认后推进流程"""
    feedback = state.get("feedback", "")
    draft = state.get("draft_report", "")

    if feedback == "APPROVED":
        print("✅ [审查官] 审核通过，准备发布！")
        return {"final_report": draft}
    else:
        print(f"❌ [审查官] 审核不通过，打回重写！修改意见：{feedback}")
        return {}


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

    # 保存到后端 outputs 文件夹
    os.makedirs("outputs", exist_ok=True)
    file_name = "outputs/report.md"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(response.content)
    print(f"💾 [排版发布员] 报告已保存在后端：{file_name}")

    return {"final_report": response.content}


def build_graph():
    workflow = StateGraph(ResearchState)

    workflow.add_node("Researcher", researcher_node)
    workflow.add_node("Analyst", analyst_node)
    workflow.add_node("Reviewer", reviewer_node)
    workflow.add_node("Human_Review", human_review_node)
    workflow.add_node("Publisher", publisher_node)

    workflow.add_edge(START, "Researcher")
    workflow.add_edge("Researcher", "Analyst")
    workflow.add_edge("Analyst", "Reviewer")
    workflow.add_conditional_edges("Reviewer", route_after_review)
    workflow.add_edge("Human_Review", "Publisher")
    workflow.add_edge("Publisher", END)

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory, interrupt_before=["Human_Review"])


app_graph = build_graph()


if __name__ == "__main__":
    print("🚀 自动化行业研究系统启动...")

    script_dir = os.path.dirname(os.path.abspath(__file__))

    initial_state = {
        "topic": "LangGraph 与 CrewAI 的对比分析",
        "target_url": "https://www.langchain.com/langgraph",
        "local_doc_path": os.path.join(script_dir, "secret_memo.txt"),
        "raw_data": "",
        "draft_report": "",
        "feedback": "",
        "final_report": "",
        "review_comments": "",
        "revision_count": 0,
    }

    for output in app_graph.stream(initial_state):
        print("Agent 正在运行...")

    final_state = app_graph.invoke(initial_state)

    if final_state.get("final_report"):
        with open("example_report.md", "w", encoding="utf-8") as f:
            f.write(final_state["final_report"])
        print("\n🎉 任务完成！报告已保存至 example_report.md")
