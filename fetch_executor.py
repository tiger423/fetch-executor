#!/usr/bin/env python3
"""
Fetch Executor Program v2

Reads YAML configuration, processes each program entry sequentially with
table-based execution: copy -> execute -> collect -> cleanup for each row.
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
        description="Execute Python programs from remote source with table-based sequential processing"
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


def create_execution_table(config):
    """Create internal execution table from YAML config."""
    table = []
    source_root = config['source_root']
    
    print(f"Creating execution table from source_root: {source_root}")
    for subfolder, command in config['programs'].items():
        table.append([source_root, subfolder, command])
        print(f"  Row: ['{source_root}', '{subfolder}', '{command}']")
    
    return table


def parse_command(command_string):
    """Parse command to extract sudo flag, script name, and config file."""
    parts = command_string.split()
    
    if len(parts) == 0:
        raise ValueError("Empty command string")
    
    has_sudo = parts[0] == 'sudo'
    start_index = 1 if has_sudo else 0
    
    if len(parts) <= start_index:
        raise ValueError("No script name found in command")
    
    script_name = parts[start_index]
    config_args = parts[start_index + 1:] if len(parts) > start_index + 1 else []
    
    return has_sudo, script_name, config_args


def copy_source_to_subfolder(source_root, subfolder):
    """Copy source folder to current directory subfolder."""
    current_dir = os.getcwd()
    source_path = os.path.join(source_root, subfolder)
    dest_path = os.path.join(current_dir, subfolder)
    
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source folder '{source_path}' does not exist")
    
    # Remove destination if it exists
    if os.path.exists(dest_path):
        shutil.rmtree(dest_path)
    
    # Copy source to destination
    shutil.copytree(source_path, dest_path)
    print(f"  Copied '{source_path}' -> '{dest_path}'")
    
    return dest_path


def execute_script_in_subfolder(subfolder, script_name, config_args, has_sudo):
    """Execute Python script in the specified subfolder."""
    # Build command
    script_path = f"./{subfolder}/{script_name}"
    
    if has_sudo:
        cmd = ['sudo', 'python', script_path] + config_args
    else:
        cmd = ['python', script_path] + config_args
    
    print(f"  Executing: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.stdout:
            print(f"  STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"  STDERR:\n{result.stderr}")
            
        if result.returncode != 0:
            print(f"  Warning: Script exited with code {result.returncode}")
        else:
            print(f"  Script completed successfully")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"  Error: Script timed out after 300 seconds")
        return False
    except FileNotFoundError:
        print(f"  Error: Script '{script_name}' not found in '{subfolder}'")
        return False
    except Exception as e:
        print(f"  Error executing script: {e}")
        return False


def collect_results_from_subfolder(subfolder):
    """Collect result files from subfolder to output directory."""
    current_dir = os.getcwd()
    subfolder_path = os.path.join(current_dir, subfolder)
    output_dir = os.path.join(current_dir, 'output-' + subfolder)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Find result files in the subfolder
    result_files = []
    for root, dirs, files in os.walk(subfolder_path):
        for file in files:
            if file.startswith('result-'):
                result_files.append(os.path.join(root, file))
    
    if not result_files:
        print(f"  No result files found in '{subfolder}'")
        return
    
    print(f"  Found {len(result_files)} result file(s) in '{subfolder}':")
    for result_file in result_files:
        try:
            filename = os.path.basename(result_file)
            dest_path = os.path.join(output_dir, filename)
            shutil.copy2(result_file, dest_path)
            print(f"    Copied '{result_file}' -> '{dest_path}'")
        except Exception as e:
            print(f"    Error copying '{result_file}': {e}")


def cleanup_subfolder(subfolder):
    """Remove the subfolder from current directory."""
    current_dir = os.getcwd()
    subfolder_path = os.path.join(current_dir, subfolder)
    
    if os.path.exists(subfolder_path):
        shutil.rmtree(subfolder_path)
        print(f"  Cleaned up subfolder '{subfolder}'")


def execute_single_row(row_index, table_row):
    """Execute single row: copy, run, collect, cleanup."""
    source_root, subfolder, command = table_row
    
    print(f"\n--- Processing Row {row_index}: {subfolder} ---")
    print(f"  Source: {source_root}/{subfolder}")
    print(f"  Command: {command}")
    
    try:
        # Step 1: Parse command
        has_sudo, script_name, config_args = parse_command(command)
        print(f"  Parsed - Sudo: {has_sudo}, Script: {script_name}, Args: {config_args}")
        
        # Step 2: Copy source to subfolder
        copy_source_to_subfolder(source_root, subfolder)
        
        # Step 3: Execute script
        success = execute_script_in_subfolder(subfolder, script_name, config_args, has_sudo)
        
        # Step 4: Collect results (even if execution failed)
        collect_results_from_subfolder(subfolder)
        
        # Step 5: Cleanup
        cleanup_subfolder(subfolder)
        
        if success:
            print(f"  Row {row_index} completed successfully")
        else:
            print(f"  Row {row_index} completed with warnings")
            
    except Exception as e:
        print(f"  Error processing row {row_index}: {e}")
        # Still cleanup on error
        cleanup_subfolder(subfolder)


def execute_table_row(execution_table):
    """Execute all rows in the table sequentially."""
    # Check table length first
    num_rows = len(execution_table)
    print(f"\n--- Sequential Execution ({num_rows} rows) ---")
    
    # Loop through all rows
    for row_index, table_row in enumerate(execution_table):
        execute_single_row(row_index, table_row)


def main():
    """Main program entry point."""
    print("Fetch Executor Starting...")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Load and validate configuration
    config = load_yaml_config(args.config_file)
    validate_config(config)
    
    print(f"Source root: {config['source_root']}")
    print(f"Programs to execute: {len(config['programs'])}")
    
    # Create execution table
    print("\n--- Creating Execution Table ---")
    execution_table = create_execution_table(config)
    
    # Execute all rows in the table
    execute_table_row(execution_table)
    
    print("\nFetch Executor Completed!")


if __name__ == "__main__":
    main()