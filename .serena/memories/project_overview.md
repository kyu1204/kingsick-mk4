# KingSick Project Overview

## Purpose
AI-powered automated trading system for Korean stock market (KOSPI) using BNF-style swing trading strategies. Integrates with Korea Investment & Securities API.

## Key Features
- Dual trading modes: AUTO (fully automated) / ALERT (notification with manual approval)
- AI signal generation based on technical indicators (RSI, MA, MACD, Bollinger Bands)
- Risk management: stop-loss, take-profit, trailing stop
- Real-time notifications via Telegram/Slack
- Backtesting capabilities (Phase 4)

## Tech Stack
- **Frontend**: Next.js 14, TypeScript, TailwindCSS, shadcn/ui, Lightweight Charts
- **Backend**: Python FastAPI, SQLAlchemy, APScheduler
- **Database**: PostgreSQL (main), Redis (cache), TimescaleDB (time-series)
- **External APIs**: Korea Investment & Securities (PyKis), Telegram Bot, Slack Webhook

## Target Users
Small private group (5 or fewer users)

## Development Status
New project - design phase completed, implementation not yet started.
