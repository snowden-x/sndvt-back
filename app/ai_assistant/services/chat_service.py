"""Chat service for handling streaming responses."""

import json
import time
import asyncio
from typing import AsyncGenerator
from langchain.chains import RetrievalQA

from app.config import get_settings
from .model_service import ModelService


class ChatService:
    """Service for handling chat interactions and streaming responses."""
    
    def __init__(self, model_service: ModelService):
        self.model_service = model_service
        self.settings = get_settings()
        
    async def stream_query_response(self, query: str) -> AsyncGenerator[str, None]:
        """Stream the response from the LLM in real-time."""
        qa_chain = self.model_service.get_qa_chain()
        llm = self.model_service.get_llm()
        
        if qa_chain is None:
            yield json.dumps({"error": "QA chain is not initialized"})
            return
        
        # Preprocess query for better results
        query = query.strip()
        if not query:
            yield json.dumps({"error": "Empty query provided"})
            return
        
        # Limit query length to prevent issues
        if len(query) > self.settings.max_query_length:
            query = query[:self.settings.max_query_length] + "..."
            print(f"⚠️ Query truncated to {self.settings.max_query_length} characters")
        
        print(f"🚀 Starting streaming response for: {query[:50]}...")
        stream_start_time = time.time()
        
        try:
            if isinstance(qa_chain, RetrievalQA):
                # For retrieval QA, we need to handle streaming differently
                print("📚 Using RetrievalQA with streaming")
                
                # Get relevant documents first (with timeout to prevent hanging)
                retrieval_start_time = time.time()
                retriever = qa_chain.retriever
                try:
                    docs = await asyncio.wait_for(retriever.ainvoke(query), timeout=5.0)
                    retrieval_end_time = time.time()
                    print(f"⏱️ Document retrieval took: {retrieval_end_time - retrieval_start_time:.2f}s")
                    print(f"📄 Retrieved {len(docs)} documents")
                except asyncio.TimeoutError:
                    retrieval_end_time = time.time()
                    print(f"⏱️ Document retrieval timed out after: {retrieval_end_time - retrieval_start_time:.2f}s")
                    print("⚠️ Document retrieval timeout, using general knowledge")
                    docs = []
                
                # Prepare context with smart truncation for performance
                context_parts = []
                total_chars = 0
                
                for doc in docs:
                    if total_chars + len(doc.page_content) > self.settings.max_context_chars:
                        remaining_space = self.settings.max_context_chars - total_chars
                        if remaining_space > 100:  # Only add if there's reasonable space
                            context_parts.append(doc.page_content[:remaining_space] + "...")
                        break
                    
                    context_parts.append(doc.page_content)
                    total_chars += len(doc.page_content)

                # Handle empty context gracefully
                if context_parts:
                    context = "\n\n".join(context_parts)
                    prompt_text = self.model_service.custom_prompt.format(context=context, question=query)
                    print(f"📝 Using documentation context ({total_chars} chars)")
                else:
                    # Fallback to general knowledge prompt if no useful context
                    prompt_text = self.model_service.general_prompt.format(query=query)
                    print("🧠 Using general knowledge (no relevant documentation found)")
                
                # Stream the LLM response
                print("🔄 Starting LLM streaming...")
                llm_start_time = time.time()
                first_chunk_received = False
                accumulated_response = ""
                
                async for chunk in llm.astream(prompt_text):
                    if not first_chunk_received:
                        first_chunk_time = time.time()
                        print(f"⏱️ Time to first token from LLM: {first_chunk_time - llm_start_time:.2f}s")
                        first_chunk_received = True

                    accumulated_response += chunk
                    yield json.dumps({
                        "type": "chunk",
                        "content": chunk,
                        "accumulated": accumulated_response
                    })
                
                # Send final message with sources
                total_time = time.time() - stream_start_time
                print(f"⏱️ Total stream processing time: {total_time:.2f}s")
                yield json.dumps({
                    "type": "complete",
                    "content": accumulated_response,
                    "sources": [doc.metadata.get('source', 'Unknown') for doc in docs],
                    "used_documentation": len(docs) > 0,
                    "context_size": total_chars if 'total_chars' in locals() else 0,
                    "documents_used": len(docs)
                })
                
            else:
                # Direct LLM streaming
                print("🤖 Using direct LLM streaming")
                accumulated_response = ""
                
                async for chunk in qa_chain.llm.astream(f"Question: {query}\n\nAnswer:"):
                    accumulated_response += chunk
                    yield json.dumps({
                        "type": "chunk", 
                        "content": chunk,
                        "accumulated": accumulated_response
                    })
                
                # Send completion
                yield json.dumps({
                    "type": "complete",
                    "content": accumulated_response,
                    "sources": [],
                    "used_documentation": False
                })
                
        except Exception as e:
            print(f"❌ Error during streaming: {e}")
            yield json.dumps({
                "type": "error",
                "error": f"Error processing query: {str(e)}"
            }) 