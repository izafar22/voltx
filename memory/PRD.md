# VoltGrid — EV Charging Network Platform (PRD)

## Original Problem Statement (Pivot)
Build the smallest product that operates a real EV charging network. Three parts: EV Charger (OCPP 1.6J, start/stop, reports kWh/status/faults), Cloud Server (users, wallets, cost calc, 90/10 revenue split, commands), and apps (Customer, Owner, Admin). Wallet-based prepaid billing, QR-code charging, single ₹/kWh pricing, minimum wallet balance check before starting.

## User Choices
- Replaced the earlier RUSHX marketing/AMC app entirely
- Login: phone OTP, DEMO fixed code 123456 (no SMS gateway)
- Wallet top-up: MOCKED instant add (no payment gateway)
- Charger hardware: server-side simulator (OCPP 1.6J-style), time-accelerated (SIM_SPEED=120)
- Build all three roles at once
- Theme cues from globalcharge.com — clean, frictionless fintech aesthetic

## Architecture
- Frontend: React + Tailwind + shadcn/ui + framer-motion + recharts; fonts Outfit/Manrope/IBM Plex Mono; full light+dark; customer app is mobile-first (max-w-md), owner/admin are desktop dashboards
- Backend: FastAPI, all routes under /api; JWT auth (Bearer, localStorage `ev_token`); role-based (customer/owner/admin)
- DB: MongoDB (users, wallets, owner_wallets, transactions, owner_transactions, chargers, sessions, withdrawals, fault_logs, notifications, counters, otp_requests)

## Personas
Customer (EV owner), Charger Owner (host earning revenue), Company Admin (network ops).

## Implemented (2026-08-19)
- Auth: phone OTP → JWT, auto-create customer, demo accounts + one-tap login
- Customer: wallet (balance, quick top-up, transactions), scan/enter station code, charger detail, min ₹100 balance check, start charging, LIVE screen (animated SoC ring + energy/time/power/cost/voltage/current, 2s polling), stop→bill→history, notifications
- Charging simulator: time-accelerated energy accrual, cost capped to wallet balance (no overdraw), 90/10 split on stop
- Owner: earnings (today/month), units sold, wallet, chargers telemetry, transactions, withdrawal request
- Admin: revenue/commission(10%)/payouts(90%) KPIs, charger-health pie, live charger monitoring (voltage/current/power/temp/signal/firmware/heartbeat) with remote restart + status control, add charger (atomic IDs) / add owner, customers + wallet adjust, fault logs, withdrawal approvals
- Charger states: Available, Charging, Offline, Fault (Preparing/Finishing modeled in status set)
- Verified: 39/39 backend pytest; all 3 roles' frontend flows via testing agent; accounting fix confirmed (owner+company == collected)

## MOCKED (no real integrations)
- SMS OTP (fixed 123456), wallet top-up (no gateway), charger hardware/OCPP (simulator)

## Backlog / Remaining
- P1: Real OTP via Twilio; real payment gateway (UPI/cards) for wallet top-up; real OCPP 1.6J charger comms + WebSocket live push (replace polling)
- P1: Auto-stop + notification when wallet exhausted mid-session (currently caps cost)
- P2: Owner earnings via Mongo aggregation (scale); charger_id counter already atomic
- P2: Native mobile apps (Flutter); real QR camera scanning; bank transfer on withdrawal
- P3: Peak/night/member pricing, reservations, RFID, loyalty, OCPP telemetry dashboards

## Next Tasks
- Wire real integrations (Twilio OTP, payment gateway, OCPP) when keys/hardware available
- WebSocket-based live charging updates; wallet-exhaustion auto-stop
