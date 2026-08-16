import os
import csv
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# Configuration & API Credentials
EMAIL = os.environ.get("NCBI_EMAIL", "cz313109@ohio.edu")
API_KEY = os.environ.get("NCBI_API_KEY", "")

MESH_TERMS = [
    "RNA, Messenger", "Transcription, Genetic", "Protein Biosynthesis", "Codon",
    "RNA Caps", "Poly A", "Lipids", "Nanoparticles", "Gene Editing",
    "Recombinases", "Retroelements", "Lentivirus", "Receptors, Chimeric Antigen",
    "T-Lymphocytes", "B-Lymphocytes", "Monocytes", "Macrophages",
    "Immunotherapy, Adoptive", "Neoplasms", "Lymphoma", "Leukemia",
    "Autoimmune Diseases", "Rheumatic Diseases", "Anemia, Sickle Cell",
    "alpha 1-Antitrypsin Deficiency"
]

def build_search_query():
    # Join terms with OR
    mesh_query = " OR ".join([f'"{term}"[MeSH]' for term in MESH_TERMS])
    
    # Calculate yesterday's date formatted as YYYY/MM/DD
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime("%Y/%m/%d")
    
    # Restrict to Entrez Date (EDAT) for yesterday
    full_query = f"({mesh_query}) AND ({date_str}[EDAT] : {date_str}[EDAT])"
    return full_query

def search_pubmed(query):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": "1000",  # Retrieve up to 1000 paper IDs per run
        "email": EMAIL,
    }
    if API_KEY:
        params["api_key"] = API_KEY

    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": f"PubMedAgent/1.0 ({EMAIL})"})
    
    with urllib.request.urlopen(req) as response:
        import json
        data = json.loads(response.read().decode())
        return data.get("esearchresult", {}).get("idlist", [])

def fetch_paper_details(id_list):
    if not id_list:
        return []

    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "xml",
        "email": EMAIL,
    }
    if API_KEY:
        params["api_key"] = API_KEY

    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": f"PubMedAgent/1.0 ({EMAIL})"})

    with urllib.request.urlopen(req) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    papers = []

    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID")
        
        # Extract Paper Title
        title = article.findtext(".//ArticleTitle") or "No title available"

        # Extract Journal Title
        journal = article.findtext(".//Journal/Title") or "No journal available"
        
        # Extract Abstract
        abstract_texts = article.findall(".//AbstractText")
        if abstract_texts:
            abstract = " ".join([elem.text for elem in abstract_texts if elem.text])
        else:
            abstract = "No abstract available"

        # Extract Publication Date
        pub_date = article.find(".//Journal/JournalIssue/PubDate")
        year = pub_date.findtext("Year") if pub_date is not None else ""
        month = pub_date.findtext("Month") if pub_date is not None else ""
        day = pub_date.findtext("Day") if pub_date is not None else ""
        date_str = f"{year}-{month}-{day}".strip("-")

        papers.append({
            "PMID": pmid,
            "Title": title.strip(),
            "Journal": journal.strip(),
            "Abstract": abstract.strip(),
            "Publication_Date": date_str,
            "PubMed_URL": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        })

    return papers

def save_to_csv(papers, filename):
    fieldnames = ["PMID", "Title", "Journal", "Abstract", "Publication_Date", "PubMed_URL"]
    with open(filename, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(papers)

def main():
    query = build_search_query()
    print(f"Executing Query: {query}\n")
    
    pmids = search_pubmed(query)
    print(f"Found {len(pmids)} papers indexed yesterday matching the criteria.")
    
    if pmids:
        papers = fetch_paper_details(pmids)
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        filename = f"pubmed_papers_{yesterday_str}.csv"
        save_to_csv(papers, filename)
        print(f"Successfully saved records to {filename}")
    else:
        print("No papers found for yesterday.")

if __name__ == "__main__":
    main()
