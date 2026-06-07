# PortfolioRadar Python Run Order

1. `app/config.py` - loads environment and default settings.
2. `app/datasources/*` - fetches market, fund, index, and news data.
3. `app/models/*` - defines database tables and initializes storage.
4. `app/repositories/*` - reads and writes model objects.
5. `app/engines/*` - calculates technical, event, sentiment, and final signals.
6. `app/services/*` - orchestrates daily pipeline and reporting.
7. `app/tasks/*` - schedules recurring jobs.
8. `app/notifiers/*` - sends reports to users.
9. `mcp_server/*` - optional MCP integration.
