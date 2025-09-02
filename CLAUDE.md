# Fetch Executor Program

## Overview
Python program for Ubuntu 24.04 with Python 3.12 that:
- Reads YAML configuration specifying source code locations and execution parameters
- Copies specified subfolders from remote/source locations to current working directory
- Executes Python programs with either regular or sudo privileges
- Collects result files (prefixed with 'result-') and copies them to ./output-{subfolder} directories

## Features
- YAML configuration parsing
- Source code folder copying to current working directory
- Dual execution modes: normal and sudo privileges
- Support for programs with or without configuration files
- Automatic result file collection and output management

## YAML Configuration Format
```yaml
source_root: "/full/path/to/source/code/root"
execution_mode: "normal"  # or "sudo" 
programs:
  sub-folder-1: "program1"
  sub-folder-2: "program2 config2.yaml"
```

### Configuration Fields:
- **source_root**: Full path to the root directory containing source code subfolders
- **execution_mode**: Either "normal" for regular execution or "sudo" for elevated privileges
- **programs**: Dictionary mapping subfolder names to execution commands
  - Key: subfolder name to copy from source_root
  - Value: program name with optional configuration file

## Usage
```bash
python fetch_executor.py config.yaml
```

## Dynamic Output Directory Changes Summary
This implementation creates separate output directories for each subfolder using dynamic naming:
- **Pattern**: `./output-{subfolder_name}/`
- **Example**: For subfolder `sub-folder-1`, creates `./output-sub-folder-1/`
- **Implementation**: Uses string concatenation `'output-' + subfolder_name`
- **Result Collection**: Each program's result files are collected to its own dedicated output directory
- **Multiple Subfolders**: Supports multiple subfolders with isolated result collections

## Execution Flow
1. **Parse CLI Arguments**: Read YAML configuration file path
2. **Parse YAML Configuration**: Extract source_root, execution_mode, and programs
3. **Copy Source Code**: Copy each specified subfolder to current working directory
4. **Execute Programs**: Run each program with appropriate execution mode
5. **Collect Results**: Find all files with 'result-' prefix and copy to ./output-{subfolder} directories

## Implementation Details

### Modules:
- **CLI Parser**: Uses argparse for command-line argument handling
- **YAML Parser**: Uses PyYAML for configuration file parsing
- **File Operations**: Uses shutil.copytree() for directory copying
- **Program Execution**: Uses subprocess.run() with normal or sudo modes
- **Result Collection**: Scans for result files and copies to output directory

### Execution Modes:
- **Normal**: `subprocess.run(['python', f'./{program}'])`
- **Sudo**: `subprocess.run(['sudo', 'python', f'./{program}'])`

### File Structure:
```
current-directory/
├── fetch_executor.py
├── config.yaml
├── copied-subfolder-1/
├── copied-subfolder-2/
├── output-sub-folder-1/
│   ├── result-file1.txt
│   └── result-analysis1.json
└── output-sub-folder-2/
    ├── result-file2.txt
    └── result-data2.csv
```

## Dependencies
- Python 3.12+
- PyYAML>=6.0
- Ubuntu 24.04 environment