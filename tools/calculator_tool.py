import ast
import math
import operator
from utils.tool_logger import logged_tool

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
            return SAFE_FUNCTIONS[node.func.id](*[_eval(a) for a in node.args])
        raise ValueError(f"Unsupported function")
    if isinstance(node, ast.Name) and node.id in SAFE_FUNCTIONS:
        return SAFE_FUNCTIONS[node.id]
    raise ValueError(f"Unsupported expression")

def _compute(expression: str):
    tree = ast.parse(expression.strip(), mode="eval")
    return _eval(tree.body)

@logged_tool
def run_python_expression(expression: str) -> str:
    """Safely evaluate a math expression. Runs twice to verify result (Chain-of-Verification).

    Args:
        expression: A math expression e.g. '2 ** 32', 'sqrt(144)', '50 * 40'.

    Returns:
        Verified computation result.
    """
    try:
        result1 = _compute(expression)
        result2 = _compute(expression)  # CoVe: run twice, compare

        if result1 != result2:
            return f"⚠️ Inconsistent results for '{expression}': {result1} vs {result2}. Please verify manually."

        # Format nicely
        if isinstance(result1, float) and result1.is_integer():
            result1 = int(result1)

        return f"✅ {expression} = **{result1}** _(verified)_"
    except Exception as e:
        return f"Could not evaluate '{expression}': {e}"
