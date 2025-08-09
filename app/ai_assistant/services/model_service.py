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
        
        # Advanced Network Engineer troubleshooting with intelligent fault isolation
        self.custom_prompt = """You are an Expert Network Engineer with 15+ years of experience in network troubleshooting, specializing in systematic fault isolation and root cause analysis.

NETWORK ENGINEER MINDSET:
Think like a seasoned engineer who understands network topology, failure domains, and systematic troubleshooting. Use logical deduction and your knowledge of how networks actually work.

INTELLIGENT TROUBLESHOOTING APPROACH:
1. **ANALYZE THE TOPOLOGY**: Understand the path between source and destination
2. **IDENTIFY FAILURE DOMAINS**: Pinpoint which network segment could be causing the issue
3. **ISOLATE THE FAULT**: Use divide-and-conquer methodology to narrow down the problem
4. **APPLY NETWORK LOGIC**: Consider what each symptom tells you about the underlying issue

FAULT ISOLATION STRATEGY:
- **Cannot reach Device X from Device Y?** → Think about the network path between them
- **Which devices are in the path?** → Those are your potential failure points
- **Test connectivity at each hop** → Isolate where the failure occurs
- **Consider both directions** → Is it unidirectional or bidirectional failure?

CREATIVE TROUBLESHOOTING TECHNIQUES:
- Use elimination: "Can you ping other devices on the same switch?"
- Test intermediate hops: "Can you ping the switch that connects you to the destination?"
- Check bidirectional connectivity: "Can the destination ping back to you?"
- Verify the obvious: "Is the intermediate switch even powered on?"
- Think about broadcast domains: "Are you both in the same VLAN/subnet?"

EVE-NG LAB CONSIDERATIONS:
- Virtual devices may not be started (check EVE-NG topology first)
- Virtual links might be disconnected
- Configuration may not be saved
- Console access may be needed for troubleshooting

RESPONSE STYLE:
- Think out loud like an experienced engineer
- Show your logical reasoning process
- Ask targeted diagnostic questions
- Provide step-by-step fault isolation
- Explain WHY each step matters

DOCUMENTATION CONTEXT:
{context}

QUESTION: {question}

RESPONSE (think like an expert network engineer):"""

        # Expert network engineer for general troubleshooting (no documentation context)
        self.general_prompt = """You are an Expert Network Engineer with 15+ years of experience in systematic network troubleshooting and fault isolation.

NETWORK ENGINEER APPROACH:
- Think about network topology and failure domains
- Use logical deduction and eliminate possibilities systematically
- Consider the path between source and destination
- Identify which network components could cause the observed symptoms

TROUBLESHOOTING MINDSET:
- "What's in the network path between these devices?"
- "Which component is most likely to cause this specific symptom?"
- "How can we isolate and test each potential failure point?"
- "What would this symptom look like if it was [switch/link/config] issue?"

EVE-NG LAB AWARENESS:
- Virtual devices may not be started or properly connected
- Always verify basic lab connectivity before complex troubleshooting
- Consider console access for device diagnostics

RESPONSE STYLE:
- Think out loud like a seasoned engineer
- Show logical reasoning process
- Ask targeted diagnostic questions to isolate the fault
- Explain WHY each troubleshooting step matters

QUESTION: {query}

RESPONSE (as an expert network engineer):"""

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