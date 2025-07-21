// =============================================================================
// SNDVT: Chat Assistant
// Complete Data Flow: User Input → AI Response
// =============================================================================

// -----------------------------------------------------------------------------
// 1. SYSTEM INITIALIZATION
// -----------------------------------------------------------------------------
FUNCTION initializeSystem():
    // Backend Startup
    startOllamaService()  // Local LLM server on port 11434
    loadAIModels("gemma3", "nomic-embed-text")
    
    // Process network documentation
    documents = loadFiles("data/network_docs/")
    chunks = splitIntoChunks(documents, chunkSize=1000)
    vectorDatabase = ChromaDB.create("data/chroma_db")
    vectorDatabase.store(chunks)
    
    // Start FastAPI server on port 8000
    startWebServer()
    
    // Frontend Startup
    startReactApp()  // Port 5173
    establishWebSocketConnection("ws://localhost:8000/api/ws")
END FUNCTION

// -----------------------------------------------------------------------------
// 2. USER INPUT PROCESSING
// -----------------------------------------------------------------------------
FUNCTION handleUserInput(userMessage):
    // Frontend: User types message and hits send
    messageObject = {
        id: generateUniqueId(),
        text: userMessage,
        sender: "user",
        timestamp: now()
    }
    
    // Add to chat history
    chatHistory.append(messageObject)
    updateUI(chatHistory)
    
    // Prepare payload with conversation context
    payload = {
        query: userMessage,
        conversation_history: chatHistory
    }
    
    // Send via WebSocket to backend
    websocket.send(JSON.stringify(payload))
    showTypingIndicator()
END FUNCTION

// -----------------------------------------------------------------------------
// 3. BACKEND MESSAGE PROCESSING
// -----------------------------------------------------------------------------
FUNCTION processIncomingMessage(websocketData):
    // Parse incoming data
    query = websocketData.query
    history = websocketData.conversation_history
    
    // Send start signal to frontend
    websocket.send(JSON.stringify({type: "start"}))
    
    // Search knowledge base for relevant context
    relevantDocs = vectorDatabase.similaritySearch(query, limit=3)
    context = combineDocuments(relevantDocs)
    
    // Build prompt for AI
    prompt = buildPrompt(query, history, context)
    
    // Stream response from AI model
    FOR EACH token IN ollamaLLM.streamResponse(prompt):
        chunk = {
            type: "chunk",
            content: token.text,
            metadata: token.metadata
        }
        websocket.send(JSON.stringify(chunk))
    END FOR
    
    // Send completion signal
    websocket.send(JSON.stringify({type: "end"}))
END FUNCTION

// -----------------------------------------------------------------------------
// 4. AI MODEL PROCESSING
// -----------------------------------------------------------------------------
FUNCTION buildPrompt(query, history, context):
    systemPrompt = """
    You are a network engineering AI assistant.
    Use documentation context when available.
    Maintain conversation continuity.
    """
    
    contextSection = IF context.exists() THEN
        "Documentation: " + context
    ELSE
        "Using general knowledge"
    
    conversationSection = ""
    FOR EACH message IN history:
        role = IF message.sender == "user" THEN "Human" ELSE "Assistant"
        conversationSection += role + ": " + message.text + "\n"
    END FOR
    
    finalPrompt = systemPrompt + "\n" + contextSection + "\n" + 
                  conversationSection + "\nHuman: " + query + "\nAssistant:"
    
    RETURN finalPrompt
END FUNCTION

FUNCTION ollamaLLM.streamResponse(prompt):
    // Configure AI model
    modelConfig = {
        model: "gemma3:4b",
        temperature: 0.3,
        max_tokens: 512,
        stream: true
    }
    
    // Send to Ollama API
    response = httpPost("http://localhost:11434/api/generate", {
        model: modelConfig.model,
        prompt: prompt,
        stream: true,
        options: modelConfig
    })
    
    // Stream tokens back
    FOR EACH chunk IN response.stream():
        IF chunk.contains("response"):
            YIELD {
                text: chunk.response,
                metadata: {
                    model: "gemma3:4b",
                    source: determineSource(prompt)
                }
            }
        END IF
    END FOR
END FUNCTION

// -----------------------------------------------------------------------------
// 5. KNOWLEDGE BASE INTEGRATION
// -----------------------------------------------------------------------------
FUNCTION vectorDatabase.similaritySearch(query, limit):
    // Convert query to vector embedding
    queryVector = ollamaEmbeddings.embed(query, model="nomic-embed-text")
    
    // Search ChromaDB for similar documents
    results = chromaDB.query(
        query_embeddings=[queryVector],
        n_results=limit,
        include=["documents", "metadatas", "distances"]
    )
    
    // Filter by relevance score
    relevantDocs = []
    FOR EACH result IN results:
        IF result.distance < 0.7:  // Similarity threshold
            relevantDocs.append({
                content: result.document,
                source: result.metadata.source,
                score: result.distance
            })
        END IF
    END FOR
    
    RETURN relevantDocs
END FUNCTION

// -----------------------------------------------------------------------------
// 6. FRONTEND RESPONSE HANDLING
// -----------------------------------------------------------------------------
FUNCTION handleStreamingResponse(websocketMessage):
    data = JSON.parse(websocketMessage)
    
    SWITCH data.type:
        CASE "start":
            // Create new AI message bubble
            aiMessage = {
                id: "ai-" + timestamp(),
                text: "",
                sender: "ai"
            }
            chatHistory.append(aiMessage)
            currentAiMessageId = aiMessage.id
            updateUI(chatHistory)
        
        CASE "chunk":
            // Append text to existing AI message
            FOR EACH message IN chatHistory:
                IF message.id == currentAiMessageId:
                    message.text += data.content
                    updateUI(chatHistory)  // Real-time update
                    break
                END IF
            END FOR
        
        CASE "end":
            // Finalize response
            hideTypingIndicator()
            currentAiMessageId = null
            finalUpdateUI(chatHistory)
        
        CASE "error":
            showError(data.error)
            hideTypingIndicator()
    END SWITCH
END FUNCTION

// -----------------------------------------------------------------------------
// 7. UI UPDATE FUNCTIONS
// -----------------------------------------------------------------------------
FUNCTION updateUI(messages):
    // Clear chat container
    chatContainer.clear()
    
    // Render each message
    FOR EACH message IN messages:
        messageElement = createMessageBubble(message)
        chatContainer.append(messageElement)
    END FOR
    
    // Auto-scroll to bottom
    chatContainer.scrollToBottom()
    
    // Update message counter
    messageCounter.text = messages.length + " messages"
END FUNCTION

FUNCTION createMessageBubble(message):
    bubble = createElement("div")
    
    IF message.sender == "user":
        bubble.className = "user-message"
        bubble.style = "background: blue, align: right"
        avatar = createAvatar("U")
    ELSE:
        bubble.className = "ai-message"
        bubble.style = "background: gray, align: left"
        avatar = createAvatar("N")  // Nexus
    END IF
    
    // Format text (markdown-like)
    formattedText = formatText(message.text)
    bubble.innerHTML = avatar + formattedText
    
    RETURN bubble
END FUNCTION

// -----------------------------------------------------------------------------
// 8. WEBSOCKET CONNECTION MANAGEMENT
// -----------------------------------------------------------------------------
FUNCTION establishWebSocketConnection(url):
    websocket = new WebSocket(url)
    
    websocket.onopen = FUNCTION():
        connectionStatus.text = "Connected"
        connectionIndicator.color = "green"
        showToast("Connected to AI Assistant")
    END FUNCTION
    
    websocket.onmessage = FUNCTION(event):
        handleStreamingResponse(event.data)
    END FUNCTION
    
    websocket.onclose = FUNCTION():
        connectionStatus.text = "Disconnected"
        connectionIndicator.color = "red"
        showToast("Disconnected from AI Assistant")
        // Attempt reconnection
        setTimeout(establishWebSocketConnection, 3000)
    END FUNCTION
    
    websocket.onerror = FUNCTION(error):
        showError("WebSocket error: " + error.message)
    END FUNCTION
END FUNCTION

// -----------------------------------------------------------------------------
// 9. MAIN EXECUTION FLOW
// -----------------------------------------------------------------------------
FUNCTION main():
    // 1. Initialize system
    initializeSystem()
    
    // 2. Set up event listeners
    chatInput.addEventListener("submit", handleUserInput)
    
    // 3. Main application loop
    WHILE application.isRunning():
        // Handle user interactions
        IF userTypesMessage():
            handleUserInput(userInput.value)
        END IF
        
        // Process incoming WebSocket messages
        IF websocket.hasMessage():
            handleStreamingResponse(websocket.getMessage())
        END IF
        
        // Update UI
        updateUI(chatHistory)
        
        // Small delay to prevent blocking
        sleep(16)  // ~60 FPS
    END WHILE
END FUNCTION

// -----------------------------------------------------------------------------
// 10. SYSTEM CONFIGURATION
// -----------------------------------------------------------------------------
CONSTANTS:
    OLLAMA_URL = "http://localhost:11434"
    BACKEND_URL = "http://localhost:8000"
    FRONTEND_URL = "http://localhost:5173"
    WEBSOCKET_URL = "ws://localhost:8000/api/ws"
    
    AI_MODEL = "gemma3:4b
    EMBEDDING_MODEL = "nomic-embed-text"
    
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    SIMILARITY_THRESHOLD = 0.7
    MAX_TOKENS = 512
    TEMPERATURE = 0.3

// Start the application
main()

flowchart TD
    A["👤 User Types Message"] --> B["📱 Frontend React App<br/>(Port 5173)"]
    B --> C["🔌 WebSocket Connection<br/>ws://localhost:8000/api/ws"]
    C --> D["🚀 FastAPI Backend<br/>(Port 8000)"]
    
    D --> E["📝 Parse Message & History"]
    E --> F["🔍 Search Knowledge Base<br/>ChromaDB Vector Store"]
    F --> G["📚 Retrieve Relevant Docs<br/>Network Documentation"]
    
    G --> H["🤖 Build AI Prompt<br/>Query + Context + History"]
    H --> I["🧠 Ollama LLM<br/>gemma3:4b Model<br/>(Port 11434)"]
    
    I --> J["📡 Stream Response Tokens"]
    J --> K["🔄 Process Each Token Chunk"]
    K --> L["📤 Send via WebSocket<br/>JSON: {type: 'chunk', content: '...'}"]
    
    L --> M["📱 Frontend Receives Stream"]
    M --> N["💬 Update Chat UI<br/>Real-time Message Building"]
    N --> O["👁️ User Sees Response"]
    
    %% Parallel processes
    P["📊 Monitoring Stack<br/>Prometheus + Grafana<br/>(Ports 9090, 3000)"] 
    Q["🌐 SNMP Exporter<br/>(Port 9116)"]
    R["🖥️ Network Devices<br/>Routers, Switches, etc."]
    
    R --> Q
    Q --> P
    P --> S["📈 Device Metrics Dashboard"]
    
    %% Data stores
    T["🗄️ ChromaDB<br/>Vector Embeddings<br/>data/chroma_db/"]
    U["📁 Network Docs<br/>data/network_docs/"]
    V["⚙️ Device Configs<br/>config/device_configs/"]
    
    U --> T
    T --> F
    V --> R
    
    %% Styling
    classDef userClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef frontendClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef backendClass fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef aiClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef dataClass fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef monitorClass fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    
    class A userClass
    class B,C,M,N,O frontendClass
    class D,E,L backendClass
    class F,G,H,I,J,K aiClass
    class T,U,V dataClass
    class P,Q,R,S monitorClass