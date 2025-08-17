from flask import Flask, request, Response, session, make_response, redirect
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
import random
import string
import time
import os
import base64
from datetime import timedelta
from flask_compress import Compress
from flask_caching import Cache
from concurrent.futures import ThreadPoolExecutor, as_completed
app = Flask(__name__)
app.secret_key = 'super_secret_key_for_testing'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 30 # Shorter for HTML
cache = Cache(app)
Compress(app)
# Final website URL (your WordPress site)
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
    return ''.join(random.choices(string.digits, k=8))
# Use % formatting, removed outer <script> tags
TIMEZONE_SPOOF_JS = """
  (function() {
    console.log('Timezone spoof loaded');
    const originalDateTimeFormat = Intl.DateTimeFormat;
    Intl.DateTimeFormat = function(...args) {
      const dtf = new originalDateTimeFormat(...args);
      const originalResolvedOptions = dtf.resolvedOptions;
      dtf.resolvedOptions = function() {
        const options = originalResolvedOptions.call(dtf);
        options.timeZone = '%s';
        options.locale = 'en-US';
        options.calendar = 'gregory';
        options.numberingSystem = 'latn';
        return options;
      };
      return dtf;
    };
    Date.prototype.getTimezoneOffset = function() {
      return %d;
    };
    // Additional Intl spoofs
    const originalNumberFormat = Intl.NumberFormat;
    Intl.NumberFormat = function(...args) {
      const nf = new originalNumberFormat(...args);
      const originalResolvedOptions = nf.resolvedOptions;
      nf.resolvedOptions = function() {
        const options = originalResolvedOptions.call(nf);
        options.locale = 'en-US';
        return options;
      };
      return nf;
    };
    const originalPluralRules = Intl.PluralRules;
    Intl.PluralRules = function(...args) {
      const pr = new originalPluralRules(...args);
      const originalResolvedOptions = pr.resolvedOptions;
      pr.resolvedOptions = function() {
        const options = originalResolvedOptions.call(pr);
        options.locale = 'en-US';
        return options;
      };
      return pr;
    };
  })();
""" % (SPOOFED_TIMEZONE, SPOOFED_OFFSET)
PROXY_JS_OVERRIDE = """
  console.log('Proxy JS override loaded');
  (function() {
    const proxyBase = window.location.origin + '/proxy?session_id=' + PROXY_SESSION_ID + '&url=';
    const spoofedLang = 'en-US,en;q=0.9';
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
      console.log('Intercepted fetch to:', url);
      if (typeof url === 'string' && !url.startsWith(proxyBase)) {
        url = proxyBase + encodeURIComponent(url);
      } else if (url instanceof Request && !url.url.startsWith(proxyBase)) {
        url = new Request(proxyBase + encodeURIComponent(url.url), url);
      }
      if (!options.headers) options.headers = {};
      options.headers['Accept-Language'] = spoofedLang;
      return originalFetch.call(this, url, options);
    };
    const originalXHR = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {
      console.log('Intercepted XHR to:', url);
      if (!url.startsWith(proxyBase)) {
        url = proxyBase + encodeURIComponent(url);
      }
      const originalSetHeader = this.setRequestHeader;
      this.setRequestHeader = function(name, value) {
        if (name === 'Accept-Language') value = spoofedLang;
        return originalSetHeader.call(this, name, value);
      };
      return originalXHR.call(this, method, url);
    };
    const originalSendBeacon = navigator.sendBeacon;
    navigator.sendBeacon = function(url, data) {
      console.log('Intercepted sendBeacon to:', url);
      if (!url.startsWith(proxyBase)) {
        url = proxyBase + encodeURIComponent(url);
      }
      return originalSendBeacon.call(navigator, url, data);
    };
    window.location.replace = function(url) {
      console.log('Intercepted location.replace to:', url);
      if (!url.startsWith(proxyBase)) {
        url = proxyBase + encodeURIComponent(url);
      }
      return this.href = url;
    };
    window.location.assign = function(url) {
      console.log('Intercepted location.assign to:', url);
      if (!url.startsWith(proxyBase)) {
        url = proxyBase + encodeURIComponent(url);
      }
      return this.href = url;
    };
    window.location.reload = function() {
      console.log('Reload blocked by proxy');
      return;
    };
    // Spoof navigator.language and languages
    Object.defineProperty(navigator, 'language', {
      get: function() {
        return 'en-US';
      }
    });
    Object.defineProperty(navigator, 'languages', {
      get: function() {
        return ['en-US', 'en'];
      }
    });
    // Also spoof userLanguage if checked
    Object.defineProperty(navigator, 'userLanguage', {
      get: function() {
        return 'en-US';
      }
    });
    // Intercept dynamic script and iframe src
    const originalCreateElement = document.createElement.bind(document);
    document.createElement = function(tagName) {
      const elem = originalCreateElement(tagName);
      const tagLower = tagName.toLowerCase();
      if (tagLower === 'script' || tagLower === 'iframe') {
        Object.defineProperty(elem, 'src', {
          get: function() {
            return this.getAttribute('src');
          },
          set: function(value) {
            if (value && typeof value === 'string' && !value.startsWith(proxyBase)) {
              console.log('Intercepted ' + tagLower + ' src set:', value);
              value = proxyBase + encodeURIComponent(value);
            }
            this.setAttribute('src', value);
          },
          enumerable: true,
          configurable: true
        });
      }
      return elem;
    };
    document.addEventListener('DOMContentLoaded', function() {
      const metas = document.querySelectorAll('meta[http-equiv="refresh"]');
      metas.forEach(meta => meta.remove());
      // Keep-alive ping every 30 sec to prevent idle IP change
      setInterval(() => {
        fetch(proxyBase + encodeURIComponent('https://ybsq.xyz/'), { method: 'HEAD' }).catch(() => {});
      }, 30000);
    });
  })();
"""
SESSION_TIMEOUT = 300
def fetch_asset(url, proxy_session, headers):
    try:
        resp = proxy_session.get(url, headers=headers, timeout=10, verify=False)
        if resp.status_code == 200 and len(resp.content) < 10240: # <10KB
            return resp.text, resp.headers.get('Content-Type', '')
        return None, None
    except:
        return None, None
def rewrite_html(content, base_url, proxy_path, proxy_session_random, proxy_session, headers, nonce):
    soup = BeautifulSoup(content, 'lxml')
   
    # Remove meta refresh and CSP meta
    for meta in soup.find_all('meta', attrs={'http-equiv': lambda x: x and x.lower() in ['refresh', 'content-security-policy']}):
        meta.decompose()
   
    # Collect small assets for inlining
    to_inline = []
    for tag in soup.find_all(['link', 'script']):
        if tag.name == 'link' and tag.get('rel') == ['stylesheet'] and tag.get('href'):
            full_url = urljoin(base_url, tag['href'])
            to_inline.append((tag, full_url, 'css'))
        elif tag.name == 'script' and tag.get('src'):
            full_url = urljoin(base_url, tag['src'])
            to_inline.append((tag, full_url, 'js'))
   
    # Parallel fetch with larger pool
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_asset, item[1], proxy_session, headers): item for item in to_inline}
        for future in as_completed(futures):
            tag, _, typ = futures[future]
            data, ctype = future.result()
            if data:
                if typ == 'css':
                    style = soup.new_tag('style')
                    style.string = data
                    tag.replace_with(style)
                elif typ == 'js':
                    script = soup.new_tag('script')
                    script.string = data
                    tag.replace_with(script)
   
    # Rewrite remaining links
    attrs_list = ['href', 'src', 'action', 'poster', 'data-src', 'data-lazy-src', 'data-url']
    tags_list = ['a', 'img', 'script', 'link', 'form', 'iframe', 'video', 'source', 'audio', 'embed']
    for tag in soup.find_all(lambda tag: tag.name in tags_list and any(tag.has_attr(attr) for attr in attrs_list)):
        for attr in attrs_list:
            if tag.has_attr(attr):
                original_url = tag[attr]
                if original_url:
                    full_url = urljoin(base_url, original_url)
                    tag[attr] = f'{proxy_path}?session_id={proxy_session_random}&url={quote_plus(full_url)}'
   
    # Set html lang to en-US for better language detection
    if soup.html:
        soup.html['lang'] = 'en-US'
   
    # Add nonce to all script tags (inline and src)
    for script in soup.find_all('script'):
        script['nonce'] = nonce
   
    # Inject scripts with nonce
    if soup.head:
        session_script = soup.new_tag('script')
        session_script['nonce'] = nonce
        session_script.string = f"const PROXY_SESSION_ID = '{proxy_session_random}';"
        soup.head.insert(0, session_script)
       
        timezone_script = soup.new_tag('script')
        timezone_script['nonce'] = nonce
        timezone_script.string = TIMEZONE_SPOOF_JS
        soup.head.insert(1, timezone_script)
       
        proxy_script = soup.new_tag('script')
        proxy_script['nonce'] = nonce
        proxy_script.string = PROXY_JS_OVERRIDE
        soup.head.insert(2, proxy_script)
   
    return str(soup)
@app.route('/', methods=['GET'])
def home():
    return "Proxy app is live. Go to /proxy to access the site."
@app.route('/favicon.ico', methods=['GET'])
def favicon():
    return '', 204  # No content for favicon to avoid 404
@app.route('/proxy', methods=['GET', 'POST', 'HEAD', 'OPTIONS'])
def proxy():  # Removed cache to avoid nonce issues
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
   
    session['last_activity'] = time.time()
   
    proxy_session_random = request.args.get('session_id')
    if not proxy_session_random:
        proxy_session_random = request.cookies.get('proxy_session_id')
    if not proxy_session_random:
        proxy_session_random = generate_random_session()
   
    target_url = request.args.get('url')
    is_initial = not target_url
   
    if is_initial and not request.args.get('session_id'):
        redirect_url = f'/proxy?session_id={proxy_session_random}&url={quote_plus(FINAL_URL)}'
        return redirect(redirect_url, code=302)
   
    username = f'{BASE_USERNAME}{proxy_session_random}{USERNAME_SUFFIX}'
    proxies = {
        'http': f'socks5h://{username}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}',
        'https': f'socks5h://{username}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}'
    }
   
    # Get or create persistent session
    if proxy_session_random not in proxy_sessions:
        proxy_sessions[proxy_session_random] = requests.Session()
    proxy_session = proxy_sessions[proxy_session_random]
    proxy_session.proxies = proxies
   
    headers = {
        'User-Agent': request.headers.get('User-Agent', 'Unknown'),
        'Accept': request.headers.get('Accept'),
        'Accept-Language': SPOOFED_LANGUAGE,
        'Referer': request.headers.get('Referer'),
    }
   
    try:
        if request.method in ('GET', 'HEAD'):
            response = proxy_session.get(target_url, headers=headers, cookies=request.cookies, timeout=60, allow_redirects=False, verify=False)
        elif request.method == 'POST':
            response = proxy_session.post(target_url, headers=headers, cookies=request.cookies, data=request.get_data(), timeout=60, allow_redirects=False, verify=False)
        else:
            return 'Unsupported method', 405
       
        proxy_path = request.host_url.rstrip('/') + '/proxy'
       
        if 300 <= response.status_code < 400 and 'location' in response.headers:
            location = urljoin(target_url, response.headers['location'])
            redirected_url = f'{proxy_path}?session_id={proxy_session_random}&url={quote_plus(location)}'
            resp = make_response('', response.status_code)
            resp.headers['Location'] = redirected_url
            for header, value in response.headers.items():
                if header.lower() not in ['content-encoding', 'content-length', 'transfer-encoding', 'connection', 'location']:
                    resp.headers[header] = value
            resp.headers['Access-Control-Allow-Origin'] = '*'
            resp.set_cookie('proxy_session_id', proxy_session_random, max_age=3600, httponly=True, secure=True if 'https' in request.host_url else False, samesite='None')
            return resp
       
        content_type = response.headers.get('Content-Type', '')
        nonce = base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8').rstrip('=')
        if 'text/html' in content_type:
            rewritten_content = rewrite_html(response.text, target_url, proxy_path, proxy_session_random, proxy_session, headers, nonce)
            resp = make_response(rewritten_content, response.status_code)
            # Set CSP with nonce for scripts, added unsafe-inline for AdSense compatibility
            resp.headers['Content-Security-Policy'] = f"script-src 'nonce-{nonce}' 'unsafe-inline' 'unsafe-eval' 'strict-dynamic' https: http:; connect-src *; img-src * data: blob:; frame-src https: http:; object-src 'none'; base-uri 'none';"
        else:
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
proxy_sessions = {} # Global dict for sessions
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)
