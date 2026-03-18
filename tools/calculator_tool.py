import ast
import math
import operator

# Safe operators and functions only
SAFE_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}
SAFE_FUNCTIONS = {
    "sqrt": math.sqrt, "abs": abs, "round": round,
    "floor": math.floor, "ceil": math.ceil,
    "log": math.log, "log10": math.log10,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "pi": math.pi, "e": math.e,
}

def _eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        op = SAFE_OPERATORS.get(type(node.op))
        if not op:
            raise ValueError(f"Unsupported operator: {node.op}")
        return op(_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op = SAFE_OPERATORS.get(type(node.op))
        if not op:
            raise ValueError(f"Unsupported operator: {node.op}")
        return op(_eval(node.operand))
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in SAFE_FUNCTIONS:
            args = [_eval(a) for a in node.args]
            return SAFE_FUNCTIONS[node.func.id](*args)
        raise ValueError(f"Unsupported function: {ast.dump(node.func)}")
    if isinstance(node, ast.Name) and node.id in SAFE_FUNCTIONS:
        return SAFE_FUNCTIONS[node.id]
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")

def run_python_expression(expression: str) -> str:
    """Safely evaluate a mathematical expression or unit conversion.

    Args:
        expression: A math expression string e.g. '2 ** 32', 'sqrt(144)', '100 * 1.08', 'log(1000, 10)'.

    Returns:
        The computed result as a string.
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _eval(tree.body)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Could not evaluate '{expression}': {e}"
