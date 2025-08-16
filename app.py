from flask import Flask, request, Response, session
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
import random
import string
import time
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_testing'

# Final website URL (changed to https://www.whatismyip.com/ as requested)
FINAL_URL = 'https://www.whatismyip.com/'

# Spoofed Timezone and Offset for New York
SPOOFED_TIMEZONE = 'America/New_York'
SPOOFED_OFFSET = 240

# Spoofed Language
SPOOFED_LANGUAGE = 'en-US,en;q=0.9'

# Proxydize Proxy Setup
PROXY_HOST = 'pg.proxi.es'
PROXY_PORT = 20002
BASE_USERNAME = 'KMwYgm4pR4upF6yX-s-'
USERNAME_SUFFIX = '-co-USA-st-NY-ci-NewYorkCity'
PROXY_PASSWORD = 'pMBwu34BjjGr5urD'

def generate_random_session():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

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

# JS to override redirects, refreshes, and client-side requests
PROXY_JS_OVERRIDE = """
<script>
  (function() {{
    const originalFetch = window.fetch;
    window.fetch = function(url, options) {{
      if (typeof url === 'string') {{
        url = '/proxy?url=' + encodeURIComponent(url);
      }} else if (url instanceof Request) {{
        url = new Request('/proxy?url=' + encodeURIComponent(url.url), url);
      }}
      return originalFetch.call(this, url, options);
    }};

    const originalXHR = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {{
      url = '/proxy?url=' + encodeURIComponent(url);
      return originalXHR.call(this, method, url);
    }};

    Object.defineProperty(window.location, 'href', {{
      set: function(value) {{
        if (value !== window.location.href) {{
          value = '/proxy?url=' + encodeURIComponent(value);
          this._value = value;
        }}
      }},
      get: function() {{
        return this._value || window.location.href;
      }}
    }});

    document.addEventListener('DOMContentLoaded', function() {{
      const metas = document.querySelectorAll('meta[http-equiv="refresh"]');
      metas.forEach(meta => meta.remove());
    }});
  }})();
</script>
"""

SESSION_TIMEOUT = 50

def rewrite_html(content, base_url, proxy_path):
    soup = BeautifulSoup(content, 'lxml')
    
    # Remove meta refresh tags
    for meta in soup.find_all('meta', attrs={'http-equiv': 'refresh'}):
        meta.decompose()
    
    # Add base tag for relative URLs
    if soup.head:
        base_tag = soup.new_tag('base', href=base_url)
        soup.head.insert(0, base_tag)
    
    # Rewrite all links (expanded attrs)
    for tag in soup.find_all(['a', 'img', 'script', 'link', 'form', 'iframe', 'video', 'source', 'audio', 'embed'], attrs={'href': True, 'src': True, 'action': True, 'poster': True, 'data-src': True, 'data-lazy-src': True, 'data-url': True}):
        for attr in ['href', 'src', 'action', 'poster', 'data-src', 'data-lazy-src', 'data-url']:
            if tag.has_attr(attr):
                original_url = tag[attr]
                if original_url:
                    full_url = urljoin(base_url, original_url)
                    tag[attr] = f'{proxy_path}?url={quote_plus(full_url)}'
    
    # Inject timezone and proxy JS
    if soup.head:
        soup.head.insert(0, BeautifulSoup(TIMEZONE_SPOOF_JS + PROXY_JS_OVERRIDE, 'html.parser'))
    
    return str(soup)

@app.route('/proxy', methods=['GET', 'POST'])
def proxy():
    if 'last_activity' in session:
        if time.time() - session['last_activity'] > SESSION_TIMEOUT:
            session.clear()
            return 'Session expired due to inactivity. Please start again.', 403
    
    session['last_activity'] = time.time()

    if 'proxy_session_random' not in session:
        session['proxy_session_random'] = generate_random_session()
    
    random_session = session['proxy_session_random']

    username = f'{BASE_USERNAME}{random_session}{USERNAME_SUFFIX}'

    proxies = {
        'http': f'socks5://{username}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}',
        'https': f'socks5://{username}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}'
    }

    if request.method == 'POST':
        target_url = FINAL_URL
    else:
        target_url = request.args.get('url')
        if not target_url:
            return 'No URL provided', 400
    
    headers = {
        'User-Agent': request.headers.get('User-Agent', 'Unknown'),
        'Accept': request.headers.get('Accept'),
        'Accept-Language': SPOOFED_LANGUAGE,
        'Referer': request.headers.get('Referer'),
    }
    
    try:
        response = requests.get(target_url, headers=headers, cookies=request.cookies, proxies=proxies, timeout=30)
        
        if 'text/html' in response.headers.get('Content-Type', ''):
            rewritten_content = rewrite_html(response.text, target_url, '/proxy')
            resp = Response(rewritten_content, status=response.status_code, content_type=response.headers['Content-Type'])
        else:
            resp = Response(response.content, status=response.status_code, content_type=response.headers['Content-Type'])
        
        return resp
    
    except Exception as e:
        return f'Error: {str(e)}', 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)
