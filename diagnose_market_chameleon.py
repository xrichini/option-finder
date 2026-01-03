# diagnose_market_chameleon.py - Diagnostic Market Chameleon
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def diagnose_market_chameleon_access():
    """Diagnostic de l'accès à Market Chameleon"""
    print("🔍 DIAGNOSTIC MARKET CHAMELEON")
    print("=" * 50)
    
    url = "https://marketchameleon.com/Reports/UnusualOptionVolumeReport"
    
    # Test 1: Vérification de la connectivité de base
    print("\n1. Test de connectivité...")
    try:
        response = requests.get(url, timeout=10)
        print(f"   Status code: {response.status_code}")
        print(f"   Content length: {len(response.content)} bytes")
        
        if response.status_code == 200:
            print("   ✅ Connectivité OK")
        else:
            print(f"   ❌ Erreur HTTP: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Erreur de connexion: {e}")
        return False
    
    # Test 2: Analyse de la structure HTML
    print("\n2. Analyse de la structure HTML...")
    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Chercher différents types de tableaux
        tables = soup.find_all('table')
        print(f"   Nombre de tableaux trouvés: {len(tables)}")
        
        if tables:
            for i, table in enumerate(tables[:3], 1):  # Analyser les 3 premiers tableaux
                print(f"   \n   Tableau {i}:")
                print(f"     Classes: {table.get('class', 'Aucune')}")
                print(f"     ID: {table.get('id', 'Aucun')}")
                
                # Compter les lignes et colonnes
                rows = table.find_all('tr')
                if rows:
                    print(f"     Lignes: {len(rows)}")
                    first_row = rows[0]
                    cols = first_row.find_all(['th', 'td'])
                    print(f"     Colonnes (première ligne): {len(cols)}")
                    
                    # Afficher les headers si présents
                    headers = [col.get_text().strip() for col in cols[:5]]  # Premiers 5 headers
                    if headers:
                        print(f"     Headers: {headers}")
        else:
            print("   ⚠️ Aucun tableau trouvé")
            
    except Exception as e:
        print(f"   ❌ Erreur parsing HTML: {e}")
        return False
    
    # Test 3: Recherche d'éléments spécifiques
    print("\n3. Recherche d'éléments de données...")
    try:
        # Chercher des mentions de volume, ratio, etc.
        text_content = soup.get_text().lower()
        
        keywords = ['volume', 'unusual', 'ratio', 'option', 'strike', 'expiration']
        found_keywords = [kw for kw in keywords if kw in text_content]
        
        print(f"   Mots-clés trouvés: {found_keywords}")
        
        if len(found_keywords) >= 4:
            print("   ✅ Contenu pertinent détecté")
        else:
            print("   ⚠️ Peu de contenu pertinent")
            
        # Chercher des patterns de données
        import re
        
        # Pattern pour les ratios (ex: 2.5x, 3.2x)
        ratio_pattern = r'\d+\.\d*x'
        ratios = re.findall(ratio_pattern, text_content)
        print(f"   Ratios trouvés: {len(ratios)} exemples: {ratios[:3]}")
        
        # Pattern pour les prix (ex: $150.50)
        price_pattern = r'\$\d+\.\d+'
        prices = re.findall(price_pattern, text_content)
        print(f"   Prix trouvés: {len(prices)} exemples: {prices[:3]}")
        
    except Exception as e:
        print(f"   ❌ Erreur analyse contenu: {e}")
    
    # Test 4: Vérification des restrictions d'accès
    print("\n4. Vérification des restrictions...")
    
    # Chercher des indicateurs d'authentification requise
    auth_indicators = [
        'login', 'sign in', 'subscribe', 'premium', 
        'authentication', 'member', 'account'
    ]
    
    page_text = soup.get_text().lower() if soup else ""
    found_auth = [indicator for indicator in auth_indicators if indicator in page_text]
    
    if found_auth:
        print(f"   ⚠️ Indicateurs d'authentification: {found_auth}")
        print("   Le site peut nécessiter un compte/abonnement")
    else:
        print("   ✅ Pas d'indicateurs d'authentification évidents")
    
    # Test 5: Sauvegarde pour inspection manuelle
    print("\n5. Sauvegarde pour inspection...")
    try:
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"mc_page_debug_{timestamp}.html"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"   Page sauvegardée: {filename}")
        print("   Vous pouvez l'ouvrir dans un navigateur pour inspection visuelle")
        
    except Exception as e:
        print(f"   ❌ Erreur sauvegarde: {e}")
    
    return True

def test_alternative_approach():
    """Test d'approches alternatives"""
    print("\n" + "=" * 50)
    print("🔧 TEST D'APPROCHES ALTERNATIVES")
    print("=" * 50)
    
    # Approche 1: Headers plus réalistes
    print("\n1. Test avec headers navigateur réalistes...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none'
    }
    
    try:
        url = "https://marketchameleon.com/Reports/UnusualOptionVolumeReport"
        response = requests.get(url, headers=headers, timeout=15)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            tables = soup.find_all('table')
            print(f"   Tables trouvées: {len(tables)}")
            
            # Chercher des données numériques dans les tables
            if tables:
                for i, table in enumerate(tables[:2], 1):
                    rows = table.find_all('tr')
                    data_rows = 0
                    for row in rows[1:6]:  # Skip header, check 5 rows
                        cells = row.find_all(['td', 'th'])
                        if len(cells) > 3:  # Au moins 4 colonnes
                            cell_texts = [cell.get_text().strip() for cell in cells]
                            # Chercher des données numériques
                            has_numbers = any(any(c.isdigit() for c in text) for text in cell_texts)
                            if has_numbers:
                                data_rows += 1
                    
                    print(f"   Tableau {i}: {data_rows} lignes avec données numériques")
                    
                    if data_rows > 0:
                        print("   ✅ Données potentielles trouvées!")
                        return True
            
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    # Approche 2: Test de la page d'accueil
    print("\n2. Test de la page d'accueil...")
    try:
        home_url = "https://marketchameleon.com"
        response = requests.get(home_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("   ✅ Page d'accueil accessible")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            links = soup.find_all('a', href=True)
            
            report_links = [
                link.get('href') for link in links 
                if 'unusual' in link.get('href', '').lower() or 
                   'option' in link.get('href', '').lower() or
                   'volume' in link.get('href', '').lower()
            ]
            
            print(f"   Liens de rapports trouvés: {len(report_links)}")
            for link in report_links[:3]:
                print(f"     - {link}")
                
        else:
            print(f"   ❌ Page d'accueil inaccessible: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Erreur page d'accueil: {e}")
    
    return False

def suggest_alternatives():
    """Suggère des alternatives à Market Chameleon"""
    print("\n" + "=" * 50)
    print("💡 ALTERNATIVES À MARKET CHAMELEON")
    print("=" * 50)
    
    alternatives = [
        {
            'name': 'Unusual Whales (free data)',
            'url': 'https://unusualwhales.com/flow',
            'description': 'Options flow en temps réel, partiellement gratuit'
        },
        {
            'name': 'FlowAlgo',
            'url': 'https://flowalgo.com',
            'description': 'Détection d\'options blocks et flow institutionnel'
        },
        {
            'name': 'Yahoo Finance Options',
            'url': 'https://finance.yahoo.com',
            'description': 'Données d\'options via API, volume et open interest'
        },
        {
            'name': 'CBOE Options Data',
            'url': 'https://www.cboe.com',
            'description': 'Données officielles de la bourse d\'options'
        },
        {
            'name': 'Tradier API',
            'url': 'https://tradier.com',
            'description': 'API avec données d\'options, volume inhabituel'
        }
    ]
    
    print("Sources alternatives pour données d'options inhabituelles:")
    print()
    
    for i, alt in enumerate(alternatives, 1):
        print(f"{i}. **{alt['name']}**")
        print(f"   URL: {alt['url']}")
        print(f"   Description: {alt['description']}")
        print()
    
    print("Recommandations:")
    print("✅ Yahoo Finance - Le plus accessible, API publique")
    print("✅ Tradier - Intégration existante dans votre projet")
    print("✅ CBOE - Données officielles et fiables")
    print("⚠️ Unusual Whales - Limité en version gratuite")
    print("⚠️ FlowAlgo - Payant mais très complet")

def main():
    """Fonction principale de diagnostic"""
    print("🚀 DIAGNOSTIC COMPLET MARKET CHAMELEON")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Diagnostic principal
    basic_access = diagnose_market_chameleon_access()
    
    if basic_access:
        # Tests d'approches alternatives
        alternative_success = test_alternative_approach()
        
        if not alternative_success:
            print("\n❌ CONCLUSION: Market Chameleon inaccessible")
            print("Causes probables:")
            print("- Site nécessite authentification/abonnement")
            print("- Protection anti-bot sophistiquée")
            print("- Structure HTML dynamique (JavaScript requis)")
            print("- Restrictions géographiques")
            
            suggest_alternatives()
        else:
            print("\n✅ CONCLUSION: Accès partiel possible")
            print("Des données sont détectées, mais le scraper nécessite des ajustements")
    else:
        print("\n❌ CONCLUSION: Problème de connectivité de base")
        print("Vérifier la connexion internet et les paramètres firewall")
    
    print("\n📋 ACTIONS RECOMMANDÉES:")
    print("1. Utiliser l'API Tradier existante pour volumes inhabituels")
    print("2. Implémenter Yahoo Finance comme source alternative")  
    print("3. Créer un algorithme interne de détection d'anomalies")
    print("4. Considérer une approche payante si budget disponible")

if __name__ == "__main__":
    main()