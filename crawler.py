import os
import pathlib

import tree_sitter_languages as tsl
from tree_sitter import Node, Language, Parser
from typing import Set, List, Dict
import tree_sitter_python as tspython


class PythonCodeWalker:
    def __init__(self):
        # Get the Python language parser
        self.language = Language(tspython.language())
        self.parser = Parser()
        self.parser.language = self.language

    def parse_file(self, filepath: str) -> Node:
        """Parse a Python file and return its AST root node."""
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()

        tree = self.parser.parse(bytes(code, 'utf-8'))
        return tree.root_node

    def extract_imports(self, node: Node, source_code: bytes) -> List[str]:
        """Extract all imports from a Python file's AST."""
        imports = []

        def walk_imports(node: Node):
            if node.type == 'import_statement':
                # Extract module names from import statements
                for child in node.children:
                    if child.type == 'dotted_name':
                        module_name = source_code[child.start_byte:child.end_byte].decode('utf-8')
                        imports.append(module_name)

            elif node.type == 'import_from_statement':
                # Extract module name from 'from X import Y' statements
                for child in node.children:
                    if child.type == 'dotted_name':
                        module_name = source_code[child.start_byte:child.end_byte].decode('utf-8')
                        imports.append(module_name)
                        break

            # Recursively walk children
            for child in node.children:
                walk_imports(child)

        walk_imports(node)
        return imports

    def find_function_definitions(self, node: Node, source_code: bytes) -> List[Dict]:
        """Find all function definitions in the AST."""
        functions = []

        def walk_functions(node: Node):
            if node.type == 'function_definition':
                # Get function name
                name_node = next((child for child in node.children if child.type == 'identifier'), None)
                if name_node:
                    func_name = source_code[name_node.start_byte:name_node.end_byte].decode('utf-8')

                    # Get function parameters
                    params_node = next((child for child in node.children if child.type == 'parameters'), None)
                    params = []
                    if params_node:
                        for param in params_node.children:
                            if param.type == 'identifier':
                                params.append(source_code[param.start_byte:param.end_byte].decode('utf-8'))

                    functions.append({
                        'name': func_name,
                        'parameters': params,
                        'line': node.start_point[0] + 1  # Line numbers are 0-indexed
                    })

            # Recursively walk children
            for child in node.children:
                walk_functions(child)

        walk_functions(node)
        return functions

    def walk_directory(self, start_file: str, base_dir: str = None) -> Dict:
        """
        Walk through directory starting from a specific file,
        following imports to discover related files.
        """
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(start_file))

        visited_files = set()
        files_to_process = [os.path.join(base_dir, start_file)]
        result = {}

        while files_to_process:
            current_file = files_to_process.pop(0)

            if current_file in visited_files:
                continue

            visited_files.add(current_file)

            if not os.path.exists(current_file) or not current_file.endswith('.py'):
                continue

            print(f"Processing: {current_file}")

            try:
                # Parse the file
                root_node = self.parse_file(current_file)
                with open(current_file, 'rb') as f:
                    source_code = f.read()

                # Extract information
                imports = self.extract_imports(root_node, source_code)
                functions = self.find_function_definitions(root_node, source_code)

                result[current_file] = {
                    'imports': imports,
                    'functions': functions,
                    'size': len(source_code),
                    'lines': source_code.count(b'\n') + 1
                }

                # Try to find imported files in the same directory structure
                for imp in imports:
                    # Convert module name to file path
                    module_path = imp.replace('.', os.sep) + '.py'
                    possible_paths = [
                        os.path.join(base_dir, module_path),
                        os.path.join(os.path.dirname(current_file), module_path),
                        os.path.join(base_dir, imp + '.py'),
                        os.path.join(os.path.dirname(current_file), imp + '.py')
                    ]

                    for path in possible_paths:
                        if os.path.exists(path) and path not in visited_files:
                            files_to_process.append(path)
                            break

            except Exception as e:
                print(f"Error processing {current_file}: {e}")
                result[current_file] = {'error': str(e)}

        return result

    def print_ast_structure(self, node: Node, source_code: bytes, indent: int = 0):
        """Print the AST structure for debugging."""
        indent_str = "  " * indent

        # Get node text if it's a leaf node
        if len(node.children) == 0:
            text = source_code[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')
            # Truncate long text
            if len(text) > 50:
                text = text[:50] + "..."
            print(f"{indent_str}{node.type}: {repr(text)}")
        else:
            print(f"{indent_str}{node.type}")

        # Recursively print children
        for child in node.children:
            self.print_ast_structure(child, source_code, indent + 1)


def get_concatenated_files_to_analyze(start_file: str, base_dir: str = None) -> str:
    walker = PythonCodeWalker()
    results = walker.walk_directory(start_file, base_dir)

    files = []
    for filepath, info in results.items():
        print(f"\nFile: {filepath}")
        if 'error' in info:
            print(f"  Error: {info['error']}")
        else:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    code = f.read()
                    files.append(f"## {filepath}\n{code}")

    return "\n\n".join(files)

# Example usage
if __name__ == "__main__":
    walker = PythonCodeWalker()

    # Walk through directory starting from agent.py
    results = walker.walk_directory("agent.py", base_dir="/Users/kyrylokyrykov/.nearai/registry/kirikiri.near/travel-assistant/0.0.1")

    # Print results
    print("\n=== Code Analysis Results ===\n")
    for filepath, info in results.items():
        print(f"\nFile: {filepath}")
        if 'error' in info:
            print(f"  Error: {info['error']}")
        else:
            print(f"  Lines: {info['lines']}")
            print(f"  Size: {info['size']} bytes")
            print(f"  Imports: {', '.join(info['imports']) if info['imports'] else 'None'}")
            print(f"  Functions:")
            for func in info['functions']:
                params = ', '.join(func['parameters'])
                print(f"    - {func['name']}({params}) at line {func['line']}")
