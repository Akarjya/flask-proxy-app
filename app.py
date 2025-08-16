from flask import Flask, request, Response, session, make_response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
import random
import string
import time
import os
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_testing'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Final website URL
FINAL_URL = 'https://www.iplocation.net/'

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
    window.location.replace = function(url) {{
      url = '/proxy?url=' + encodeURIComponent(url);
      this.href = url;
    }};
    window.location.assign = function(url) {{
      url = '/proxy?url=' + encodeURIComponent(url);
      this.href = url;
    }};
    window.location.reload = function() {{
      console.log('Reload blocked by proxy');
      return;
    }};
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
    
    # Remove meta refresh tags to prevent auto-redirect
    for meta in soup.find_all('meta', attrs={'http-equiv': 'refresh'}):
        meta.decompose()
    
    # Add base tag for relative URLs
    if soup.head:
        base_tag = soup.new_tag('base', href=base_url)
        soup.head.insert(0, base_tag)
    
    # Rewrite all possible links (fixed to match tags with ANY of the attrs)
    attrs_list = ['href', 'src', 'action', 'poster', 'data-src', 'data-lazy-src', 'data-url']
    tags_list = ['a', 'img', 'script', 'link', 'form', 'iframe', 'video', 'source', 'audio', 'embed']
    for tag in soup.find_all(lambda tag: tag.name in tags_list and any(tag.has_attr(attr) for attr in attrs_list)):
        for attr in attrs_list:
            if tag.has_attr(attr):
                original_url = tag[attr]
                if original_url:
                    full_url = urljoin(base_url, original_url)
                    tag[attr] = f'{proxy_path}?url={quote_plus(full_url)}'
    
    # Inject timezone and proxy JS override
    if soup.head:
        soup.head.insert(0, BeautifulSoup(TIMEZONE_SPOOF_JS + PROXY_JS_OVERRIDE, 'html.parser'))
    
    return str(soup)

@app.route('/', methods=['GET'])
def home():
    return "Proxy app is live. Go to /proxy to access the site."

@app.route('/proxy', methods=['GET', 'POST', 'HEAD', 'OPTIONS'])
def proxy():
    if request.method == 'OPTIONS':
        resp = Response('')
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, HEAD, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return resp

    session.permanent = True
    if 'last_activity' in session:
        if time.time() - session['last_activity'] > SESSION_TIMEOUT:
            session.clear()
            return 'Session expired due to inactivity. Please start again.', 403
    
    session['last_activity'] = time.time()
    
    if 'proxy_session_random' not in session:
        session['proxy_session_random'] = generate_random_session()
        session.modified = True
    
    random_session = session['proxy_session_random']
    username = f'{BASE_USERNAME}{random_session}{USERNAME_SUFFIX}'
    proxies = {
        'http': f'socks5://{username}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}',
        'https': f'socks5://{username}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}'
    }
    
    target_url = request.args.get('url')
    is_initial = False
    if not target_url:
        target_url = FINAL_URL
        is_initial = True
    
    headers = {
        'User-Agent': request.headers.get('User-Agent', 'Unknown'),
        'Accept': request.headers.get('Accept'),
        'Accept-Language': SPOOFED_LANGUAGE,
        'Referer': request.headers.get('Referer'),
    }
    
    try:
        if is_initial or request.method in ('GET', 'HEAD'):
            response = requests.get(target_url, headers=headers, cookies=request.cookies, proxies=proxies, timeout=30, allow_redirects=False)
        elif request.method == 'POST':
            response = requests.post(target_url, headers=headers, cookies=request.cookies, data=request.get_data(), proxies=proxies, timeout=30, allow_redirects=False)
        else:
            return 'Unsupported method', 405
        
        # Calculate full proxy path
        proxy_path = request.host_url.rstrip('/') + '/proxy'
        
        if 300 <= response.status_code < 400 and 'location' in response.headers:
            location = urljoin(target_url, response.headers['location'])
            redirected_url = f'{proxy_path}?url={quote_plus(location)}'
            resp = Response('', status=response.status_code)
            resp.headers['Location'] = redirected_url
            for header, value in response.headers.items():
                if header.lower() not in ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'location']:
                    resp.headers[header] = value
            resp.headers['Access-Control-Allow-Origin'] = '*'
            return resp
        
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' in content_type:
            rewritten_content = rewrite_html(response.text, target_url, proxy_path)
            resp = Response(rewritten_content, status=response.status_code)
        else:
            resp = Response(response.content, status=response.status_code)
        
        resp.headers['Content-Type'] = content_type
        for header, value in response.headers.items():
            if header.lower() not in ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'content-type']:
                resp.headers[header] = value
        
        resp.headers['Access-Control-Allow-Origin'] = '*'
        
        if request.method == 'HEAD':
            resp.set_data(b'')
            resp.headers['Content-Length'] = '0'
        
        return resp
    
    except Exception as e:
        return f'Error: {str(e)}', 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)
