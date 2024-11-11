import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import csv
import xml.etree.ElementTree as ET
from tqdm import tqdm
import time
import PyPDF2
from io import BytesIO

class SitemapCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.urls = set()  # URLs from sitemap
        self.crawled_urls = set()  # Additional URLs found during crawl
        self.visited_urls = set()  # All processed URLs
        self.data = {}  # Store data with normalized URL as key
        self.pbar = None
        self.domain = None

    def normalize_url(self, url):
        """Normalize URLs to prevent duplicates"""
        if not url:
            return None
            
        # Handle relative URLs
        if not url.startswith(('http://', 'https://')):
            url = urljoin(self.domain, url)
            
        try:
            parsed = urlparse(url)
            
            # Convert domain to lowercase
            netloc = parsed.netloc.lower()
            
            # Standardize www/non-www (choose www version)
            if not netloc.startswith('www.'):
                netloc = 'www.' + netloc
            
            # Clean up the path
            path = parsed.path
            if not path:
                path = '/'
            elif path != '/' and path.endswith('/'):
                path = path.rstrip('/')
                
            # Reconstruct URL without fragments and queries
            normalized = urlunparse((
                parsed.scheme,
                netloc,
                path,
                '',  # params
                '',  # query
                ''   # fragment
            ))
            
            return normalized
        except Exception as e:
            print(f"Error normalizing URL {url}: {str(e)}")
            return None

    def is_valid_url(self, url):
        """Check if URL belongs to target domain"""
        if not url:
            return False
            
        try:
            normalized_url = self.normalize_url(url)
            if not normalized_url:
                return False
                
            parsed_url = urlparse(normalized_url)
            parsed_domain = urlparse(self.domain)
            
            # Check if domains match and exclude certain file types
            return (parsed_url.netloc == parsed_domain.netloc and
                    not url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.zip')))
        except Exception as e:
            print(f"Error validating URL {url}: {str(e)}")
            return False

    def get_sitemap_locations(self, domain):
        """Try different common sitemap locations"""
        sitemap_locations = [
            f"{domain}/sitemap_index.xml",
            f"{domain}/sitemap.xml",
            f"{domain}/sitemap-index.xml",
            f"{domain}/wp-sitemap.xml",
            f"{domain}/sitemaps.xml"
        ]
        
        found_sitemaps = []
        for url in sitemap_locations:
            try:
                response = self.session.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200 and 'xml' in response.headers.get('content-type', ''):
                    found_sitemaps.append(url)
            except:
                continue
                
        return found_sitemaps

    def parse_sitemap(self, sitemap_url):
        """Parse a sitemap XML file and extract URLs"""
        try:
            response = self.session.get(sitemap_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            namespace = root.tag.split('}')[0] + '}'
            
            if 'sitemapindex' in root.tag:
                for sitemap in root.findall(f'.//{namespace}loc'):
                    self.parse_sitemap(sitemap.text)
            else:
                for url in root.findall(f'.//{namespace}loc'):
                    normalized_url = self.normalize_url(url.text)
                    if normalized_url:
                        self.urls.add(normalized_url)
                    
        except Exception as e:
            print(f"Error processing sitemap {sitemap_url}: {str(e)}")

    def get_pdf_data(self, url, response):
        """Extract metadata from PDF files"""
        try:
            pdf_file = BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Try to get PDF metadata
            meta_title = ''
            meta_description = ''
            
            if pdf_reader.metadata:
                meta_title = pdf_reader.metadata.get('/Title', '')
                meta_description = pdf_reader.metadata.get('/Subject', '')
            
            # If no title in metadata, use filename
            if not meta_title:
                meta_title = url.split('/')[-1]
            
            return {
                'url': url,
                'meta_title': meta_title,
                'meta_description': meta_description,
                'first_h1': 'PDF Document'
            }
            
        except Exception as e:
            print(f"Error processing PDF {url}: {str(e)}")
            return None

    def crawl_page(self, url):
        """Crawl a single page and return its data and found links"""
        try:
            response = self.session.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            links = set()
            
            # Handle PDFs
            if url.lower().endswith('.pdf'):
                return self.get_pdf_data(url, response), links
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract meta title
            meta_title = ''
            title_tag = soup.find('title')
            if title_tag:
                meta_title = title_tag.string.strip()
            
            # Extract meta description
            meta_description = ''
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag:
                meta_description = desc_tag.get('content', '').strip()
            
            # Extract first H1
            first_h1 = ''
            h1_tag = soup.find('h1')
            if h1_tag:
                first_h1 = h1_tag.get_text().strip()
            
            # Find all links on the page
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)
                if self.is_valid_url(absolute_url):
                    normalized_url = self.normalize_url(absolute_url)
                    if normalized_url:
                        links.add(normalized_url)
            
            return {
                'url': url,
                'meta_title': meta_title,
                'meta_description': meta_description,
                'first_h1': first_h1
            }, links
            
        except Exception as e:
            print(f"\nError crawling {url}: {str(e)}")
            return None, set()

    def process_url(self, url):
        """Process a URL and store its data"""
        normalized_url = self.normalize_url(url)
        if not normalized_url or normalized_url in self.visited_urls:
            return set()
            
        self.visited_urls.add(normalized_url)
        page_data, new_links = self.crawl_page(url)
        
        if page_data:
            self.data[normalized_url] = {
                'URL': normalized_url,
                'Meta Title': page_data['meta_title'],
                'Meta Description': page_data['meta_description'],
                'First H1': page_data['first_h1']
            }
            
        if self.pbar:
            self.pbar.update(1)
            
        return new_links - self.visited_urls

    def crawl(self, domain):
        """Main crawl process"""
        self.domain = self.normalize_url(domain)
        
        print("\nLooking for sitemaps...")
        sitemaps = self.get_sitemap_locations(domain)
        
        if sitemaps:
            print(f"Found {len(sitemaps)} sitemap(s)")
            for sitemap in sitemaps:
                print(f"Processing sitemap: {sitemap}")
                self.parse_sitemap(sitemap)
            print(f"\nFound {len(self.urls)} URLs in sitemaps")
        else:
            print("No sitemaps found, starting with homepage")
            self.urls.add(self.domain)
        
        # Initialize progress bar
        total_urls = len(self.urls)
        self.pbar = tqdm(total=total_urls, desc="Processing pages")
        
        # Process sitemap URLs first
        to_crawl = set()
        for url in self.urls:
            new_links = self.process_url(url)
            to_crawl.update(new_links)
        
        # Crawl additional discovered URLs
        while to_crawl:
            url = to_crawl.pop()
            new_links = self.process_url(url)
            to_crawl.update(new_links)
            
            # Update progress bar total for newly discovered URLs
            if self.pbar.total < len(self.visited_urls) + len(to_crawl):
                self.pbar.total = len(self.visited_urls) + len(to_crawl)
            
            time.sleep(1)  # Be nice to the server
        
        self.pbar.close()

    def save_sitemap(self, filename):
        """Save the collected data to a CSV file"""
        fieldnames = ['URL', 'Meta Title', 'Meta Description', 'First H1']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.data.values())

def main():
    # Get user input
    domain = input("Enter the domain to crawl (e.g., https://example.com): ").strip()
    filename = input("Enter the output filename (e.g., sitemap.csv): ").strip()
    
    if not filename.endswith('.csv'):
        filename += '.csv'

    # Initialize and run crawler
    print(f"\nInitializing crawler for {domain}")
    crawler = SitemapCrawler()
    crawler.crawl(domain)
    
    if crawler.data:
        # Save results
        print("\nSaving results...")
        crawler.save_sitemap(filename)
        print(f"\nSitemap has been saved to {filename}")
        print(f"Total pages processed: {len(crawler.data)}")
        print(f"Pages from sitemap: {len(crawler.urls)}")
        print(f"Additional pages found: {len(crawler.visited_urls) - len(crawler.urls)}")
    else:
        print("\nNo data collected!")

if __name__ == "__main__":
    main()