from typing import Dict, Any
from app.core.registry import ToolRegistry

@ToolRegistry.register()
def extract_functions(state: Dict[str, Any]) -> Dict[str, Any]:
    """Simulates extracting functions from code."""
    code = state.get("code", "")
    # Mock logic
    function_count = len(code.split("def ")) - 1
    return {"function_count": max(function_count, 1), "functions": ["func1", "func2"]}

@ToolRegistry.register()
def check_complexity(state: Dict[str, Any]) -> Dict[str, Any]:
    """Calculates complexity score."""
    # Mock complexity based on length
    code_len = len(state.get("code", ""))
    complexity = code_len / 100
    return {"complexity_score": complexity}

@ToolRegistry.register()
def detect_issues(state: Dict[str, Any]) -> Dict[str, Any]:
    """Detects code smells and quality issues deterministically."""
    code = state.get("code", "")
    issues = state.get("issues", [])
    iteration = state.get("iteration", 0)
    
    # Deterministic issue detection based on code characteristics
    new_issues = []
    
    # Check for common issues (deterministic)
    if len(code) > 200:
        new_issues.append("Function too long")
    if "print(" in code:
        new_issues.append("Uses print() instead of logging")
    if code.count("\n") > 20:
        new_issues.append("Too many lines in function")
    if "    " not in code and "\t" not in code and len(code) > 50:
        new_issues.append("Poor or missing indentation")
    
    # Simulate gradual improvement - reduce issues by ~30% each iteration
    # Keep only issues not yet fixed
    if iteration > 0:
        # Simulate fixing about 1-2 issues per iteration
        issues_to_keep = max(0, len(issues) - 2)
        issues = issues[:issues_to_keep]
    
    # Combine existing and new issues (new issues decrease as we improve)
    all_issues = issues + new_issues
    
    return {
        "issues": all_issues,
        "issue_count": len(all_issues),
        "iteration": iteration + 1
    }

@ToolRegistry.register()
def suggest_improvements(state: Dict[str, Any]) -> Dict[str, Any]:
    """Suggests fixes and updates quality score based on current issues."""
    issue_count = state.get("issue_count", 0)
    complexity = state.get("complexity_score", 0)
    iteration = state.get("iteration", 0)
    
    # Quality score calculation (0-10 scale)
    # Base quality starts at 5, decreases with issues and complexity
    quality = 10 - (issue_count * 1.5) - (complexity * 0.2)
    quality = max(0, min(10, quality))  # Clamp between 0 and 10
    
    # Simulate incremental code improvements
    code = state.get("code", "")
    
    # Add improvement comments based on iteration
    improvements = [
        "\n# Refactored for better readability",
        "\n# Added error handling",
        "\n# Optimized algorithm",
        "\n# Added documentation",
        "\n# Fixed code smells"
    ]
    
    if iteration > 0 and iteration <= len(improvements):
        code = code + improvements[iteration - 1]
    
    # Simulate fixing the print issue after a few iterations
    if iteration > 2 and "print(" in code:
        code = code.replace("print(", "logger.info(")
    
    return {
        "quality_score": quality,
        "code": code,
        "improvements_applied": iteration
    }
