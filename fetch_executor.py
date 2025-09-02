#!/usr/bin/env python3
"""
Fetch Executor Program

Reads YAML configuration, copies source code to working directory,
executes Python programs with optional sudo privileges, and collects result files.
"""

import argparse
import os
import shutil
import subprocess
import sys
import glob
import yaml
from pathlib import Path


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Execute Python programs from remote source with configurable privileges"
    )
    parser.add_argument(
        "config_file",
        help="Path to YAML configuration file"
    )
    return parser.parse_args()


def load_yaml_config(config_file):
    """Load and parse YAML configuration file."""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file}' not found")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        sys.exit(1)


def validate_config(config):
    """Validate required configuration fields."""
    required_fields = ['source_root', 'programs']
    for field in required_fields:
        if field not in config:
            print(f"Error: Required field '{field}' missing from configuration")
            sys.exit(1)
    
    if not os.path.exists(config['source_root']):
        print(f"Error: Source root directory '{config['source_root']}' does not exist")
        sys.exit(1)
    
    # Set default execution mode if not specified
    if 'execution_mode' not in config:
        config['execution_mode'] = 'normal'
        
    if config['execution_mode'] not in ['normal', 'sudo']:
        print(f"Error: execution_mode must be 'normal' or 'sudo', got '{config['execution_mode']}'")
        sys.exit(1)


def copy_source_folders(source_root, programs):
    """Copy specified subfolders from source to current directory."""
    current_dir = os.getcwd()
    
    for subfolder in programs.keys():
        source_path = os.path.join(source_root, subfolder)
        dest_path = os.path.join(current_dir, subfolder)
        
        if not os.path.exists(source_path):
            print(f"Warning: Source folder '{source_path}' does not exist, skipping...")
            continue
            
        # Remove destination if it already exists
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
        
        try:
            shutil.copytree(source_path, dest_path)
            print(f"Copied '{source_path}' -> '{dest_path}'")
        except Exception as e:
            print(f"Error copying '{source_path}' to '{dest_path}': {e}")
            sys.exit(1)


def execute_program(program_spec, execution_mode):
    """Execute a Python program with specified mode and arguments."""
    # Parse program specification
    parts = program_spec.split()
    program_name = parts[0]
    config_args = parts[1:] if len(parts) > 1 else []
    
    # Build command
    if execution_mode == 'sudo':
        cmd = ['sudo', 'python', f'./{program_name}'] + config_args
    else:
        cmd = ['python', f'./{program_name}'] + config_args
    
    print(f"Executing: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
            
        if result.returncode != 0:
            print(f"Warning: Program '{program_name}' exited with code {result.returncode}")
        else:
            print(f"Program '{program_name}' completed successfully")
            
    except subprocess.TimeoutExpired:
        print(f"Error: Program '{program_name}' timed out after 300 seconds")
    except FileNotFoundError:
        print(f"Error: Program '{program_name}' not found")
    except Exception as e:
        print(f"Error executing '{program_name}': {e}")


def collect_result_files(subfolder_name):
    """Collect files with 'result-' prefix and copy to ./output-{subfolder_name} directory."""
    current_dir = os.getcwd()
    output_dir = os.path.join(current_dir, 'output-' + subfolder_name)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all files with 'result-' prefix in current directory and subdirectories
    result_files = []
    for root, dirs, files in os.walk(current_dir):
        # Skip any output directories to avoid copying files we've already moved
        dirs_to_remove = [d for d in dirs if d.startswith('output-')]
        for d in dirs_to_remove:
            dirs.remove(d)
            
        for file in files:
            if file.startswith('result-'):
                result_files.append(os.path.join(root, file))
    
    if not result_files:
        print("No result files found (files starting with 'result-')")
        return
    
    print(f"Found {len(result_files)} result file(s):")
    for result_file in result_files:
        try:
            filename = os.path.basename(result_file)
            dest_path = os.path.join(output_dir, filename)
            shutil.copy2(result_file, dest_path)
            print(f"  Copied '{result_file}' -> '{dest_path}'")
        except Exception as e:
            print(f"  Error copying '{result_file}': {e}")


def main():
    """Main program entry point."""
    print("Fetch Executor Starting...")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Load and validate configuration
    config = load_yaml_config(args.config_file)
    validate_config(config)
    
    print(f"Source root: {config['source_root']}")
    print(f"Execution mode: {config['execution_mode']}")
    print(f"Programs to execute: {len(config['programs'])}")
    
    # Copy source folders to current directory
    print("\n--- Copying Source Folders ---")
    copy_source_folders(config['source_root'], config['programs'])
    
    # Execute programs
    print("\n--- Executing Programs ---")
    for subfolder, program_spec in config['programs'].items():
        print(f"\nExecuting program in '{subfolder}': {program_spec}")
        
        # Change to subfolder directory
        subfolder_path = os.path.join(os.getcwd(), subfolder)
        if not os.path.exists(subfolder_path):
            print(f"Warning: Subfolder '{subfolder_path}' not found, skipping...")
            continue
            
        original_cwd = os.getcwd()
        try:
            os.chdir(subfolder_path)
            execute_program(program_spec, config['execution_mode'])
        finally:
            os.chdir(original_cwd)
    
    # Collect result files for each subfolder
    print("\n--- Collecting Result Files ---")
    for subfolder in config['programs'].keys():
        print(f"Collecting results from {subfolder} to ./output-{subfolder}/")
        collect_result_files(subfolder)
    
    print("\nFetch Executor Completed!")


if __name__ == "__main__":
    main()