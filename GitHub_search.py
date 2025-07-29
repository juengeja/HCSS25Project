import requests
import time
import argparse
from datetime import datetime, timedelta

GITHUB_API_URL = "https://api.github.com/search/repositories"
MIN_STARS = 10
TIME_FILTER = f"pushed:>{(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')}"
BUFFER_OVERFLOW_KEYWORDS = [
    "strcpy", "strcat", "gets", "sprintf", "scanf",
    "memcpy", "memmove", "strncpy", "strncat", "fscanf"
]

def search_github_repos(token, max_results=20):
    headers = {"Authorization": f"token {token}"} if token else {}
    repos = []
    page = 1
    
    while len(repos) < max_results:
        query = f"stars:>={MIN_STARS} {TIME_FILTER} language:C language:C++"
        params = {
            "q": query,
            "sort": "updated",
            "order": "desc",
            "per_page": 100,
            "page": page
        }
        
        try:
            response = requests.get(GITHUB_API_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if "items" not in data:
                print("API Fehler:", data.get("message", "Unbekannter Fehler"))
                break
                
            for repo in data["items"]:
                if has_potential_overflow(repo, headers):
                    repos.append(format_repo_info(repo))
                    if len(repos) >= max_results:
                        break
            
            page += 1
            time.sleep(2)  # Rate-Limit
            
        except requests.exceptions.RequestException as e:
            print(f"API Fehler: {str(e)}")
            break
    
    return repos

def has_potential_overflow(repo, headers):
    """Prüft auf Verwendung gefährlicher Funktionen"""
    code_search_url = "https://api.github.com/search/code"
    for keyword in BUFFER_OVERFLOW_KEYWORDS:
        params = {
            "q": f"{keyword} repo:{repo['full_name']}",
            "per_page": 1
        }
        try:
            response = requests.get(code_search_url, headers=headers, params=params)
            if response.status_code == 200:
                result = response.json()
                if result["total_count"] > 0:
                    print(f"! Gefunden: {keyword} in {repo['full_name']}")
                    return True
            elif response.status_code == 403:  # Rate-Limit überschritten
                time.sleep(60)
        except Exception as e:
            print(f"Suche fehlgeschlagen: {str(e)}")
        time.sleep(2)  # Zwischen Anfragen pausieren
    return False

def format_repo_info(repo):
    return {
        "name": repo["name"],
        "owner": repo["owner"]["login"],
        "url": repo["html_url"],
        "stars": repo["stargazers_count"],
        "forks": repo["forks_count"],
        "last_updated": repo["pushed_at"],
        "language": repo["language"],
        "description": repo["description"] or "Keine Beschreibung"
    }

def main():
    parser = argparse.ArgumentParser(description="Finde GitHub-Projekte mit Buffer-Overflow-Potenzial")
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token (erforderlich)")
    parser.add_argument("--results", type=int, default=10, help="Maximale Ergebnisse (default: 10)")
    args = parser.parse_args()

    print("Suche nach C/C++ Projekten mit potenziellen Buffer-Overflow-Schwachstellen...")
    results = search_github_repos(args.token, args.results)

    print(f"\nGefundene Projekte mit Buffer-Overflow-Potenzial ({len(results)}):")
    for i, repo in enumerate(results, 1):
        print(f"\n{i}. {repo['owner']}/{repo['name']}")
        print(f"   Sprache: {repo['language']}")
        print(f"   Sterne: {repo['stars']} | Forks: {repo['forks']}")
        print(f"   Letztes Update: {repo['last_updated']}")
        print(f"   URL: {repo['url']}")
        print(f"   Beschreibung: {repo['description'][:150]}...")

if __name__ == "__main__":
    main()