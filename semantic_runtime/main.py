from dataclasses import dataclass
import os
import argparse
from semantic_runtime.main_runner import KernelScopeRunner # assuming previous core runner class structure
from semantic_runtime.drivers.mock_driver import MockDriver
from semantic_runtime.drivers.linux_driver import LinuxDriver



def main():
    parser = argparse.ArgumentParser(description="KernelScope 2.0 Compiler CLI Front-End Interface")
    parser.add_argument(
        '--driver', 
        choices=['mock', 'linux'], 
        default='mock',
        help="Select data ingestion driver source path (default: mock)"
    )
    parser.add_argument(
        '--chunks',
        default='chunks.jsonl',
        help="Target location path for production linux chunks line stream (only used with --driver linux)"
    )
    
    args = parser.parse_args()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cache_path = os.path.join(current_dir, "semantic_context_cache")
    
    # Initialize the core architecture runner
    runner = KernelScopeRunner(cache_dir=cache_path, verbosity=1)
    
    # Routing Driver Selection Strategy
    cleanup_func = lambda: None
    try:
        if args.driver == 'mock':
            chunks_path, symbol_db, cleanup_func = MockDriver.get_chunks_and_db()
        else:
            chunks_path, symbol_db, cleanup_func = LinuxDriver.get_chunks_and_db(args.chunks)
            
        runner.run_pipeline(chunks_path, symbol_db)
        runner.interactive_shell()
        
    except Exception as e:
        print(f"\n[Fatal Ingestion Error] Command Execution Halted: {str(e)}")
    finally:
        cleanup_func()

if __name__ == "__main__":
    main()