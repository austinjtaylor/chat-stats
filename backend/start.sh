#!/bin/bash
# Railway start script for FastAPI backend

uvicorn app:app --host 0.0.0.0 --port $PORT
