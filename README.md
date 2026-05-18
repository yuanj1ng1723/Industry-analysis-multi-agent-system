# 🚀 Auto-Research-Agent: 智能深度行研系统 (Web UI 版)

本项目是一个基于 **LangGraph** 构建的企业级多智能体自动化行业研究系统。摒弃了传统的黑盒 Agent 模式，采用**状态机（StateGraph）**精确控制业务流转。

在最新的版本中，我们引入了 **Streamlit Web 交互界面** 和 **私有知识库 (RAG)**，并首创了 **AI 审查 + 人类主编（Human-in-the-loop）的双重审核机制**，确保最终输出的分析报告兼具 AI 的高效与人类的专业严谨。

## ✨ 核心亮点 (Features)

- **🖥️ 全新可视化工作台**：基于 Streamlit 开发的现代化 Web UI，支持会话隔离（Session Memory），支持多用户并发访问不串线。
- **📚 本地知识库增强 (RAG)**：支持一键上传 PDF/TXT 私密资料，底层采用 `Chroma` 向量数据库与 `ZhipuAI` 文本嵌入，实现本地档案与全网公开资讯的“双剑合璧”。
- **🕸️ LangGraph 细粒度控制**：构建了包含 `Researcher`, `Analyst`, `AI Reviewer`, `Publisher` 等角色的有向图工作流，支持审核打回的循环重写（Cyclic Loop）。
- **🛡️ 双重审核机制**：
  - **AI 毒舌审查官 (Reflexion)**：内部多轮自我博弈，自动打回低质量报告。
  - **人机协作 (Human-in-the-loop)**：在研报发布的关键节点，UI 界面会自动挂起（Paused），等待人类主编通过操作台输入修改意见或一键发布。
- **📥 自动化排版与导出**：最终报告自动翻译为英文并增加精美 Emoji 排版，支持一键下载 Markdown 文件。

## 🏗️ 架构设计 (Workflow)

```mermaid
graph TD
    A[START] --> B[🕵️ Researcher Node: 联网搜索 + 本地 RAG]
    B --> C[✍️ Analyst Node: LLM 生成分析初稿]
    C --> D[🧐 AI Reviewer: 毒舌审查官初审]
    D -- AI 审核不通过 (打回) --> C
    D -- AI 审核通过 / 达最大重试次数 --> E{🙋 Human Review: 人类主编终审}
    E -- 前端输入修改意见 (打回) --> C
    E -- 完美直接发布 (APPROVED) --> F[📝 Publisher Node: 英文翻译与精美排版]
    F --> G[END: 前端展示及 Markdown 下载]


🛠️ 快速开始 (Quick Start)
1. 环境准备
确保你已经安装了 Python 3.9+，然后克隆项目并安装依赖：

Bash
git clone https://github.com/你的用户名/Auto-Research-Agent.git
cd Auto-Research-Agent
pip install -r requirements.txt
2. 配置环境变量
请在项目根目录创建 .env 文件或在终端中导出以下环境变量（系统同时接入了 Anthropic/Kimi 与 智谱 AI）：

Bash
export ANTHROPIC_API_KEY="your-kimi-or-anthropic-key"
export ANTHROPIC_BASE_URL="https://api.kimi.com/coding/" # (可选，如使用 Kimi)
export ZHIPUAI_API_KEY="your-zhipu-api-key"
3. 启动 Web 服务
Bash
streamlit run app.py
启动后，在浏览器访问 http://localhost:8501 即可体验！

📦 依赖栈 (Tech Stack)
Agent Framework: LangGraph, LangChain Core
LLM & Embeddings: Kimi (ChatAnthropic), ZhipuAI Embeddings
Web UI: Streamlit
RAG & VectorStore: ChromaDB, HuggingFace
Search Engine: DuckDuckGo Search (DDGS) + Jina Reader API
Text
---
### 📢 二、GitHub Release 发版说明 (Changelog)
在 GitHub 上打 Tag (比如 `v2.0.0`) 时，可以在 Releases 页面填写以下更新日志。这能向面试官展示你具备规范的代码发布习惯。
**标题**：`v2.0.0: Streamlit Web UI, RAG Integration & Dual-Review System 🚀`
**详细描述**：
```markdown
在这个大版本更新中，系统从底层的命令行脚本正式进化为了一个带交互界面的企业级大模型应用。
### 🌟 新特性 (New Features)
- **Web 可视化界面**: 引入 `Streamlit` 替代 CLI，提供沉浸式的操作体验，支持报告实时预览与 Markdown 一键下载。
- **并发状态管理**: 在 `app.py` 中利用 UUID 分配 `thread_id` 结合 LangGraph 的 `MemorySaver`，彻底解决了多轮对话记忆与状态隔离问题。
- **RAG 私有知识库**: 新增侧边栏文件上传功能。底层集成 `Chroma` 向量数据库、`PyPDFLoader` 及 `ZhipuAIEmbeddings`，实现私密文档与联网搜索的双重信源融合。
- **AI "毒舌"审查节点**: 优化了图结构，在进入人工审核（Human-in-the-loop）前，新增 `reviewer_node` 进行自我反思与打回，大幅减轻人类主编的审查压力。
### 🔧 优化 (Improvements)
- 将人机协同的修改意见反馈通道，从终端标准输入（stdin）平滑迁移至 Streamlit 的状态更新 (`app_graph.update_state`)。
- 增加了针对各类无意义抓取内容的容错处理（Try-Except 与 Jina 返回截断）。
### ⚠️ 安全提示 (Security Note)
- 请确保不要将包含实际 API Key 的文件推送到公共仓库。
💡 给你的额外建议：
