#!/usr/bin/env python3
import argparse
import requests
import json
import sys
from typing import Optional
import readline  # For command history and line editing

def stream_question(query: str, url: str = "http://localhost:8000/ask") -> Optional[requests.Response]:
    """Stream a question to the AI assistant API."""
    try:
        response = requests.post(url, json={"query": query}, stream=True)
        response.raise_for_status()
        return response
    except Exception as e:
        print(f"Error: Could not connect to the API: {e}")
        return None

def print_streaming_response(response: requests.Response) -> None:
    """Print the streaming response as it comes in."""
    if not response:
        return

    sources = []
    used_documentation = False
    first_chunk = True
    
    try:
        # Read the stream line by line
        for line in response.iter_lines():
            if not line:
                continue
                
            # Remove "data: " prefix from SSE format
            line = line.decode('utf-8')
            if not line.startswith("data: "):
                continue
            data = json.loads(line[6:])  # Skip "data: " prefix
            
            if data["event"] == "chunk":
                if first_chunk:
                    print("\n🤖 Answer:")
                    print("=" * 80)
                    first_chunk = False
                
                # Print the chunk without a newline to create a streaming effect
                sys.stdout.write(data["data"]["text"])
                sys.stdout.flush()
            
            elif data["event"] == "done":
                # Store the sources and documentation status
                sources = data["data"].get("sources", [])
                used_documentation = data["data"].get("used_documentation", False)
                
                # Print source information if available
                if sources:
                    print("\n\n📑 Reference Documentation:")
                    print("=" * 80)
                    for source in sources:
                        print(f"\nFrom: {source['source']}")
                        print(f"Preview: {source['content_preview']}")
                
                # Print knowledge source information
                print("\n💡 Knowledge Source:")
                print("=" * 80)
                if used_documentation:
                    print("📚 Response based on documentation and general knowledge")
                else:
                    print("🧠 Response based on general network engineering knowledge")
            
            elif data["event"] == "error":
                print(f"\n❌ Error: {data['data']['error']}")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Streaming interrupted by user")
        response.close()
    except Exception as e:
        print(f"\n❌ Error during streaming: {e}")
        response.close()

def interactive_mode(url: str):
    """Run an interactive shell for querying the AI assistant."""
    print("\n🤖 Network Engineer AI Assistant Interactive Shell")
    print("=" * 80)
    print("Type your questions and press Enter. Use 'exit', 'quit', or 'q' to end the session.")
    print("Use Ctrl+C to interrupt the current response.")
    print("\nYou can ask about:")
    print("- Network documentation in your knowledge base")
    print("- General networking concepts and troubleshooting")
    print("- Network logs and configuration analysis")
    print("- Best practices and recommendations")
    print("=" * 80)

    while True:
        try:
            # Get input with a nice prompt
            query = input("\n💭 > ").strip()
            
            # Check for exit commands
            if query.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye! 👋")
                break
            
            # Skip empty queries
            if not query:
                continue
            
            response = stream_question(query, url)
            print_streaming_response(response)
            
        except KeyboardInterrupt:
            print("\nQuery interrupted. Ready for a new question!")
            continue
        except EOFError:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\nError: {e}")

def main():
    parser = argparse.ArgumentParser(description="CLI tool for the Network Engineer AI Assistant")
    parser.add_argument("--url", default="http://localhost:8000/ask", 
                      help="API endpoint URL (default: http://localhost:8000/ask)")
    parser.add_argument("query", nargs="*", help="Your question for the AI assistant (if not provided, enters interactive mode)")
    
    args = parser.parse_args()
    
    if not args.query:
        # No query provided, enter interactive mode
        interactive_mode(args.url)
    else:
        # Single query mode
        query = " ".join(args.query)
        print(f"\n💭 Asking: {query}\n")
        response = stream_question(query, args.url)
        print_streaming_response(response)

if __name__ == "__main__":
    main() 