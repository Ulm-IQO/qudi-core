import ast
import os

class PublicMethodVisitor(ast.NodeVisitor):
    def __init__(self):
        self.public_methods = 0
        self.documented_methods = 0
        self.enclosing_scopes = []

    def visit_FunctionDef(self, node):
        if not node.name.startswith("__") and (not node.name.startswith("_") or "__all__" in self.enclosing_scopes):
            self.public_methods += 1
            # Check if the first node in the function body is a string (which would be a docstring)
            if node.body and isinstance(node.body[0], (ast.Expr, ast.Constant)) and isinstance(node.body[0].value, (ast.Str, ast.Constant)):
                self.documented_methods += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.enclosing_scopes.append(node.name)
        self.generic_visit(node)
        self.enclosing_scopes.pop()

    def visit_Module(self, node):
        # Initialize enclosing scopes, and handle __all__ if present
        self.enclosing_scopes = []
        if hasattr(node, 'body'):
            for item in node.body:
                if isinstance(item, ast.Assign) and any(target.id == '__all__' for target in item.targets if isinstance(target, ast.Name)):
                    self.enclosing_scopes = [name.s for name in item.value.elts if isinstance(name, ast.Str)]
        self.generic_visit(node)

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
directory = os.path.join("src", "qudi")



# Call the function to parse files and calculate coverage
total_methods, documented_methods = parse_files(directory)

# Calculate coverage
coverage = (documented_methods / total_methods) * 100 if total_methods != 0 else 0

print(f"Total public methods: {total_methods}")
print(f"Documented public methods: {documented_methods}")
print(f"Documentation coverage: {coverage:.2f}%")
