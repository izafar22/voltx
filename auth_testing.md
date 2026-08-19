# Auth Testing — VoltGrid (Phone OTP + JWT)

## Login (no SMS, fixed OTP 123456)
```
URL=$REACT_APP_BACKEND_URL
curl -s -X POST $URL/api/auth/request-otp -H "Content-Type: application/json" -d '{"phone":"+919000000003"}'
TOK=$(curl -s -X POST $URL/api/auth/verify-otp -H "Content-Type: application/json" -d '{"phone":"+919000000003","otp":"123456"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s $URL/api/auth/me -H "Authorization: Bearer $TOK"
```
Seeded: admin +919000000001, owner +919000000002, customer +919000000003.

## Browser (frontend stores JWT in localStorage)
```
await page.goto(APP_URL + "/login")
# use demo buttons, or set token directly:
await page.evaluate("localStorage.setItem('ev_token', 'JWT_HERE')")
await page.goto(APP_URL + "/app")
```
Roles: customer→/app, owner→/owner, admin→/admin.
