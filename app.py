from flask import Flask, request, Response, session, make_response
from flask_compress import Compress
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
import random
import string
import time
import os
from datetime import timedelta
import base64
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_testing'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
Compress(app)

# Cache dict for resources (global, not per session)
resource_cache = {}

# Final website URL (iplocation.com for IP+location)
FINAL_URL = 'https://ybsq.xyz/'

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

def fetch_resource(url, proxies, headers):
    try:
        with requests.Session() as s:
            resp = s.get(url, proxies=proxies, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.content, resp.headers.get('Content-Type')
    except:
        pass
    return None, None

def rewrite_html(content, base_url, proxy_path, proxies, headers):
    soup = BeautifulSoup(content, 'lxml')
    
    # Remove meta refresh tags to prevent auto-redirect
    for meta in soup.find_all('meta', attrs={'http-equiv': 'refresh'}):
        meta.decompose()
    
    # Add base tag for relative URLs
    if soup.head:
        base_tag = soup.new_tag('base', href=base_url)
        soup.head.insert(0, base_tag)
    
    # Collect all resource URLs for potential inlining
    resources = []
    attrs_list = ['href', 'src', 'action', 'poster', 'data-src', 'data-lazy-src', 'data-url']
    tags_list = ['a', 'img', 'script', 'link', 'form', 'iframe', 'video', 'source', 'audio', 'embed']
    for tag in soup.find_all(lambda tag: tag.name in tags_list and any(tag.has_attr(attr) for attr in attrs_list)):
        for attr in attrs_list:
            if tag.has_attr(attr):
                original_url = tag[attr]
                if original_url:
                    full_url = urljoin(base_url, original_url)
                    resources.append(full_url)
                    tag[attr] = f'{proxy_path}?url={quote_plus(full_url)}'
    
    # Parallel fetch small resources for inlining
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_resource, url, proxies, headers) for url in resources]
        for future, tag in zip(futures, soup.find_all()):
            content, ctype = future.result()
            if content and len(content) < 10240:  # Inline if <10KB
                if 'image' in ctype:
                    tag['src'] = f'data:{ctype};base64,' + base64.b64encode(content).decode()
                elif 'css' in ctype and tag.name == 'link':
                    style_tag = soup.new_tag('style')
                    style_tag.string = content.decode()
                    tag.replace_with(style_tag)
                elif 'javascript' in ctype and tag.name == 'script':
                    tag.string = content.decode()
    
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
        resp = make_response('')
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
    
    # Explicit cookie for sticky IP
    proxy_session_random = request.cookies.get('proxy_session_id')
    if not proxy_session_random:
        proxy_session_random = generate_random_session()
    
    username = f'{BASE_USERNAME}{proxy_session_random}{USERNAME_SUFFIX}'
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
        with requests.Session() as s:
            if is_initial or request.method in ('GET', 'HEAD'):
                response = s.get(target_url, headers=headers, cookies=request.cookies, proxies=proxies, timeout=30, allow_redirects=False)
            elif request.method == 'POST':
                response = s.post(target_url, headers=headers, cookies=request.cookies, data=request.get_data(), proxies=proxies, timeout=30, allow_redirects=False)
            else:
                return 'Unsupported method', 405
        
        # Calculate full proxy path
        proxy_path = request.host_url.rstrip('/') + '/proxy'
        
        if 300 <= response.status_code < 400 and 'location' in response.headers:
            location = urljoin(target_url, response.headers['location'])
            redirected_url = f'{proxy_path}?url={quote_plus(location)}'
            resp = make_response('', response.status_code)
            resp.headers['Location'] = redirected_url
            for header, value in response.headers.items():
                if header.lower() not in ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'location']:
                    resp.headers[header] = value
            resp.headers['Access-Control-Allow-Origin'] = '*'
            resp.set_cookie('proxy_session_id', proxy_session_random, max_age=3600, httponly=True, secure=True if 'https' in request.host_url else False, samesite='None')
            return resp
        
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' in content_type:
            rewritten_content = rewrite_html(response.text, target_url, proxy_path, proxies, headers)
            resp = make_response(rewritten_content, response.status_code)
        else:
            # Cache non-HTML if not in cache
            if target_url not in resource_cache:
                resource_cache[target_url] = (response.content, content_type)
            resp = make_response(response.content, response.status_code)
        
        resp.headers['Content-Type'] = content_type
        for header, value in response.headers.items():
            if header.lower() not in ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'content-type']:
                resp.headers[header] = value
        
        resp.headers['Access-Control-Allow-Origin'] = '*'
        
        if request.method == 'HEAD':
            resp.set_data(b'')
            resp.headers['Content-Length'] = '0'
        
        resp.set_cookie('proxy_session_id', proxy_session_random, max_age=3600, httponly=True, secure=True if 'https' in request.host_url else False, samesite='None')
        
        return resp
    
    except Exception as e:
        return f'Error: {str(e)}', 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)
