import json
import base64
from urllib.parse import urlparse, parse_qs
import sys

def decode_jwt_payload(jwt):
    try:
        parts = jwt.split('.')
        if len(parts) >= 2:
            payload = parts[1]
            missing_padding = len(payload) % 4
            if missing_padding:
                payload += '=' * (4 - missing_padding)
            return json.loads(base64.b64decode(payload).decode('utf-8'))
    except Exception as e:
        print(f"Error decoding JWT: {e}")
    return {}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 parse_url.py <URL>")
        sys.exit(1)
        
    url = sys.argv[1]
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    auth_token_raw = params.get('auth_token', [None])[0]
    if auth_token_raw:
        payload = decode_jwt_payload(auth_token_raw)
        inner_token = payload.get('token')
        if inner_token:
            session_data = {
                'jwtToken': inner_token,
                'feedToken': params.get('feed_token', [None])[0],
                'refreshToken': params.get('refresh_token', [None])[0]
            }
            with open('tokens.json', 'w') as f:
                json.dump(session_data, f)
            print("Successfully updated tokens.json")
        else:
            # Maybe the auth_token itself is the jwtToken?
            session_data = {
                'jwtToken': auth_token_raw,
                'feedToken': params.get('feed_token', [None])[0],
                'refreshToken': params.get('refresh_token', [None])[0]
            }
            with open('tokens.json', 'w') as f:
                json.dump(session_data, f)
            print("Successfully updated tokens.json (using raw auth_token)")
    else:
        print("auth_token not found in URL.")
