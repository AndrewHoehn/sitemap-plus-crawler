# sitemap-plus-crawler
This Python script combines XML sitemap parsing with web crawling to create a comprehensive site inventory. It extracts URLs from XML sitemaps and crawls the website to find additional pages that might be missing from the sitemap. For each URL found, it collects the page title, meta description, and first H1 heading.

## Features

- Parses XML sitemaps (including sitemap index files)
- Crawls websites to find additional URLs not in sitemaps
- Normalizes URLs to prevent duplicates
- Processes PDF files to extract metadata
- Handles both www and non-www domain versions
- Exports results to CSV
- Shows progress with a dynamic progress bar
- Respects server load with built-in delays

## Requirements

```bash
pip install requests beautifulsoup4 tqdm PyPDF2
```

## Usage

```bash
python sitemap_crawler.py
```

The script will prompt you for:
1. The domain to crawl (e.g., https://example.com)
2. The output filename for the CSV

## Output Format

The script generates a CSV file with the following columns:
- URL
- Meta Title
- Meta Description
- First H1

## How It Works

1. **Sitemap Detection**: Checks common locations for XML sitemaps:
   - /sitemap_index.xml
   - /sitemap.xml
   - /sitemap-index.xml
   - /wp-sitemap.xml
   - /sitemaps.xml

2. **URL Collection**: Gathers URLs from:
   - All found XML sitemaps
   - Website crawling
   - PDF documents

3. **URL Normalization**: Standardizes URLs by:
   - Converting to lowercase
   - Removing trailing slashes
   - Standardizing www/non-www versions
   - Removing fragments and query parameters

4. **Data Collection**: For each URL, captures:
   - Page title (meta title)
   - Meta description
   - First H1 heading
   - PDF metadata (for PDF files)

## Example Output

```csv
URL,Meta Title,Meta Description,First H1
https://www.example.com/,Homepage,Site description,Welcome
https://www.example.com/about,About Us,About our company,About Us
https://www.example.com/document.pdf,Document Title,PDF Document,PDF Document
```

## Notes

- The script includes a 1-second delay between requests to be respectful to servers
- URLs ending in .jpg, .jpeg, .png, .gif, and .zip are excluded
- PDF files are processed to extract available metadata
- Progress is displayed in real-time with a progress bar
- Final statistics show URLs from sitemaps vs. additionally discovered URLs

## Error Handling

- Invalid URLs are skipped
- Failed requests are logged but don't stop the process
- PDF processing errors are caught and logged

## Contributing

Feel free to submit issues and enhancement requests!
