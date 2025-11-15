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

            # Execute the script
            exec(script, namespace)

            # Check if there's a return value
            # The script should set a 'return' statement or we look for common patterns
            if 'return' in namespace:
                return namespace['return']

            # Try to evaluate the script as an expression to get the last value
            try:
                # This is a workaround: compile and exec, then check for implicit return
                # Since we already exec'd, we need to parse for returns
                # For simplicity, let's use a wrapper function approach
                wrapped_script = f"def __gensi_user_script():\n"
                for line in script.split('\n'):
                    wrapped_script += f"    {line}\n"

                wrapper_namespace = context.copy()
                exec(wrapped_script, wrapper_namespace)
                return wrapper_namespace['__gensi_user_script']()

            except SyntaxError:
                # Script doesn't have a return value
                raise ValueError("Python script must return a value")

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
