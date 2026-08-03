# RUSHX — EV Charging, BESS & Solar Solutions Platform (PRD)

## Original Problem Statement
Premium web platform for RUSHX (India's EV charging solutions company): marketing website + product showcase + quote/lead capture + JWT/Google auth customer portal + AMC subscription portal + service booking + admin operations dashboard. Products: EV Chargers (Portable/3.3/7.4/11/22kW), PowerBoy Powerwall (BESS), Hearth Solar Inverter, Custom OEM. Services: Manufacturing, Installation, PCB-level Repair, AMC.

## User Choices (v1)
- All third-party integrations MOCKED (Razorpay, Twilio WhatsApp, Resend) — turn on later
- Auth: Emergent-managed Google login
- AMC tiers: sensible defaults (Basic ₹4,999 / Standard ₹9,999 / Premium ₹18,999 per year)
- Case studies / blog: pushed to later phase
- Product visuals: sourced/generated

## Architecture
- Frontend: React + Tailwind + shadcn/ui + framer-motion + recharts + react-hook-form; light/dark mode
- Backend: FastAPI, all routes under /api
- DB: MongoDB (products, amc_plans, users, user_sessions, leads, bookings, subscriptions, invoices, quotes, messages)
- Auth: Emergent Google OAuth, session_token cookie (httpOnly/secure/samesite=none) + Bearer fallback; role=admin for crazycoder4192@gmail.com

## User Personas
- Individuals / homeowners / EV owners; Businesses; Institutions; Enterprise/fleet/govt/OEM; Internal RUSHX admins

## Implemented (2026-08-03)
- Marketing site: Home (hero, animated counters, product grid, services strip, why, segments, CTA), Products catalog, Product detail, Services, Why RUSHX, Segments, Contact
- Quote/lead capture: reusable QuoteDialog on hero/products/segments + Contact form → creates lead + mocked WhatsApp ack
- Auth: Google login, AuthCallback, ProtectedRoute (customer + adminOnly)
- Customer portal: dashboard KPIs, service bookings list + book dialog (type/date/slot/device/desc), AMC plan cards (subscribe/cancel, mocked Razorpay + invoice), quotes (approve/decline), invoices
- Admin dashboard: KPI cards, leads pipeline chart + inbox (status change, send quote), bookings table (technician assign + status), AMC subscribers, customers, WhatsApp message log
- Full light/dark mode, responsive, data-testid coverage
- Verified: 50/50 backend pytest pass; all frontend flows verified by testing agent

## MOCKED (not real integrations)
- Razorpay subscriptions/invoices, Twilio WhatsApp (messages log), Resend email

## Backlog / Remaining
- P1: Turn on real Razorpay recurring subscriptions; real Twilio WhatsApp; Resend renewal/booking emails
- P1: Object storage for service photos + product image CMS uploads
- P2: Admin product catalog CMS (edit specs/images/prices), case studies + blog CMS
- P2: Registered devices in profile; renewal reminders (scheduled)
- P2: shadcn Calendar for booking date + past-date validation; loading/error states on dashboards
- P3: e-commerce checkout for spares, technician app, OCPP, multi-language, dealer portal, referrals

## Next Tasks
- Wire real integrations (Razorpay/Twilio/Resend) when keys provided
- Admin catalog CMS + object storage
