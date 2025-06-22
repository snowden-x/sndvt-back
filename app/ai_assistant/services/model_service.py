"""Model management service."""

import time
import subprocess
from typing import Optional
from langchain_ollama import OllamaLLM as Ollama
from langchain.chains import RetrievalQA, LLMChain
from langchain.prompts import PromptTemplate

from app.config import get_settings


class ModelService:
    """Service for managing Ollama models and LLM chains."""
    
    def __init__(self):
        self.settings = get_settings()
        self.llm: Optional[Ollama] = None
        self.qa_chain = None
        
        # Enhanced prompt template with better structure and efficiency
        self.custom_prompt = """You are a Senior Network Engineer AI Assistant. Follow these guidelines for optimal responses:

RESPONSE STRUCTURE:
1. Give a direct, concise answer first
2. Provide technical details if needed
3. Include actionable steps when applicable

CONTEXT RULES:
- If documentation context is provided below, prioritize it over general knowledge
- If no relevant context, rely on your networking expertise
- Always indicate your information source

EFFICIENCY GUIDELINES:
- Be precise and avoid unnecessary verbosity
- Use bullet points for lists and steps
- Include specific commands, IPs, or configurations when relevant
- If analyzing logs/configs, highlight key findings first

DOCUMENTATION CONTEXT:
{context}

QUESTION: {question}

RESPONSE:"""

        # Efficient prompt for general knowledge (no documentation context)
        self.general_prompt = """You are a Senior Network Engineer AI Assistant. Provide expert networking guidance.

RESPONSE GUIDELINES:
- Give direct, actionable answers
- Use bullet points for clarity
- Include specific commands/configurations when relevant
- Be concise but comprehensive

QUESTION: {query}

RESPONSE:"""

    async def initialize_llm(self) -> Ollama:
        """Initialize Ollama with performance optimizations."""
        print("🤖 Initializing Ollama with performance optimizations...")
        self.llm = Ollama(
            model=self.settings.ollama_llm_model,
            temperature=self.settings.ollama_temperature,
            top_p=self.settings.ollama_top_p,
            top_k=self.settings.ollama_top_k,
            num_predict=self.settings.ollama_num_predict,
        )
        return self.llm
        
    async def preload_and_warm_model(self) -> None:
        """
        Preload the model and warm it up with a simple query to ensure it's ready.
        This eliminates cold start delays.
        """
        if not self.llm:
            await self.initialize_llm()
            
        print("🔥 Preloading and warming up the model...")
        start_time = time.time()
        
        try:
            # Create a simple warm-up query
            warmup_query = "Hello, are you ready?"
            
            # Use the LLM to warm up
            response = ""
            async for chunk in self.llm.astream(warmup_query):
                response += chunk
            
            elapsed = time.time() - start_time
            print(f"✅ Model warmed up successfully in {elapsed:.2f}s")
            print(f"🔥 Model is now ready and will stay loaded (keep_alive={self.settings.ollama_keep_alive})")
            
            # Verify model is loaded
            result = subprocess.run(["ollama", "ps"], capture_output=True, text=True)
            if result.returncode == 0 and self.settings.ollama_llm_model in result.stdout:
                print(f"✅ Confirmed: {self.settings.ollama_llm_model} is loaded in memory")
            else:
                print(f"⚠️ Warning: {self.settings.ollama_llm_model} not found in loaded models")
                print("   This may cause cold start delays on first request")
            
        except Exception as e:
            print(f"⚠️ Warning: Could not warm up model: {e}")
            
    def initialize_qa_chain(self, vectorstore=None):
        """Initialize QA chain with custom prompt."""
        if not self.llm:
            raise RuntimeError("LLM must be initialized before creating QA chain")
            
        if vectorstore:
            # Create the prompt template
            qa_prompt = PromptTemplate(
                template=self.custom_prompt,
                input_variables=["context", "question"]
            )
            
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=vectorstore.as_retriever(search_kwargs={"k": 2}),
                return_source_documents=True,
                chain_type_kwargs={"prompt": qa_prompt}
            )
        else:
            # If no vectorstore, create a simple chain with optimized prompt
            self.qa_chain = LLMChain(
                llm=self.llm,
                prompt=PromptTemplate(
                    template=self.general_prompt,
                    input_variables=["query"]
                )
            )
            
        print("--- QA Chain is ready! ---")
        return self.qa_chain
        
    def get_llm(self) -> Optional[Ollama]:
        """Get the current LLM instance."""
        return self.llm
        
    def get_qa_chain(self):
        """Get the current QA chain."""
        return self.qa_chain 