"""AccoBot MCP Client — connect to external MCP servers.

Provides the ability to connect to MCP (Model Context Protocol) servers
and register their tools into AccoBot's tool registry.

Architecture (simplified from Hermes Agent):
- Config in ~/.accobot/config.yaml under mcp_servers key
- Background asyncio event loop for long-lived connections
- Tools registered with prefix mcp_{server}_{tool}
- Transparent to the agent (same registry, same dispatch)
"""
