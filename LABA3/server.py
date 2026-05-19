from mcp.server.fastmcp import FastMCP
from datetime import datetime

# Инициализация сервера — имя видно в клиенте
mcp = FastMCP("my-first-mcp")

# Декоратор @mcp.tool() регистрирует функцию как инструмент
# Docstring становится описанием для LLM — пишем внятно
@mcp.tool()
def get_server_time() -> str:
    """Returns the current server time in ISO format."""
    return datetime.now().isoformat()

@mcp.tool()
def echo(message: str) -> str:
    """Echoes back the provided message. Useful for testing."""
    return f"Echo: {message}"

if __name__ == "__main__":
    # stdio — клиент запускает этот процесс сам
    mcp.run(transport="stdio")