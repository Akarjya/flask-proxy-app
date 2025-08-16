from flask import Flask, request, Response, session
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
import random
import string
import time
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_testing'  # Testing ke liye, baad mein random change karo

# Final website URL (testing ke liye IP check site daala, baad mein change karo apne site pe)
FINAL_URL = 'https://www.whatismyip.com/'

# Spoofed Timezone and Offset for New York (EDT in August: UTC-4, offset 240)
SPOOFED_TIMEZONE = 'America/New_York'
SPOOFED_OFFSET = 240  # getTimezoneOffset returns positive for west of UTC

# Spoofed Language
SPOOFED_LANGUAGE = 'en-US,en;q=0.9'

# Proxydize Proxy Setup (tumhare examples se liya)
PROXY_HOST = 'pg.proxi.es'
PROXY_PORT = 20002
BASE_USERNAME = 'KMwYgm4pR4upF6yX-s-'
USERNAME_SUFFIX = '-co-USA-st-NY-ci-NewYorkCity'
PROXY_PASSWORD = 'pMBwu34BjjGr5urD'  # Sab examples mein same

# Function to generate random 10-char alphanum string for sticky session (uppercase letters + digits jaise examples)
def generate_random_session():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

# JS code to spoof timezone
TIMEZONE_SPOOF_JS = f"""
<script>
  (function() {{
    const originalDateTimeFormat = Intl.DateTimeFormat;
    Intl.DateTimeFormat = function(...args) {{
      const dtf = new originalDateTimeFormat(...args);
      const originalResolvedOptions = dtf.resolvedOptions;
      dtf.resolvedOptions = function() {{
        const options = originalResolvedOptions.call(dtf);
        options.timeZone = '{SPOOFED_TIMEZONE}';
        return options;
      }};
      return dtf;
    }};

    Date.prototype.getTimezoneOffset = function() {{
      return {SPOOFED_OFFSET};
    }};
  }})();
</script>
"""

# Session timeout in seconds
SESSION_TIMEOUT = 50

def rewrite_html(content, base_url, proxy_path):
    soup = BeautifulSoup(content, 'lxml')
    
    # Rewrite all URLs
    for tag in soup.find_all(['a', 'img', 'script', 'link', 'form', 'iframe'], attrs={'href': True, 'src': True, 'action': True}):
        for attr in ['href', 'src', 'action']:
            if tag.has_attr(attr):
                original_url = tag[attr]
                if original_url:
                    full_url = urljoin(base_url, original_url)
                    tag[attr] = f'{proxy_path}?url={quote_plus(full_url)}'
    
    # Inject timezone spoof JS
    if soup.head:
        soup.head.insert(0, BeautifulSoup(TIMEZONE_SPOOF_JS, 'html.parser'))
    
    return str(soup)

@app.route('/proxy', methods=['GET', 'POST'])
def proxy():
    # Check session timeout and activity
    if 'last_activity' in session:
        if time.time() - session['last_activity'] > SESSION_TIMEOUT:
            session.clear()
            return 'Session expired due to inactivity. Please start again.', 403
    
    # Update last activity time
    session['last_activity'] = time.time()

    # Generate or get sticky session random string for proxy username (per user)
    if 'proxy_session_random' not in session:
        session['proxy_session_random'] = generate_random_session()
        session.modified = True  # Yeh add kiya session save hone ke liye

    random_session = session['proxy_session_random']

    # Construct username with random session for sticky
    username = f'{BASE_USERNAME}{random_session}{USERNAME_SUFFIX}'

    # Proxies with sticky (same IP for this user)
    proxies = {
        'http': f'http://{username}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}',
        'https': f'http://{username}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}'
    }

    # Determine target URL
    if request.method == 'POST':
        target_url = FINAL_URL  # From button click
    else:
        target_url = request.args.get('url')
        if not target_url:
            return 'No URL provided', 400
    
    # User real headers, but modify language
    headers = {
        'User-Agent': request.headers.get('User-Agent', 'Unknown'),
        'Accept': request.headers.get('Accept'),
        'Accept-Language': SPOOFED_LANGUAGE,  # Modified to New York English
        'Referer': request.headers.get('Referer'),
    }
    
    try:
        # Fetch via proxy (all work done here: proxy apply, changes, fetch)
        response = requests.get(target_url, headers=headers, cookies=request.cookies, proxies=proxies)
        
        # Rewrite if HTML (includes timezone JS change)
        if 'text/html' in response.headers.get('Content-Type', ''):
            rewritten_content = rewrite_html(response.text, target_url, '/proxy')
            return Response(rewritten_content, status=response.status_code, content_type=response.headers['Content-Type'])
        else:
            return Response(response.content, status=response.status_code, content_type=response.headers['Content-Type'])
    
    except Exception as e:
        return f'Error: {str(e)}', 500

import os  # For Render port

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)
