# RAG服务层，处理检索增强生成相关的业务逻辑
from typing import List, TypedDict, Generator
from langchain.schema import Document
from langchain.prompts import PromptTemplate
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import START, StateGraph
from bson import ObjectId

from services.vector_service import VectorService
from config.settings import ai_config
from config.database import db_client

class RAGService:
    """RAG检索增强生成服务"""
    
    def __init__(self):
        """初始化RAG服务"""
        self.vector_service = VectorService()
        
        # 初始化DeepSeek LLM
        self.llm = ChatDeepSeek(
            model='deepseek-chat',
            temperature=0.3,
            streaming=True,
            api_key=ai_config.deepseek_api_key
        )
        
        # 定义QA提示模板
        self.qa_prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""你是一个专业 AI 助手。以下是你可以参考的文档：
{context}

用户问题：{question}

请结合文档内容回答，并在必要时给出参考来源,并附上参考来源的文档ID。

🔥 重要：请使用 HTML 格式输出，确保格式清晰美观。

格式要求：
1. 使用 <p> 标签包裹段落
2. 使用 <strong> 或 <b> 标签标识重要内容
3. 使用 <em> 或 <i> 标签标识强调内容
4. 使用 <ul> 和 <li> 标签创建无序列表
5. 使用 <ol> 和 <li> 标签创建有序列表
6. 使用 <br> 标签换行
7. 使用 <code> 标签标识代码或特殊文本
8. 使用 <blockquote> 标签标识引用
9. 使用 <table>、<thead>、<tbody>、<tr>、<th>、<td> 标签创建表格
10. 不要使用 Markdown 语法，只使用纯 HTML

示例输出格式：
<p>根据文档内容，以下是答案：</p>
<p><strong>主要观点：</strong>这是重要内容。</p>
<ul>
  <li>第一点说明</li>
  <li>第二点说明</li>
</ul>
<p>详细说明文本...</p>

请严格按照 HTML 格式输出，不要使用 Markdown。

"""


# 格式要求：
# 1. 使用换行符分隔段落，确保输出内容结构清晰
# 2. 数学公式使用 LaTeX 格式，行内公式使用 $...$ 标识
# 3. 块级公式使用 $$...$$
# 4. 重要概念或关键词使用 **粗体** 标识
# 5. 如有列表，请使用标准的 Markdown 格式

# 示例：
# 当讨论物理定律时，牛顿第二定律可表示为：
# $$F = ma$$
# 其中 $F$ 是力，$m$ 是质量，$a$ 是加速度。

        )
        
        # 构建RAG链
        self.rag_chain = self._build_rag_chain()
    
    def _build_rag_chain(self):
        """构建RAG处理链"""
        
        # 定义状态类型
        class State(TypedDict):
            question: str
            user_id: str 
            continue_chat: bool
            context: List[Document]
            answer: str
        
        def retrieve(state: State):
            """检索步骤：根据问题检索相关文档"""
            query = state['question']
            user_id = state.get('user_id')
            
            # 获取向量搜索结果
            results = self.vector_service.search_embedding(query, user_id, top_k=5)
            
            docs = []
            for score, doc_id in results:
                # 从todosContent集合获取完整内容
                content = db_client.todosContent.find_one({"_id": ObjectId(doc_id)})
                if content and content['user_id'] == user_id:
                    # 合并用户内容和提取内容
                    full_content_parts = []
                    
                    # 用户输入的内容
                    if content.get("content"):
                        full_content_parts.append(content["content"])
                    
                    # 提取的内容
                    if content.get("extracted_content"):
                        extracted = content["extracted_content"]
                        
                        # OCR文本
                        if extracted.get("ocr_texts") and len(extracted["ocr_texts"]) > 0:
                            ocr_section = "【图片识别内容】\n" + "\n".join(extracted["ocr_texts"])
                            full_content_parts.append(ocr_section)
                        
                        # 文档文本
                        if extracted.get("file_texts") and len(extracted["file_texts"]) > 0:
                            file_section = "【文档提取内容】\n" + "\n".join(extracted["file_texts"])
                            full_content_parts.append(file_section)
                    
                    # 合并所有内容传给LLM
                    full_content = "\n\n".join(full_content_parts)
                    
                    docs.append(Document(
                        page_content=full_content,
                        metadata={
                            "doc_id": doc_id,
                            "score": score,
                            "user_id": user_id
                        }
                    ))
            
            return {"context": docs}
        
        def generate(state: State):
            """生成步骤：基于检索到的文档生成回答"""
            docs_content = "\n\n".join(doc.page_content for doc in state["context"])
            
            # 如果是继续对话，添加提示
            continue_prefix = ""
            if state.get("continue_chat", False):
                continue_prefix = "这是用户重新进入对话的继续。请继续之前的回答。\n"
            
            # 格式化提示
            formatted_prompt = self.qa_prompt.format(
                context=docs_content,
                question=f"{continue_prefix}{state['question']}"
            )
            
            # 返回生成器，方便SSE流式输出
            def stream_answer():
                try:
                    for chunk in self.llm.stream(formatted_prompt):
                        yield chunk.content
                    
                    # 生成结束后，附加参考来源
                    if state["context"]:
                        yield "\n\n参考文档：\n" + "\n".join(
                            [f"- doc_id: {doc.metadata['doc_id']} (score={doc.metadata['score']:.4f})"
                             for doc in state["context"]]
                        )
                except Exception as e:
                    yield f"\n\n生成回答时发生错误: {str(e)}"
            
            return {"answer": stream_answer}
        
        # 构建状态图
        graph_builder = StateGraph(State)

        graph_builder.add_node("retrieve", retrieve)
        graph_builder.add_node("generate", generate)
        graph_builder.add_edge(START, "retrieve")
        graph_builder.add_edge("retrieve", "generate")
        
        return graph_builder.compile()
    
    def process_question(self, question: str, user_id: str, continue_chat: bool = False) -> dict:
        """
        处理用户问题，返回RAG结果
        
        Args:
            question: 用户问题
            user_id: 用户ID
            continue_chat: 是否继续对话
            
        Returns:
            dict: 包含answer生成器的结果
        """
        state = {
            "question": question,
            "user_id": user_id,
            "continue_chat": continue_chat
        }
        
        return self.rag_chain.invoke(state)
    
    def get_relevant_documents(self, query: str, user_id: str, top_k: int = 5) -> List[Document]:
        """
        获取相关文档（不生成回答）
        
        Args:
            query: 查询文本
            user_id: 用户ID
            top_k: 返回文档数量
            
        Returns:
            List[Document]: 相关文档列表
        """
        results = self.vector_service.search_embedding(query, user_id, top_k)
        
        docs = []
        for score, doc_id in results:
            content = db_client.todosContent.find_one({"_id": ObjectId(doc_id)})
            if content and content['user_id'] == user_id:
                docs.append(Document(
                    page_content=content["content"],
                    metadata={
                        "doc_id": doc_id,
                        "score": score,
                        "user_id": user_id,
                        "todo_id": content.get("todo_id", ""),
                        "created_at": content.get("created_at", "")
                    }
                ))
        
        return docs


