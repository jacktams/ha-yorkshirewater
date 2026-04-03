"""Constants for pyyorkshirewater."""

BASE_URL = "https://my.yorkshirewater.com"
LOGIN_URL = "https://login.yorkshirewater.com"

CLIENT_ID = "css-onlineaccount-fe"
REDIRECT_URI = f"{BASE_URL}/account/callback/response"
SCOPES = "openid user-names css-onlineaccount-api css-registration-api"

LOGIN_PAGE = f"{LOGIN_URL}/account/LoginSignup"
AUTHORIZE_URL = f"{LOGIN_URL}/connect/authorize"
TOKEN_URL = f"{LOGIN_URL}/connect/token"

API_BASE = f"{BASE_URL}/api/account"

ENDPOINTS: dict[str, str] = {
    "meter_details": f"{API_BASE}/smartmeter/meter-details",
    "daily_consumption": f"{API_BASE}/smartmeter/daily-consumption",
    "yearly_consumption": f"{API_BASE}/smartmeter/yearly-consumption",
    "current_consumption": f"{API_BASE}/smartmeter/current-consumption",
    "your_usage": f"{API_BASE}/smartmeter/your-usage",
}
