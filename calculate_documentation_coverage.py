import ast
import os

class PublicMethodVisitor(ast.NodeVisitor):
    def __init__(self):
        self.public_methods = 0
        self.documented_methods = 0

    def visit_FunctionDef(self, node):
        if not node.name.startswith("__") and (not node.name.startswith("_") or "__all__" in self.enclosing_scopes):
            self.public_methods += 1
            if node.body and isinstance(node.body[0], ast.Expr):
                self.documented_methods += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.enclosing_scopes.append(node.name)
        self.generic_visit(node)
        self.enclosing_scopes.pop()

    def visit_Module(self, node):
        if hasattr(node, "__all__"):
            self.enclosing_scopes = node.__all__
        else:
            self.enclosing_scopes = []

def parse_files(directory):
    public_methods = 0
    documented_methods = 0

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=file_path)

                visitor = PublicMethodVisitor()
                visitor.visit(tree)

                public_methods += visitor.public_methods
                documented_methods += visitor.documented_methods

    return public_methods, documented_methods

# Specify the directory containing your Python files
directory = "../src/qudi/"

# Call the function to parse files and calculate coverage
total_methods, documented_methods = parse_files(directory)

# Calculate coverage
coverage = (documented_methods / total_methods) * 100 if total_methods != 0 else 0

print(f"Total public methods: {total_methods}")
print(f"Documented public methods: {documented_methods}")
print(f"Documentation coverage: {coverage:.2f}%")
