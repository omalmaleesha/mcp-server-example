from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("docs")

USER_AGENT = "docs-app/1.0"
SERPER_URL=""

docs_urls = {
    "langchain": "python.langchain.com/docs",
    "llama-index": "docs.llamaindex.ai/en/stable",
    "openai": "platform.openai.com/docs",
}

async def search_web(query: str) -> dict | None:
  ...
  
async def fetch_url(url: str):
  ...

@mcp.tool()  
async def get_docs(query: str, library: str):
  ...

if __name__ == "__main__":
    print("Running MCP server")
    mcp.run(transport="stdio")