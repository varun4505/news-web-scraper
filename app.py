import requests
import feedparser
from bs4 import BeautifulSoup
from flask import Flask, render_template, jsonify, request, Response
from datetime import datetime, timedelta
import dateutil.parser
import concurrent.futures
import time
import re
import json
import os
import hashlib
from textblob import TextBlob
import threading
import queue

app = Flask(__name__)

# Cache configuration
# For Vercel serverless environment, use /tmp for cache as it's writable
# In local development, use the local cache directory
if os.environ.get('VERCEL_ENV'):
    CACHE_DIR = "/tmp/cache"
else:
    CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
    
CACHE_EXPIRY = 30  # minutes

# Maximum articles per source (set to None for unlimited)
MAX_ARTICLES_PER_SOURCE = 20

# Create cache directory if it doesn't exist
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# List of news sources to scrape from
NEWS_SOURCES = [
    # International Sources
    {
        "name": "NPR",
        "rss_url": "https://feeds.npr.org/1001/rss.xml",
        "base_url": "https://www.npr.org",
        "supports_direct_search": False,
        "region": "international"
    },
    {
        "name": "BBC News",
        "rss_url": "http://feeds.bbci.co.uk/news/rss.xml",
        "base_url": "https://www.bbc.com",
        "supports_direct_search": False,
        "region": "international"
    },
    {
        "name": "The Guardian",
        "rss_url": "https://www.theguardian.com/world/rss",
        "base_url": "https://www.theguardian.com",
        "supports_direct_search": False,
        "region": "international"
    },
    {
        "name": "CNN",
        "rss_url": "http://rss.cnn.com/rss/edition.rss",
        "base_url": "https://www.cnn.com",
        "supports_direct_search": False,
        "region": "international"
    },
    {
        "name": "New York Times",
        "rss_url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "base_url": "https://www.nytimes.com",
        "supports_direct_search": False,
        "region": "international"
    },
    {
        "name": "AFP",
        "rss_url": "https://www.afp.com/en/rss",
        "base_url": "https://www.afp.com",
        "supports_direct_search": False,
        "region": "international"
    },
    {
        "name": "Outlook",
        "rss_url": "https://www.outlookindia.com/rss",
        "base_url": "https://www.outlookindia.com",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "The Week",
        "rss_url": "https://www.theweek.in/rss/home.xml",
        "base_url": "https://www.theweek.in",
        "supports_direct_search": False,
        "region": "indian"
    },
    # Indian National Sources
    {
        "name": "The Hindu",
        "rss_url": "https://www.thehindu.com/news/feeder/default.rss",
        "base_url": "https://www.thehindu.com",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "NDTV",
        "rss_url": "https://feeds.feedburner.com/ndtvnews-top-stories",
        "base_url": "https://www.ndtv.com",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "Times of India",
        "rss_url": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
        "base_url": "https://timesofindia.indiatimes.com",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "The New Indian Express",
        "rss_url": "https://www.newindianexpress.com/feeds/rss/",
        "base_url": "https://www.newindianexpress.com",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "PTI",
        "rss_url": "https://www.ptinews.com/rss/rss.aspx?id=1",
        "base_url": "https://www.ptinews.com",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "UNI",
        "rss_url": "http://www.uniindia.com/rss-feeds/news/india/",
        "base_url": "http://www.uniindia.com",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "IANS",
        "rss_url": "https://ians.in/feeds/latest-news/",
        "base_url": "https://ians.in",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "ANI",
        "rss_url": "https://aninews.in/rss/latest-news/",
        "base_url": "https://aninews.in",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "Business Today",
        "rss_url": "https://www.businesstoday.in/rssfeeds/?id=1",
        "base_url": "https://www.businesstoday.in",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "India Today",
        "rss_url": "https://www.indiatoday.in/rss/1206514",
        "base_url": "https://www.indiatoday.in",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "Business World",
        "rss_url": "http://www.businessworld.in/rss-feed/",
        "base_url": "http://www.businessworld.in",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "Economic Times",
        "rss_url": "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
        "base_url": "https://economictimes.indiatimes.com",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "HT Mint",
        "rss_url": "https://www.livemint.com/rss/news",
        "base_url": "https://www.livemint.com",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "Business Standard",
        "rss_url": "https://www.business-standard.com/rss/home_page_top_stories.rss",
        "base_url": "https://www.business-standard.com",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "Financial Express",
        "rss_url": "https://www.financialexpress.com/feed/",
        "base_url": "https://www.financialexpress.com",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "Money Control",
        "rss_url": "https://www.moneycontrol.com/rss/latestnews.xml",
        "base_url": "https://www.moneycontrol.com",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "Your Story",
        "rss_url": "https://yourstory.com/feed",
        "base_url": "https://yourstory.com",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "Inc42",
        "rss_url": "https://inc42.com/feed/",
        "base_url": "https://inc42.com",
        "supports_direct_search": False,
        "region": "indian"
    },
    # Telangana & AP Sources
    {
        "name": "Deccan Chronicle",
        "rss_url": "https://www.deccanchronicle.com/rss_feed/",
        "base_url": "https://www.deccanchronicle.com",
        "supports_direct_search": False,
        "region": "telangana-ap"
    },
    {
        "name": "Telangana Today",
        "rss_url": "https://telanganatoday.com/feed",
        "base_url": "https://telanganatoday.com",
        "supports_direct_search": False,
        "region": "telangana-ap"
    },
    {
        "name": "The Hans India",
        "rss_url": "https://www.thehansindia.com/rss/top-stories",
        "base_url": "https://www.thehansindia.com",
        "supports_direct_search": False,
        "region": "telangana-ap"
    },
    {
        "name": "Sakshi",
        "rss_url": "https://www.sakshi.com/rss.xml",
        "base_url": "https://www.sakshi.com",
        "supports_direct_search": False,
        "region": "telangana-ap"
    },
    {
        "name": "Eenadu",
        "rss_url": "https://www.eenadu.net/rss-feeds/top-stories",
        "base_url": "https://www.eenadu.net",
        "supports_direct_search": False,
        "region": "telangana-ap"
    },
    {
        "name": "Andhra Jyothi",
        "rss_url": "https://www.andhrajyothy.com/rss/rss.aspx",
        "base_url": "https://www.andhrajyothy.com",
        "supports_direct_search": False,
        "region": "telangana-ap"
    },
    {
        "name": "Namaste Telangana",
        "rss_url": "https://ntnews.com/rss-feed",
        "base_url": "https://ntnews.com",
        "supports_direct_search": False,
        "region": "telangana-ap"
    },
    {
        "name": "Prajashakti",
        "rss_url": "http://www.prajashakti.com/rss/rss.xml",
        "base_url": "http://www.prajashakti.com",
        "supports_direct_search": False,
        "region": "telangana-ap"
    },
    {
        "name": "The Metro India",
        "rss_url": "https://themetro.in/feed/",
        "base_url": "https://themetro.in",
        "supports_direct_search": False,
        "region": "telangana-ap"
    },
    {
        "name": "The Pioneer",
        "rss_url": "https://www.dailypioneer.com/rss/top-stories.xml",
        "base_url": "https://www.dailypioneer.com",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "Bizz Buzz",
        "rss_url": "https://www.bizzbuzz.news/feed/",
        "base_url": "https://www.bizzbuzz.news",
        "supports_direct_search": False,
        "region": "indian"
    },
    {
        "name": "Free Press Journal",
        "rss_url": "https://www.freepressjournal.in/cmlink/1.0.671503",
        "base_url": "https://www.freepressjournal.in",
        "supports_direct_search": False,
        "region": "indian"
    }
]

def analyze_sentiment(text):
    """Analyze the sentiment of a text using TextBlob"""
    if not text:
        return {
            "polarity": 0,
            "sentiment": "neutral",
            "confidence": 0
        }
    
    analysis = TextBlob(text)
    polarity = analysis.sentiment.polarity
    
    # Determine sentiment category
    if polarity > 0.1:
        sentiment = "positive"
    elif polarity < -0.1:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    
    # Calculate confidence (0-100%)
    confidence = min(abs(polarity) * 100, 100)
    
    return {
        "polarity": round(polarity, 2),
        "sentiment": sentiment,
        "confidence": round(confidence, 1)
    }

def fetch_news_from_source(source, keyword=None):
    """Fetch news articles from a given RSS feed source with optional keyword filtering"""
    try:
        # feedparser doesn't support timeout parameter
        feed = feedparser.parse(source["rss_url"])
        
        # Check if the feed was successfully parsed
        if hasattr(feed, 'bozo_exception') and feed.bozo_exception:
            print(f"Warning parsing {source['name']}: {str(feed.bozo_exception)}")
        
        articles = []
        
        # Use the configured maximum articles per source (None means no limit)
        max_entries = MAX_ARTICLES_PER_SOURCE if MAX_ARTICLES_PER_SOURCE is not None else len(feed.entries)
        for entry in feed.entries[:max_entries]:
            article = {
                "title": entry.get("title", "No title"),
                "publisher": source["name"],
                "source_link": entry.get("link", ""),
                "description": "",
                "author": "",
                "published_date": "",
                "sentiment": {},
                "region": source.get("region", "international")
            }
            
            # Try to extract description
            if hasattr(entry, "summary"):
                soup = BeautifulSoup(entry.summary, "html.parser")
                article["description"] = soup.get_text().strip()
            
            # Try to extract author
            if hasattr(entry, "author"):
                article["author"] = entry.author
            
            # Try to extract published date with better error handling
            article["published_date"] = "Unknown"  # Default value
            
            # Try different date fields
            date_fields = ["published", "updated", "pubDate"]
            for field in date_fields:
                if article["published_date"] == "Unknown" and hasattr(entry, field) and getattr(entry, field):
                    try:
                        date = dateutil.parser.parse(getattr(entry, field))
                        article["published_date"] = date.strftime("%Y-%m-%d %H:%M:%S")
                        break
                    except Exception:
                        continue
            
            # If no date, use current time
            if article["published_date"] == "Unknown":
                article["published_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Try to fetch more details from the actual page
            try:
                if article["source_link"]:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml',
                        'Accept-Language': 'en-US,en;q=0.9'
                    }
                    # Add session with retry capability
                    session = requests.Session()
                    adapter = requests.adapters.HTTPAdapter(max_retries=2)
                    session.mount('http://', adapter)
                    session.mount('https://', adapter)
                    
                    # Use session with shorter timeout (connect_timeout, read_timeout)
                    response = session.get(article["source_link"], headers=headers, timeout=(3, 6))
                    
                    if response.status_code == 200:
                        page_soup = BeautifulSoup(response.text, "html.parser")
                        
                        # Try to get a better description if current one is too short
                        if len(article["description"]) < 100:
                            meta_desc = page_soup.find("meta", attrs={"name": "description"}) or \
                                       page_soup.find("meta", attrs={"property": "og:description"})
                            if meta_desc and meta_desc.get("content"):
                                article["description"] = meta_desc.get("content").strip()
                        
                        # Try to get author if not available
                        if not article["author"]:
                            author_elem = page_soup.find("meta", attrs={"name": "author"}) or \
                                         page_soup.find("meta", attrs={"property": "article:author"})
                            if author_elem and author_elem.get("content"):
                                article["author"] = author_elem.get("content").strip()
            except Exception as e:
                print(f"Error fetching details from {source['name']} article: {str(e)}")
            
            # Apply keyword filtering if provided
            if keyword:
                keyword = keyword.lower()
                if (keyword not in article["title"].lower() and 
                    keyword not in article["description"].lower() and 
                    (not article["author"] or keyword not in article["author"].lower())):
                    continue  # Skip this article as it doesn't match the keyword
            
            # Perform sentiment analysis on title and description
            analysis_text = article["title"] + " " + article["description"]
            article["sentiment"] = analyze_sentiment(analysis_text)
                
            articles.append(article)
        
        print(f"Fetched {len(articles)} articles from {source['name']}" + (f" with keyword '{keyword}'" if keyword else ""))
        return articles
    except Exception as e:
        print(f"Error fetching news from {source['name']}: {str(e)}")
        return []

def get_all_news(keyword=None, stream_queue=None):
    """Fetch news from all sources in parallel with optional keyword filtering
       If stream_queue is provided, articles from each source are added to the queue as they arrive
    """
    all_articles = []
    start_time = time.time()
    
    print(f"Fetching news from {len(NEWS_SOURCES)} sources" + (f" with keyword '{keyword}'" if keyword else ""))
    
    # Prepare the arguments for each source
    source_args = [(source, keyword) for source in NEWS_SOURCES]
    
    # Use concurrent.futures to fetch from multiple sources simultaneously
    # Limit max_workers to prevent overloading system and potential timeouts
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Use starmap-like approach since we need to pass multiple arguments
        futures = {executor.submit(fetch_news_from_source, source, keyword): source['name'] for source, keyword in source_args}
        
        # Process completed futures with more aggressive timeouts
        try:
            # Reduce timeout to avoid blocking too long - we'd rather have partial results than no results
            completed_count = 0
            for future in concurrent.futures.as_completed(list(futures.keys()), timeout=30):
                source_name = futures[future]
                try:
                    articles = future.result(timeout=5)  # 5 second timeout for getting result
                    completed_count += 1
                    
                    # Sort these articles by date before adding them
                    def safe_date_parser(date_str):
                        try:
                            if date_str and date_str != "Unknown":
                                return dateutil.parser.parse(date_str)
                            return datetime(1970, 1, 1)
                        except Exception:
                            return datetime(1970, 1, 1)
                    
                    try:
                        articles = sorted(
                            articles,
                            key=lambda x: safe_date_parser(x.get("published_date")),
                            reverse=True
                        )
                    except Exception:
                        pass  # If sorting fails, use unsorted articles
                    
                    # Add to the main list
                    all_articles.extend(articles)
                    
                    # If streaming, send these articles immediately
                    if stream_queue is not None and articles:
                        progress = {
                            "articles": articles,
                            "completed": completed_count,
                            "total": len(futures),
                            "source_name": source_name
                        }
                        stream_queue.put(progress)
                        
                    print(f"Fetched {len(articles)} articles from {source_name}")
                    
                except concurrent.futures.TimeoutError:
                    print(f"Timeout fetching from source {source_name}")
                except Exception as e:
                    print(f"Error processing source {source_name}: {str(e)}")
        except concurrent.futures.TimeoutError:
            print(f"Some news sources took too long to respond. Returning partial results.")
            # Cancel any outstanding futures to prevent hanging threads
            for future in futures:
                if not future.done():
                    future.cancel()
        except Exception as e:
            print(f"Unexpected error processing news sources: {str(e)}")
    
    # Sort all articles by published date (newest first) with better error handling
    def safe_date_parser(date_str):
        try:
            if date_str and date_str != "Unknown":
                return dateutil.parser.parse(date_str)
            return datetime(1970, 1, 1)
        except Exception:
            return datetime(1970, 1, 1)
    
    try:
        all_articles = sorted(
            all_articles, 
            key=lambda x: safe_date_parser(x.get("published_date")),
            reverse=True
        )
    except Exception as e:
        print(f"Error sorting articles: {str(e)}")
        # If sorting fails, return unsorted articles rather than nothing
    
    end_time = time.time()
    print(f"Fetched {len(all_articles)} articles in {end_time - start_time:.2f} seconds")
    
    # Send the final complete signal if streaming
    if stream_queue is not None:
        stream_queue.put({"complete": True, "total_articles": len(all_articles)})
    
    return all_articles

def get_cache_key(query_params=None):
    """Generate a cache key based on query parameters"""
    if query_params is None:
        query_params = {}
    
    key = "-".join([f"{k}={v}" for k, v in sorted(query_params.items())])
    return hashlib.md5(key.encode()).hexdigest()

def get_cached_news(cache_key):
    """Get cached news if available and not expired"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    if not os.path.exists(cache_file):
        return None
        
    file_mod_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
    if datetime.now() - file_mod_time > timedelta(minutes=CACHE_EXPIRY):
        return None  # Cache expired
        
    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading cache: {str(e)}")
        return None

def save_to_cache(cache_key, data):
    """Save news data to cache"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving to cache: {str(e)}")

def sort_articles(articles, sort_by="date"):
    """Sort articles based on criteria"""
    if sort_by == "date" or sort_by == "time":
        def safe_date_parser(article):
            try:
                if article.get("published_date") and article["published_date"] != "Unknown":
                    return dateutil.parser.parse(article["published_date"])
                return datetime(1970, 1, 1)
            except Exception:
                return datetime(1970, 1, 1)
                
        return sorted(
            articles,
            key=safe_date_parser,
            reverse=True
        )
    elif sort_by == "sentiment_positive":
        return sorted(
            articles,
            key=lambda x: x.get("sentiment", {}).get("polarity", 0),
            reverse=True
        )
    elif sort_by == "sentiment_negative":
        return sorted(
            articles,
            key=lambda x: x.get("sentiment", {}).get("polarity", 0),
            reverse=False
        )
    elif sort_by == "publisher":
        return sorted(
            articles,
            key=lambda x: x.get("publisher", "")
        )
    return articles

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/news/stream')
def api_news_stream():
    """Stream news articles as they are fetched in real-time"""
    keyword = request.args.get('keyword', '')
    
    def generate():
        # Create a queue for streaming updates
        q = queue.Queue()
        
        # Start a thread to fetch news and put results in the queue
        def fetch_thread():
            try:
                get_all_news(keyword=keyword if keyword else None, stream_queue=q)
            except Exception as e:
                print(f"Error in fetch thread: {str(e)}")
                q.put({"error": str(e)})
        
        threading.Thread(target=fetch_thread).start()
        
        # Keep yielding data from the queue until we get the complete signal
        while True:
            try:
                data = q.get(timeout=45)  # Wait up to 45 seconds for new data
                q.task_done()
                
                # If we got the complete signal, send it and stop
                if data.get("complete", False):
                    yield f"data: {json.dumps(data)}\n\n"
                    break
                
                # Otherwise stream the partial results
                yield f"data: {json.dumps(data)}\n\n"
            except queue.Empty:
                # If no data for 45 seconds, assume something went wrong
                yield f"data: {json.dumps({'error': 'Timeout waiting for news sources'})}\n\n"
                break
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/news')
def api_news():
    keyword = request.args.get('keyword', '')
    sort_by = request.args.get('sort', 'date')
    force_refresh = request.args.get('refresh', '').lower() == 'true'
    
    print(f"API request - keyword: '{keyword}', sort: '{sort_by}', force_refresh: {force_refresh}")
    
    # Create cache key based on query parameters
    query_params = {
        'keyword': keyword,
        'sort': sort_by
    }
    cache_key = get_cache_key(query_params)
    
    # Create response object
    response = None
    from_cache = False
    articles = []
    
    # Try to get news from cache unless force refresh
    if not force_refresh:
        cached_news = get_cached_news(cache_key)
        if cached_news:
            print(f"Serving {len(cached_news)} news articles from cache")
            articles = cached_news
            from_cache = True
    
    # If not from cache, fetch fresh news
    if not articles:
        print("Fetching fresh news...")
        # Fetch news with direct keyword search if provided
        articles = get_all_news(keyword if keyword else None)
        print(f"Fetched {len(articles)} fresh articles")
        
        # Only save to cache if we have articles
        if articles:
            save_to_cache(cache_key, articles)
    
    # Sort articles based on criteria
    articles = sort_articles(articles, sort_by)
    
    print(f"Returning {len(articles)} articles to client")
    response = jsonify(articles)
    
    # Add cache header
    response.headers['X-From-Cache'] = str(from_cache).lower()
    
    return response

if __name__ == '__main__':
    try:
        # Set up signal handling for graceful shutdown
        import signal
        import sys
        
        def signal_handler(sig, frame):
            print('Shutting down gracefully...')
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        
        # Start the Flask app
        print("Starting news scraper application...")
        print("Access the application at http://localhost:5000")
        app.run(debug=True, host='0.0.0.0')
    except KeyboardInterrupt:
        print("Keyboard interrupt received, exiting gracefully.")
    except Exception as e:
        print(f"Error in main thread: {str(e)}")
    finally:
        print("Cleaning up resources...")
        # Ensure all threads are terminated
        for thread in threading.enumerate():
            if thread != threading.current_thread():
                print(f"Waiting for thread {thread.name} to finish")
                thread.join(timeout=1.0)
        print("Shutdown complete.")
        
# This is for Vercel serverless deployment
# The app variable needs to be accessible directly
