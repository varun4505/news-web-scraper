# Real-time News Scraper

A fast and free web scraper for fetching the latest news from multiple sources.

## Features

- Scrapes news articles from multiple reliable sources
- Extracts title, author name, publisher name, description, and source links
- Uses parallel requests for faster scraping
- Clean and responsive web interface
- Real-time refresh functionality

## Sources

Currently scrapes news from:
- Reuters
- NPR
- BBC News
- The Guardian

## Installation

### Local Installation

1. Clone this repository or download the files
2. Install the required dependencies:

```
pip install -r requirements.txt
```

3. Run the application:

```
python app.py
```

4. Open your browser and go to `http://localhost:5000`

### Deployment on Vercel

This project is configured for deployment on Vercel:

1. Create a GitHub repository and push your code to it:
```
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/news-scraper.git
git push -u origin main
```

2. Sign up for a Vercel account at https://vercel.com/

3. Import your GitHub repository in Vercel:
   - Go to the Vercel dashboard
   - Click "Add New" → "Project"
   - Select your GitHub repository
   - Keep the default settings and click "Deploy"

4. Your application will be deployed and available at a Vercel URL

## Customization

You can add more news sources by editing the `NEWS_SOURCES` list in `app.py`. Each source should have:
- name: The publisher name
- rss_url: URL to the RSS feed
- base_url: The base URL of the news site

## Technical Details

- Built with Flask
- Uses BeautifulSoup4 for HTML parsing
- Uses feedparser for RSS feed parsing
- Implements concurrent requests for faster scraping
- Responsive UI with Bootstrap

## License

This project is open source and available for personal use.
