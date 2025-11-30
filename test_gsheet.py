from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request

creds = Credentials.from_service_account_file(
    "gen-lang-client-0331880280-82e83aa91427.json",
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

creds.refresh(Request())  # nếu có vấn đề chữ ký/giờ sẽ nổ ngay tại đây
print("Access token OK, expires:", creds.expiry)
