# Reddit-Posts-Stock-AI-Recommendation-System

An AI-powered stock analysis and recommendation system that scrapes Reddit's `r/wallstreetbets`, analyzes posts using AI agents, and generates a list of stock BUY recommendations.

A cron job is set up to run the workflow and send results to Discord every week. Please be aware - the recommendation is **NOT** a financial advice, use it at your own risk.

I am also hoping the workflow engine and AI agent framework can be adapted for other use cases in the future.

## Join the Discord Channel
If you want to receive the stock recommendations directly, please join my Discord: [https://discord.gg/XxP8z5dxFX](https://discord.gg/XxP8z5dxFX)

It's now still under testing and development, but you can see the recommendations in the `#stock-recommendations` channel.

Feel free to share your feedbacks and suggestions!

## Overview

Reddit-Posts-Stock-AI-Recommendation-System combines social media sentiment analysis with real-time web research to provide curated stock recommendations. It scrapes Reddit posts from `r/wallstreetbets`, processes them through specialized AI agents with web search capabilities, and uses a senior picker agent to select the highest-conviction opportunities from the pool of recommendations.

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

- **Real-Time Intelligence**: Each agent leverages OpenAI's web search tool to:
  - Verify recent catalysts and earnings news
  - Cross-check Reddit claims with authoritative sources
  - Gather diverse perspectives from multiple web sources
  - Ensure recommendations are grounded in current market reality

- **Discord Integration**: Automatically sends formatted recommendations to Discord channels

Example Discord Output:
![Discord Output Example](readme_resources/example_discord_v_0.1.0.png)

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

### Core Components

- **Reddit Scraper** (`stock_ai/reddit/`): Fetches posts from `r/wallstreetbets` using `PRAW`
- **AI Agents** (`stock_ai/agents/`): Specialized LLM agents with web search capabilities
  - **Reddit Agents**: News, DD, and YOLO agents that analyze posts and perform web research
  - **Stock Picker Agent**: Senior investor agent that selects top picks from all recommendations
  - Currently has hard dependency on OpenAI's GPT-5 model and Response API with web search tool
- **Workflow Engine** (`stock_ai/workflows/`): Orchestrates the entire analysis pipeline
  - A generic, extensible workflow engine that can be adapted for other use cases
  - Supports parallel execution of agents and idempotent step processing
  - Modular design for easy addition of new agents or data sources
  - SQL-based persistence layer for tracking workflow state
- **Discord Notifier** (`stock_ai/notifiers/`): Sends formatted results to Discord
  - Will be extended to support other notification channels in the future, such as email

### Workflow Pipeline

1. **Data Collection**: Scrape recent posts from r/wallstreetbets (News, DD, YOLO flairs)
2. **Post Filtering**: Filter posts by engagement metrics and content quality
3. **AI Analysis with Web Research**: Run specialized agents in parallel on filtered posts
   - Each agent analyzes posts in their category (News/DD/YOLO)
   - Agents perform real-time web searches to verify claims and gather market intelligence
   - Generate initial BUY recommendations with confidence levels
4. **Stock Selection**: Stock Picker agent evaluates all recommendations
   - Reviews investment thesis quality and risk profiles
   - Applies institutional investor criteria to select top 1-3 picks
   - Provides rationale for final selections
5. **Discord Notification**: Send curated recommendations to Discord channel


## Roadmap
- [ ] Develop evaluation framework to measure performance of recommendations over time
- [ ] Integrate email notification channel so it becomes a newsletter system


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