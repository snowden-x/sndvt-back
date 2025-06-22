#!/usr/bin/env python3
"""
Ollama Model Manager - Utility for managing and testing Ollama models
"""
import subprocess
import json
import time
import requests
import argparse
from typing import List, Dict, Any

def run_command(cmd: List[str]) -> tuple[bool, str]:
    """Run a shell command and return success status and output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()

def check_ollama_running() -> bool:
    """Check if Ollama service is running."""
    success, _ = run_command(["ollama", "list"])
    return success

def list_models() -> List[Dict[str, Any]]:
    """List all available Ollama models."""
    if not check_ollama_running():
        print("❌ Ollama is not running. Please start it first.")
        return []
    
    success, output = run_command(["ollama", "list"])
    if not success:
        print(f"❌ Failed to list models: {output}")
        return []
    
    # Parse the output (skip header line)
    lines = output.split('\n')[1:]  # Skip header
    models = []
    
    for line in lines:
        if line.strip():
            parts = line.split()
            if len(parts) >= 3:
                models.append({
                    'name': parts[0],
                    'id': parts[1],
                    'size': parts[2],
                    'modified': ' '.join(parts[3:]) if len(parts) > 3 else ''
                })
    
    return models

def pull_model(model_name: str) -> bool:
    """Pull/download a model."""
    print(f"📥 Pulling model: {model_name}")
    success, output = run_command(["ollama", "pull", model_name])
    
    if success:
        print(f"✅ Successfully pulled {model_name}")
        return True
    else:
        print(f"❌ Failed to pull {model_name}: {output}")
        return False

def test_model_speed(model_name: str, test_query: str = "What is networking?") -> Dict[str, float]:
    """Test model response speed."""
    print(f"🧪 Testing model speed: {model_name}")
    
    # Prepare the test
    cmd = ["ollama", "run", model_name, test_query]
    
    # Time the response
    start_time = time.time()
    success, output = run_command(cmd)
    end_time = time.time()
    
    if success:
        response_time = end_time - start_time
        chars_per_sec = len(output) / response_time if response_time > 0 else 0
        
        print(f"✅ Response time: {response_time:.2f}s")
        print(f"📊 Speed: {chars_per_sec:.1f} chars/sec")
        print(f"📏 Response length: {len(output)} characters")
        
        return {
            'response_time': response_time,
            'chars_per_sec': chars_per_sec,
            'response_length': len(output)
        }
    else:
        print(f"❌ Test failed: {output}")
        return {}

def show_model_info(model_name: str):
    """Show detailed information about a model."""
    success, output = run_command(["ollama", "show", model_name])
    
    if success:
        print(f"📋 Model Info: {model_name}")
        print("=" * 60)
        print(output)
    else:
        print(f"❌ Failed to get model info: {output}")

def preload_model(model_name: str):
    """Preload a model into memory."""
    print(f"🔥 Preloading model: {model_name}")
    
    # Use a simple query to load the model
    cmd = ["ollama", "run", model_name, "Hello"]
    success, output = run_command(cmd)
    
    if success:
        print(f"✅ Model {model_name} preloaded successfully")
    else:
        print(f"❌ Failed to preload model: {output}")

def check_running_models():
    """Check which models are currently loaded in memory."""
    success, output = run_command(["ollama", "ps"])
    
    if success:
        print("🔄 Currently Running Models:")
        print("=" * 60)
        print(output)
    else:
        print(f"❌ Failed to check running models: {output}")

def benchmark_models(models: List[str], test_query: str = "Explain VLAN configuration"):
    """Benchmark multiple models."""
    print(f"🏁 Benchmarking {len(models)} models...")
    print("=" * 80)
    
    results = {}
    
    for model in models:
        print(f"\n🧪 Testing {model}...")
        result = test_model_speed(model, test_query)
        if result:
            results[model] = result
    
    # Show comparison
    if results:
        print("\n📊 Benchmark Results:")
        print("=" * 80)
        print(f"{'Model':<20} {'Time (s)':<10} {'Speed (c/s)':<12} {'Length':<8}")
        print("-" * 60)
        
        for model, data in sorted(results.items(), key=lambda x: x[1]['response_time']):
            print(f"{model:<20} {data['response_time']:<10.2f} {data['chars_per_sec']:<12.1f} {data['response_length']:<8}")

def main():
    parser = argparse.ArgumentParser(description="Ollama Model Manager")
    parser.add_argument("--list", action="store_true", help="List all models")
    parser.add_argument("--pull", help="Pull/download a model")
    parser.add_argument("--test", help="Test model speed")
    parser.add_argument("--info", help="Show model information")
    parser.add_argument("--preload", help="Preload model into memory")
    parser.add_argument("--running", action="store_true", help="Show running models")
    parser.add_argument("--benchmark", nargs="+", help="Benchmark multiple models")
    parser.add_argument("--query", default="What is networking?", help="Test query for speed tests")
    
    args = parser.parse_args()
    
    if not check_ollama_running():
        print("❌ Ollama is not running. Please start it first with: ollama serve")
        return
    
    if args.list:
        models = list_models()
        if models:
            print("📋 Available Models:")
            print("=" * 80)
            print(f"{'Name':<25} {'ID':<15} {'Size':<10} {'Modified'}")
            print("-" * 80)
            for model in models:
                print(f"{model['name']:<25} {model['id']:<15} {model['size']:<10} {model['modified']}")
        else:
            print("No models found.")
    
    elif args.pull:
        pull_model(args.pull)
    
    elif args.test:
        test_model_speed(args.test, args.query)
    
    elif args.info:
        show_model_info(args.info)
    
    elif args.preload:
        preload_model(args.preload)
    
    elif args.running:
        check_running_models()
    
    elif args.benchmark:
        benchmark_models(args.benchmark, args.query)
    
    else:
        print("Use --help to see available commands")

if __name__ == "__main__":
    main() 