# WIND Sentinel

AI-powered early fault detection system for wind turbines using event-driven microservice architecture.

## Problem

Wind turbines experience unexpected failures that cause costly downtime. WIND Sentinel uses SCADA sensor data and ML models (Isolation Forest, XGBoost) to predict failures before they happen.

## Architecture

```
  ┌─────────── INTERNAL (RabbitMQ Event Bus) ───────────────────────┐
  │                                                                  │
  │  SCADA CSV ──→ data-ingestion ──→ feature-service ──→ prediction │
  │               [measurement.raw]  [measurement.features]  │       │
  │                                                   notification   │
  │                                                    │       │     │
  └────────────────────────────────────────────────────┼───────┼─────┘
                                                       │       │
                                                  WebSocket  WebSocket
                                                       │       │
  ┌─────────── EXTERNAL (API Gateway) ─────────────────┼───────┼─────┐
  │                   REST + Auth + PostgreSQL          │       │     │
  └─────────────────────┬──────────────────────────────┘───────┘─────┘
                        │                              │
                  Web Dashboard                   Mobile App
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data Ingestion / Feature / Prediction | Python + FastAPI |
| API Gateway / Notification | Node.js + Express |
| Web Dashboard | React (Vite) |
| Mobile App | React Native (Expo) |
| Message Broker | RabbitMQ |
| Database | PostgreSQL |

## Quick Start

```bash
docker compose up -d
```

## Project Structure

```
wind-sentinel/
├── docker-compose.yml
├── .env
├── data/raw/                 # SCADA dataset (Wind Farm A)
└── services/
    ├── data-ingestion-service/
    ├── feature-service/
    ├── prediction-service/
    ├── notification-service/
    └── api-gateway/
```
