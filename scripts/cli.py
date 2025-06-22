#!/usr/bin/env python3
import argparse
import requests
import json
import sys
import time
from typing import Optional
import readline  # For command history and line editing

def stream_question(query: str, url: str = "http://localhost:8000/ask") -> Optional[requests.Response]:
    """Stream a question to the AI assistant API."""
    try:
        print(f"🚀 Sending query to: {url}")
        start_time = time.time()
        response = requests.post(url, json={"query": query}, stream=True)
        response.raise_for_status()
        print(f"⚡ Connection established in {time.time() - start_time:.2f}s")
        return response
    except Exception as e:
        print(f"❌ Error: Could not connect to the API: {e}")
        return None

def print_streaming_response(response: requests.Response) -> None:
    """Print the streaming response as it comes in."""
    if not response:
        return

    sources = []
    used_documentation = False
    first_chunk = True
    total_response = ""
    start_time = time.time()
    first_token_time = None
    
    try:
        print("\n🤖 AI Assistant Response:")
        print("=" * 80)
        
        # Read the stream line by line
        for line in response.iter_lines():
            if not line:
                continue
                
            # Remove "data: " prefix from SSE format
            line = line.decode('utf-8')
            if not line.startswith("data: "):
                continue
            
            try:
                data = json.loads(line[6:])  # Skip "data: " prefix
            except json.JSONDecodeError:
                continue
            
            if data.get("type") == "chunk":
                if first_chunk:
                    first_token_time = time.time()
                    print("📝 Streaming response:\n")
                    first_chunk = False
                
                # Print the chunk without a newline to create a streaming effect
                chunk_content = data.get("content", "")
                sys.stdout.write(chunk_content)
                sys.stdout.flush()
                total_response += chunk_content
            
            elif data.get("type") == "complete":
                # Store the sources and documentation status
                sources = data.get("sources", [])
                used_documentation = data.get("used_documentation", False)
                
                # Print timing information
                total_time = time.time() - start_time
                if first_token_time:
                    time_to_first_token = first_token_time - start_time
                    print(f"\n\n⏱️ Performance Metrics:")
                    print("=" * 80)
                    print(f"Time to first token: {time_to_first_token:.2f}s")
                    print(f"Total response time: {total_time:.2f}s")
                    print(f"Response length: {len(total_response)} characters")
                    if total_time > 0:
                        print(f"Average speed: {len(total_response)/total_time:.1f} chars/sec")
                
                # Print source information if available
                if sources:
                    print(f"\n📑 Reference Documentation:")
                    print("=" * 80)
                    for i, source in enumerate(sources, 1):
                        print(f"{i}. {source}")
                
                # Print knowledge source information
                print(f"\n💡 Knowledge Source:")
                print("=" * 80)
                if used_documentation:
                    print("📚 Response based on documentation and general knowledge")
                else:
                    print("🧠 Response based on general network engineering knowledge")
            
            elif data.get("type") == "error":
                print(f"\n❌ Error: {data.get('error', 'Unknown error')}")
                break
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Streaming interrupted by user")
        response.close()
    except Exception as e:
        print(f"\n❌ Error during streaming: {e}")
        response.close()

def test_connection(url: str) -> bool:
    """Test if the API server is running."""
    try:
        # Extract base URL
        base_url = url.replace("/ask", "")
        response = requests.get(f"{base_url}/docs", timeout=5)
        return response.status_code == 200
    except:
        return False

def interactive_mode(url: str):
    """Run an interactive shell for querying the AI assistant."""
    print("\n🤖 Network Engineer AI Assistant Interactive Shell")
    print("=" * 80)
    
    # Test connection first
    if not test_connection(url):
        print("⚠️ Warning: Cannot connect to API server. Make sure it's running at the configured URL.")
        print(f"   URL: {url}")
        print("   Try running: python main.py")
        print()
    
    print("Type your questions and press Enter. Use 'exit', 'quit', or 'q' to end the session.")
    print("Use Ctrl+C to interrupt the current response.")
    print("\nYou can ask about:")
    print("- Network documentation in your knowledge base")
    print("- General networking concepts and troubleshooting")
    print("- Network logs and configuration analysis")
    print("- Best practices and recommendations")
    print("=" * 80)

    query_count = 0
    while True:
        try:
            # Get input with a nice prompt
            query = input(f"\n💭 Query #{query_count + 1} > ").strip()
            
            # Check for exit commands
            if query.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye! 👋")
                break
            
            # Skip empty queries
            if not query:
                continue
            
            query_count += 1
            print(f"\n🔍 Processing query #{query_count}...")
            response = stream_question(query, url)
            print_streaming_response(response)
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Query interrupted. Ready for a new question!")
            continue
        except EOFError:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="CLI tool for the Network Engineer AI Assistant")
    parser.add_argument("--url", default="http://localhost:8000/ask", 
                      help="API endpoint URL (default: http://localhost:8000/ask)")
    parser.add_argument("--test", action="store_true", 
                      help="Test connection to the API server")
    parser.add_argument("query", nargs="*", help="Your question for the AI assistant (if not provided, enters interactive mode)")
    
    args = parser.parse_args()
    
    if args.test:
        print("🔍 Testing connection to API server...")
        if test_connection(args.url):
            print("✅ API server is running and accessible!")
        else:
            print("❌ Cannot connect to API server. Make sure it's running.")
        return
    
    if not args.query:
        # No query provided, enter interactive mode
        interactive_mode(args.url)
    else:
        # Single query mode
        query = " ".join(args.query)
        print(f"\n💭 Asking: {query}")
        response = stream_question(query, args.url)
        print_streaming_response(response)

if __name__ == "__main__":
    main() 