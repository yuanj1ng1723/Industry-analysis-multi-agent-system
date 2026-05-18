import streamlit as st
import tempfile
import os
import uuid

# 导入你写好的 Agent 图
from industry_research_agent import app_graph 

st.set_page_config(page_title="DeepResearch AI", page_icon="🕵️‍♂️", layout="wide")

# ==========================================
# 核心机制 1：为当前用户分配一个专属的“对话 ID”
# 这是调用 MemorySaver 必须的，有了 ID，Agent 才能记住是谁在跑任务
# ==========================================
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4()) 
config = {"configurable": {"thread_id": st.session_state.thread_id}}


st.title("🕵️‍♂️ DeepResearch AI - 智能深度行研系统")
st.markdown("**💡 系统能力**：结合 **联网搜索** 与 **私有知识库检索 (RAG)**，并支持 **Human-in-the-Loop (人机协同审核)**。")

# 侧边栏
with st.sidebar:
    st.header("📂 投喂私有资料 (RAG)")
    uploaded_file = st.file_uploader("支持 PDF 或 TXT 文件", type=['txt', 'pdf'])

# ==========================================
# 核心机制 2：向图获取当前的状态，判断是否处于“暂停(断点)”状态
# ==========================================
graph_state = app_graph.get_state(config)
# 如果 next 列表里有 "Human_Review"，说明被我们设置的 interrupt_before 拦截了！
is_paused = len(graph_state.next) > 0 and graph_state.next[0] == "Human_Review"


# 场景 A：还没有开始，或者已经跑完了，显示输入框
if not is_paused:
    topic = st.text_input("🎯 请输入您想研究的课题：", placeholder="例如：2024年 AI Agent 发展趋势与商业化前景")

    # 如果有历史最终报告，直接展示在下面
    if graph_state.values.get("final_report"):
        st.success("🎉 研究完成！以下是最终报告：")
        with st.container(border=True):
            st.markdown(graph_state.values.get("final_report"))

        # 下载报告按钮
        final_report = graph_state.values.get("final_report", "")
        st.download_button(
            label="📥 下载报告 (Markdown)",
            data=final_report,
            file_name=f"行业研究报告_{topic[:20]}.md",
            mime="text/markdown",
            type="primary",
            use_container_width=True,
        )

        # 重新开始按钮
        if st.button("🔄 开启新课题（清空记忆）"):
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()

    # 点击开始运行
    elif st.button("🚀 开始深度研究", type="primary"):
        if not topic:
            st.warning("⚠️ 请先输入研究课题！")
        else:
            local_doc_path = ""
            if uploaded_file is not None:
                file_extension = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    local_doc_path = tmp_file.name
                    
            initial_state = {
                "topic": topic,
                "target_url": "", 
                "local_doc_path": local_doc_path, 
                "raw_data": "", "draft_report": "", "feedback": "", "final_report": ""
            }

            with st.spinner("🤖 Agent 团队正在爆肝检索与撰写初稿中，请稍候..."):
                # 注意：这里会一直运行，直到遇到 "Human_Review" 的断点才会停下
                app_graph.invoke(initial_state, config)
            
            # 运行到断点后，刷新页面，触发下方“场景 B”的代码
            st.rerun()


# 场景 B：Agent 跑到一半被暂停了！显示审核界面！
if is_paused:
    st.warning("⏸️ Agent 已完成初稿撰写，进入暂停状态。请您（主编）进行审核！")
    
    # 从记忆中提取出刚刚写好的初稿
    current_draft = graph_state.values.get("draft_report", "（未获取到初稿内容）")
    
    st.markdown("### 📑 报告初稿")
    with st.container(border=True, height=400):
        st.markdown(current_draft)
        
    st.markdown("### ✍️ 人类主编审核操作台")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.info("如果报告写得很棒，可以直接一键排版发布。")
        if st.button("✅ 完美，直接发布！", type="primary", use_container_width=True):
            # 核心魔法：直接在前端把意见写入 Agent 的记忆里
            app_graph.update_state(config, {"feedback": "APPROVED"})
            
            with st.spinner("✨ 发布官正在进行 Emoji 排版翻译，即将出炉..."):
                # 传入 None，告诉 Agent 解除暂停，继续往下跑！
                app_graph.invoke(None, config) 
            st.rerun()
            
    with col2:
        st.info("如果觉得哪里不好，写下意见，让分析师重写。")
        feedback_text = st.text_area("修改意见：", placeholder="例如：优缺点部分太敷衍了，请再重点分析一下安全性问题...")
        if st.button("❌ 严厉打回重写", type="secondary", use_container_width=True):
            if feedback_text.strip():
                # 把修改意见塞进记忆
                app_graph.update_state(config, {"feedback": feedback_text})
                
                with st.spinner("🔄 分析师正在看着你的意见，流着泪回炉重造..."):
                    app_graph.invoke(None, config)
                st.rerun()
            else:
                st.error("打回重写必须给出修改意见哦！")