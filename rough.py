import pandas as pd
import requests
from bs4 import BeautifulSoup

url = "https://lawsikho.com/blog/ipc-to-bns-conversion-table/"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

# Find all table elements in the article
tables = soup.find_all("table")

scraped_tables = []

for index, table in enumerate(tables):
    headers_list = []
    # Extract headers (th)
    for th in table.find_all("th"):
        headers_list.append(th.get_text(strip=True))

    rows_data = []
    # Extract rows (tr)
    for tr in table.find_all("tr"):
        row = [td.get_text(strip=True) for td in tr.find_all("td")]
        if row:  # append non-empty rows
            rows_data.append(row)

    # Convert to DataFrame
    df = pd.DataFrame(rows_data, columns=headers_list if headers_list else None)
    
    # Save each table to CSV
    filename = f"lawsikho_table_{index + 1}.csv"
    df.to_csv(filename, index=False)
    print(f"Scraped and saved: {filename}")