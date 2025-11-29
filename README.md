# Reddit-Posts-Stock-AI-Recommendation-System

An AI-powered stock analysis and recommendation system that:
- Scrapes Reddit's `r/wallstreetbets`, analyzes posts using AI agents, and generates a list of stock BUY recommendations.
- Based on the recommendations, a trader AI agent make decisions on which stocks to buy/sell for a virtual portfolio.
- A daily cron job that tracks the portfolio performance


Please be aware - the recommendation is **NOT** a financial advice, use it at your own risk.

I am also hoping the workflow engine and AI agent framework can be adapted for other use cases in the future.

## Join the Discord Channel
If you want to receive the stock recommendations directly, please join my Discord: [https://discord.gg/XxP8z5dxFX](https://discord.gg/XxP8z5dxFX)

You can see the recommendations and the daily performance updates of the virtual portfolio in the `#stock-recommendations` channel.

Feel free to share your feedbacks and suggestions!

## Overview

The system runs on three github workflows:
1. **Reddit Stock Recommendation Workflow**: Runs weekly to scrape Reddit posts, analyze them with AI agents, generate stock BUY recommendations, and send them to Discord
2. **Weekly Trade Workflow**: Runs weekly to make buy/sell/hold decisions based on the latest recommendations and update the virtual portfolio, then send the trade summary to Discord
3. **Daily Performance Workflow**: Runs daily to track the portfolio performance and send updates to Discord

## Features

- **Multi-Agent Analysis with Web Search**: Three specialized AI agents analyze different types of Reddit posts and verify findings through real-time web research:
  - **News Agent**: Extracts stock mentions from news posts and performs web searches to verify recent catalysts, earnings, and market developments
  - **DD Agent**: Analyzes due diligence posts and cross-references claims with current market data, filings, and news sources
  - **YOLO Agent**: Identifies high-risk/reward opportunities from YOLO posts and validates momentum through real-time web searches

- **Stock Picker Agent**: A senior institutional investor AI agent that:
  - Reviews all recommendations from the three specialized agents
  - Evaluates investment thesis strength, risk profiles, and market timing
  - Applies 20+ years of market experience to identify patterns
  - Selects the top 1-3 highest-conviction picks
  - Provides rationale for final selections

- **Trading Decision AI Agent**:
  - Reviews the latest stock recommendations, current portfolio holdings and current market prices
  - Makes buy/sell/hold decisions based on recommendation confidence levels and portfolio diversification
  - Generates a trade summary with reasoning for each action
  - Updates the virtual portfolio based on trades executed
  - Caveat: Trades are simulated using current prices from the Yahoo Finance API and may not reflect actual broker execution prices

- **Memory Persistence**: Uses PostgreSQL (via Supabase) to store workflow state, Reddit posts, agent analyses, recommendations, portfolio data, trades, and performance metrics, etc.
  - Enables tracking of recommendation performance over time
  - Facilitates idempotent workflow execution

- **Workflow Engine**: A modular and extensible workflow engine that orchestrates the entire analysis pipeline
  - Supports parallel execution of AI agents
  - Idempotent step processing with SQL-based persistence
  - Easy to add new agents or data sources in the future


- **Discord Integration**: Automatically sends recommendations, trade summaries, and portfolio performance updates to Discord channels

Example Discord Output:
![Discord Output Example](readme_resources/example_discord_v_0.1.0.png)


![Discord Output Example 2](readme_resources/discord_trade_example.png)


## Tech Stack
Python, PRAW (Reddit API), OpenAI GPT-5 with Web Search, Yahoo Finance API, PostgreSQL (Supabase), Discord API, Alembic (DB migrations), GitHub Actions

(I roll my own workflow engine and AI agent framework!)

## Architecture

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#1e3a8a','primaryTextColor':'#fff','primaryBorderColor':'#1e40af','lineColor':'#6366f1','secondaryColor':'#0f172a','tertiaryColor':'#fff','fontSize':'14px'}}}%%
flowchart TB
    Start([Start Workflow]):::startEnd
    End([End]):::startEnd
    
    Start --> RunMeta[Insert Run Metadata]:::process
    RunMeta --> Scrape[Scrape Reddit Posts<br/>r/wallstreetbets]:::process
    
    Scrape --> Filter[Filter Posts<br/>by Engagement & Quality]:::process
    
    Filter --> Split{Split by<br/>Flair Type}:::decision
    
    Split -->|News| News[News Posts]:::data
    Split -->|DD| DD[DD Posts]:::data
    Split -->|YOLO| YOLO[YOLO Posts]:::data
    
    News --> NewsAgent[News Agent<br/>+ Web Search]:::agent
    DD --> DDAgent[DD Agent<br/>+ Web Search]:::agent
    YOLO --> YOLOAgent[YOLO Agent<br/>+ Web Search]:::agent
    
    NewsAgent --> NewsRec[(News<br/>Recommendations)]:::storage
    DDAgent --> DDRec[(DD<br/>Recommendations)]:::storage
    YOLOAgent --> YOLORec[(YOLO<br/>Recommendations)]:::storage
    
    NewsRec --> Merge[Merge All<br/>Recommendations]:::process
    DDRec --> Merge
    YOLORec --> Merge
    
    Merge --> Picker[Stock Picker Agent<br/>Senior Investor<br/>20+ Years Experience]:::picker
    
    Picker --> Final[(Final<br/>Recommendations<br/>Top 1-3 Picks)]:::storage
    
    Final --> Discord[Discord Notifier]:::process
    
    Discord --> End
    
    subgraph Stage1["Stage 1-2: Data Collection"]
        RunMeta
        Scrape
        Filter
    end
    
    subgraph Stage2["Stage 3: Parallel AI Analysis"]
        Split
        News
        DD
        YOLO
        NewsAgent
        DDAgent
        YOLOAgent
        NewsRec
        DDRec
        YOLORec
    end
    
    subgraph Stage3["Stage 4: Stock Selection"]
        Merge
        Picker
        Final
    end
    
    subgraph Stage4["Stage 5: Notification"]
        Discord
    end
    
    subgraph External["External Services"]
        Reddit[Reddit API<br/>PRAW]:::external
        OpenAI[OpenAI API<br/>GPT-5 + Web Search]:::external
        DB[(PostgreSQL<br/>Supabase)]:::external
        DiscordAPI[Discord API]:::external
    end
    
    Scrape -.->|fetch posts| Reddit
    NewsAgent -.->|analyze + search| OpenAI
    DDAgent -.->|analyze + search| OpenAI
    YOLOAgent -.->|analyze + search| OpenAI
    Picker -.->|evaluate| OpenAI
    
    RunMeta -.->|persist| DB
    NewsRec -.->|persist| DB
    DDRec -.->|persist| DB
    YOLORec -.->|persist| DB
    Final -.->|persist| DB
    
    Discord -.->|send| DiscordAPI
    
    classDef startEnd fill:#10b981,stroke:#059669,stroke-width:3px,color:#fff
    classDef process fill:#3b82f6,stroke:#2563eb,stroke-width:2px,color:#fff
    classDef decision fill:#f59e0b,stroke:#d97706,stroke-width:2px,color:#000
    classDef data fill:#8b5cf6,stroke:#7c3aed,stroke-width:2px,color:#fff
    classDef agent fill:#06b6d4,stroke:#0891b2,stroke-width:3px,color:#fff
    classDef picker fill:#ec4899,stroke:#db2777,stroke-width:3px,color:#fff
    classDef storage fill:#6366f1,stroke:#4f46e5,stroke-width:2px,color:#fff
    classDef external fill:#64748b,stroke:#475569,stroke-width:2px,color:#fff
    
    style Stage1 fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#94a3b8
    style Stage2 fill:#1e293b,stroke:#06b6d4,stroke-width:2px,color:#94a3b8
    style Stage3 fill:#1e293b,stroke:#ec4899,stroke-width:2px,color:#94a3b8
    style Stage4 fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#94a3b8
    style External fill:#0f172a,stroke:#64748b,stroke-width:2px,color:#94a3b8
```

## Roadmap
- [X] Develop evaluation framework to measure performance of recommendations over time
- Any suggestions are welcome!

## How to

### Database migration
Uses Alembic for database migrations. To create a new migration after modifying the models, run:
```bash
uv run alembic revision --autogenerate -m "your message"
```
Make sure your `.env` file has `DATABASE_URL_REMOTE` set to your remote database URL. (For me, it's a Supabase Postgres database)

Then apply the migration with:
```bash
DB_TARGET=REMOTE uv run alembic upgrade head
```