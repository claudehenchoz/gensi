"""Python script executor for user-provided scripts in .gensi files."""

from typing import Any


class PythonExecutor:
    """
    Executes Python scripts from .gensi files.

    Per user requirements, scripts are trusted and not sandboxed.
    """

    def execute(self, script: str, context: dict[str, Any]) -> Any:
        """
        Execute a Python script with given context.

        Args:
            script: The Python script to execute
            context: Dictionary of variables to inject into the script's namespace

        Returns:
            The value returned by the script (last expression or explicit return)

        Raises:
            Exception: If the script execution fails
        """
        try:
            # Create execution namespace with context variables
            namespace = context.copy()

            # Strategy 1: If script contains 'return', wrap in a function
            if 'return' in script:
                # Indent each line and wrap in a function
                lines = script.split('\n')
                indented_lines = [f"    {line}" if line.strip() else "" for line in lines]
                wrapped_script = "def __gensi_user_script():\n" + "\n".join(indented_lines)

                try:
                    exec(wrapped_script, namespace)
                    return namespace['__gensi_user_script']()
                except SyntaxError:
                    # If wrapping fails, fall through to other strategies
                    pass

            # Strategy 2: Try evaluating as expression (implicit return)
            try:
                return eval(script, namespace)
            except (SyntaxError, TypeError):
                # Not a simple expression
                pass

            # Strategy 3: Execute as statements (no return value expected)
            exec(script, namespace)
            return None

        except Exception as e:
            raise Exception(f"Python script execution failed: {str(e)}") from e


def execute_python_script(script: str, context: dict[str, Any]) -> Any:
    """
    Convenience function to execute a Python script.

    Args:
        script: The Python script to execute
        context: Dictionary of variables to inject into the script's namespace

    Returns:
        The value returned by the script

    Raises:
        Exception: If the script execution fails
    """
    executor = PythonExecutor()
    return executor.execute(script, context)
