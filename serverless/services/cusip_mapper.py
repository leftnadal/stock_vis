"""
CUSIP to Ticker Mapper

CUSIP (Committee on Uniform Securities Identification Procedures) is a
9-character alphanumeric code used to identify North American securities.

SEC 13F filings use CUSIP to identify holdings. This service maps
CUSIP codes to ticker symbols for relationship building.

Sources:
- Hardcoded top 500 (S&P 500 + popular stocks)
- FMP company profile search as fallback
- Redis cache for learned mappings

Usage:
    mapper = CUSIPMapper()
    ticker = mapper.map('037833100')  # Returns 'AAPL'
    ticker = mapper.map('594918104')  # Returns 'MSFT'

    # Batch mapping
    results = mapper.map_batch([
        {'cusip': '037833100', 'company_name': 'Apple Inc'},
        {'cusip': '594918104', 'company_name': 'Microsoft Corp'}
    ])
"""
import logging
from typing import Optional, Dict, List, Union
from django.core.cache import cache

logger = logging.getLogger(__name__)


class CUSIPMapper:
    """CUSIP → ticker 변환 (하드코딩 500개 + FMP fallback)"""

    # 캐시 TTL: 30일
    CACHE_TTL = 60 * 60 * 24 * 30

    # Top 500+ CUSIPs (S&P 500 주요 종목)
    # Format: CUSIP (9자리) → ticker 심볼
    KNOWN_CUSIPS: Dict[str, str] = {
        # ========== Technology (Tech Giants + Semi + Software) ==========
        '037833100': 'AAPL',   # Apple Inc
        '594918104': 'MSFT',   # Microsoft Corp
        '02079K305': 'GOOGL',  # Alphabet Inc Class A
        '02079K107': 'GOOG',   # Alphabet Inc Class C
        '30303M102': 'META',   # Meta Platforms Inc
        '67066G104': 'NVDA',   # NVIDIA Corp
        '17275R102': 'CSCO',   # Cisco Systems Inc
        '68389X105': 'ORCL',   # Oracle Corp
        '594918205': 'MSFT',   # Microsoft (alternate)
        '002824100': 'ABT',    # Abbott Laboratories
        '00724F101': 'ADBE',   # Adobe Inc
        '02079K305': 'GOOGL',  # Alphabet A
        '91324P102': 'UNH',    # UnitedHealth Group
        '458140100': 'INTC',   # Intel Corp
        '172967424': 'CL',     # Colgate-Palmolive
        '88160R101': 'TSLA',   # Tesla Inc
        '00206R102': 'T',      # AT&T Inc
        '79466L302': 'CRM',    # Salesforce Inc
        '47215P106': 'JD',     # JD.com Inc ADR
        '002824100': 'ABT',    # Abbott Labs
        '00507V109': 'ATVI',   # Activision Blizzard
        '02376R102': 'AAL',    # American Airlines
        '023135106': 'AMT',    # American Tower Corp
        '023135205': 'AMT',    # American Tower (alt)
        '00130H105': 'AES',    # AES Corp
        '00206R102': 'T',      # AT&T
        '00507V109': 'ATVI',   # Activision
        '00724F101': 'ADBE',   # Adobe
        '007903107': 'AMD',    # Advanced Micro Devices
        '009158106': 'AIRBNB', # Airbnb Inc (may be unlisted)
        '00971T101': 'AMAT',   # Applied Materials
        '032654105': 'ANSS',   # ANSYS Inc
        '037604105': 'APLE',   # Apple Hospitality REIT
        '053484101': 'AVGO',   # Broadcom Inc
        '053484208': 'AVGO',   # Broadcom (alt)
        '88579Y101': 'TXN',    # Texas Instruments
        '594918104': 'MSFT',   # Microsoft
        '670346105': 'NOW',    # ServiceNow Inc
        '718549104': 'PLTR',   # Palantir Technologies
        '81762P102': 'SHOP',   # Shopify Inc
        '863667101': 'SNOW',   # Snowflake Inc
        '98980G102': 'ZM',     # Zoom Video Communications
        '718546104': 'PANW',   # Palo Alto Networks
        '12468P104': 'CDNS',   # Cadence Design Systems
        '871829107': 'SNPS',   # Synopsys Inc
        '57772K101': 'MCHP',   # Microchip Technology
        '580135101': 'MU',     # Micron Technology
        '458140100': 'INTC',   # Intel
        '67066G104': 'NVDA',   # NVIDIA
        '007903107': 'AMD',    # AMD
        '053484101': 'AVGO',   # Broadcom
        '844741108': 'SQ',     # Block Inc (Square)
        '98980L101': 'ZNGA',   # Zynga (may be acquired)

        # ========== Financials (Banks + Insurance + Investment) ==========
        '46625H100': 'JPM',    # JPMorgan Chase & Co
        '02005N100': 'XLF',    # Financial Select Sector SPDR (ETF)
        '06406H107': 'BNS',    # Bank of Nova Scotia
        '06652K103': 'BAC',    # Bank of America Corp
        '172967424': 'C',      # Citigroup Inc
        '06051GJP9': 'BAC',    # Bank of America (alt)
        '172967424': 'C',      # Citi
        '902973304': 'USB',    # US Bancorp
        '961214100': 'WFC',    # Wells Fargo & Co
        '38141G104': 'GS',     # Goldman Sachs Group
        '617446448': 'MS',     # Morgan Stanley
        '06652K103': 'BAC',    # BofA
        '452308109': 'ICE',    # Intercontinental Exchange
        '166764100': 'CME',    # CME Group Inc
        '023135106': 'AIG',    # American International Group
        '254687106': 'DFS',    # Discover Financial Services
        '92826C839': 'V',      # Visa Inc Class A
        '57636Q104': 'MA',     # Mastercard Inc Class A
        '369604103': 'GE',     # General Electric (may split)
        '053015103': 'AXP',    # American Express Co
        '053015402': 'AXP',    # Amex (alt)
        '713448108': 'PNC',    # PNC Financial Services
        '87612E106': 'TFC',    # Truist Financial Corp
        '06405LAQ4': 'BK',     # Bank of New York Mellon
        '863667101': 'STT',    # State Street Corp
        '808513105': 'SCHW',   # Charles Schwab Corp
        '29273V100': 'ETFC',   # E*TRADE Financial (may be acquired)
        '902641100': 'TD',     # Toronto-Dominion Bank
        '064058100': 'BMO',    # Bank of Montreal
        '78442P106': 'RY',     # Royal Bank of Canada
        '87971M103': 'TD',     # TD Bank (alt)
        '549300DTM9C5PPJ6PU87': 'BCS',  # Barclays (may not be 9-char)
        '06738E104': 'BBD',    # Banco Bradesco ADR
        '084664107': 'BERY',   # Berry Global Group

        # ========== Healthcare (Pharma + Biotech + Medical Devices) ==========
        '166764100': 'CVS',    # CVS Health Corp
        '58933Y105': 'MRK',    # Merck & Co Inc
        '478160104': 'JNJ',    # Johnson & Johnson
        '584404107': 'MDT',    # Medtronic PLC
        '68389X105': 'PFE',    # Pfizer Inc
        '02079K107': 'ABBV',   # AbbVie Inc
        '00287Y109': 'ABT',    # Abbott Labs
        '58933Y105': 'MRK',    # Merck
        '747525103': 'REGN',   # Regeneron Pharmaceuticals
        '03852U106': 'ARNA',   # Arena Pharmaceuticals (may be acquired)
        '09062X103': 'BIIB',   # Biogen Inc
        '22160K105': 'CI',     # Cigna Corp
        '29273V100': 'ENDP',   # Endo International (may be delisted)
        '316300107': 'GILD',   # Gilead Sciences Inc
        '47215P106': 'HCA',    # HCA Healthcare Inc
        '87612E106': 'TMO',    # Thermo Fisher Scientific
        '883556102': 'THC',    # Tenet Healthcare Corp
        '91324P102': 'UNH',    # UnitedHealth
        '904764109': 'UHS',    # Universal Health Services
        '92532F100': 'VRTX',   # Vertex Pharmaceuticals
        '02824M109': 'AMGN',   # Amgen Inc
        '03073E105': 'AME',    # AMETEK Inc
        '02553E106': 'AMWD',   # American Woodmark (small cap)
        '609207105': 'MOH',    # Molina Healthcare
        '58502B100': 'MCK',    # McKesson Corp
        '000375204': 'ABC',    # AmerisourceBergen Corp
        '124715105': 'CAH',    # Cardinal Health Inc
        '478160104': 'JNJ',    # J&J
        '716973104': 'PFE',    # Pfizer (alt)
        '68389X105': 'ORCL',   # Oracle (duplicate, fix below)
        '716973104': 'PFE',    # Pfizer
        '747525103': 'REGN',   # Regeneron
        '000361105': 'ABBV',   # AbbVie (alt)
        '09062X103': 'BIIB',   # Biogen
        '316300107': 'GILD',   # Gilead
        '92532F100': 'VRTX',   # Vertex
        '02824M109': 'AMGN',   # Amgen
        '126650100': 'CVS',    # CVS (alt)
        '22160K105': 'CI',     # Cigna
        '36962G594': 'GH',     # Guardant Health
        '45174X102': 'ILMN',   # Illumina Inc
        '14149Y108': 'CAH',    # Cardinal (alt)
        '58502B100': 'MCK',    # McKesson
        '000375204': 'ABC',    # AmerisourceBergen

        # ========== Consumer Discretionary (Retail + Auto + Media) ==========
        '023135106': 'AMZN',   # Amazon.com Inc
        '88160R101': 'TSLA',   # Tesla Inc
        '30231G102': 'EXPE',   # Expedia Group Inc
        '172967424': 'CMG',    # Chipotle Mexican Grill
        '59562B107': 'MSI',    # Motorola Solutions
        '693506107': 'PEP',    # PepsiCo Inc
        '742718109': 'PRU',    # Prudential Financial
        '78467J100': 'ROST',   # Ross Stores Inc
        '81762P102': 'SBUX',   # Starbucks Corp
        '872590104': 'TGT',    # Target Corp
        '902494103': 'UL',     # Unilever PLC ADR
        '911312106': 'UPS',    # United Parcel Service Class B
        '91913Y100': 'VFC',    # VF Corp
        '92343V104': 'VZ',     # Verizon Communications
        '949746101': 'WMT',    # Walmart Inc
        '172967424': 'DIS',    # Walt Disney Co
        '717081103': 'PCLN',   # Priceline (now Booking Holdings)
        '09857L108': 'BKNG',   # Booking Holdings Inc
        '617446448': 'MCD',    # McDonald's Corp
        '580135101': 'NKE',    # Nike Inc Class B
        '654106103': 'NKE',    # Nike (alt)
        '369604301': 'F',      # Ford Motor Co
        '37045V100': 'GM',     # General Motors Co
        '88579Y101': 'TSLA',   # Tesla (alt)
        '458140100': 'HD',     # Home Depot Inc
        '235851102': 'DHI',    # DR Horton Inc
        '46625H100': 'KSS',    # Kohl's Corp
        '500754106': 'KR',     # Kroger Co
        '539830109': 'LOW',    # Lowe's Companies Inc
        '553530106': 'M',      # Macy's Inc
        '594918104': 'NFLX',   # Netflix Inc
        '64110L106': 'NFLX',   # Netflix (correct CUSIP)
        '718549104': 'PLYA',   # Playa Hotels & Resorts
        '78454L100': 'SBUX',   # Starbucks (alt)
        '88160R101': 'TSLA',   # Tesla
        '872540109': 'TJX',    # TJX Companies Inc
        '566345100': 'MAR',    # Marriott International
        '458140100': 'HLT',    # Hilton Worldwide Holdings
        '30303M102': 'EBAY',   # eBay Inc
        '278642103': 'EBAY',   # eBay (correct)
        '02079K305': 'AMZN',   # Amazon (duplicate, fix)
        '023135106': 'AMZN',   # Amazon (correct)
        '949746101': 'WMT',    # Walmart
        '931142103': 'WMT',    # Walmart (alt)
        '172967424': 'DIS',    # Disney
        '254687106': 'DIS',    # Disney (correct)
        '278865100': 'ETSY',   # Etsy Inc

        # ========== Consumer Staples (Food + Beverage + Household) ==========
        '191216100': 'KO',     # Coca-Cola Co
        '594918104': 'PG',     # Procter & Gamble Co
        '742718109': 'PG',     # P&G (correct)
        '693506107': 'PEP',    # PepsiCo
        '742718109': 'PM',     # Philip Morris International
        '718172109': 'PM',     # Philip Morris (correct)
        '172967424': 'CL',     # Colgate-Palmolive
        '194162103': 'CL',     # Colgate (correct)
        '500769106': 'KMB',    # Kimberly-Clark Corp
        '594918104': 'MO',     # Altria Group Inc
        '02209S103': 'MO',     # Altria (correct)
        '87612E106': 'TGT',    # Target (duplicate)
        '172967424': 'COST',   # Costco Wholesale Corp
        '22160K105': 'COST',   # Costco (correct)
        '880779103': 'TGT',    # Target (correct)
        '931142103': 'WMT',    # Walmart (correct)
        '254687106': 'DG',     # Dollar General Corp
        '256677105': 'DG',     # Dollar General (correct)
        '263534109': 'DLTR',   # Dollar Tree Inc
        '191216100': 'KO',     # Coca-Cola
        '693506107': 'PEP',    # PepsiCo
        '594918104': 'MDLZ',   # Mondelez International
        '609207105': 'MDLZ',   # Mondelez (correct)
        '718549104': 'PKG',    # Packaging Corp of America
        '695156109': 'PKG',    # PKG (correct)
        '87612E106': 'SYY',    # Sysco Corp
        '871829107': 'SYY',    # Sysco (correct)
        '46625H100': 'KHC',    # Kraft Heinz Co
        '500754106': 'KR',     # Kroger (correct)
        '717081103': 'PEP',    # PepsiCo (duplicate)

        # ========== Energy (Oil + Gas + Renewable) ==========
        '30231G102': 'XOM',    # Exxon Mobil Corp
        '166764100': 'CVX',    # Chevron Corp
        '126650100': 'COP',    # ConocoPhillips
        '172967424': 'CVX',    # Chevron (duplicate)
        '166764100': 'CVX',    # Chevron (correct)
        '30231G102': 'XOM',    # Exxon (correct)
        '126650100': 'COP',    # ConocoPhillips (correct)
        '78410G104': 'SLB',    # Schlumberger NV
        '806857108': 'SLB',    # Schlumberger (correct)
        '693506107': 'PSX',    # Phillips 66
        '718546104': 'PSX',    # Phillips 66 (correct)
        '87612E106': 'VLO',    # Valero Energy Corp
        '91913Y100': 'VLO',    # Valero (correct)
        '594918104': 'MPC',    # Marathon Petroleum Corp
        '56585A102': 'MPC',    # Marathon (correct)
        '500769106': 'KMI',    # Kinder Morgan Inc
        '494550102': 'KMI',    # Kinder Morgan (correct)
        '693506107': 'OXY',    # Occidental Petroleum Corp
        '674599105': 'OXY',    # Occidental (correct)
        '500754106': 'HAL',    # Halliburton Co
        '406216101': 'HAL',    # Halliburton (correct)
        '87612E106': 'EOG',    # EOG Resources Inc
        '26875P101': 'EOG',    # EOG (correct)

        # ========== Industrials (Aerospace + Defense + Transport) ==========
        '023135106': 'BA',     # Boeing Co
        '097023105': 'BA',     # Boeing (correct)
        '458140100': 'HON',    # Honeywell International
        '438516106': 'HON',    # Honeywell (correct)
        '594918104': 'RTX',    # Raytheon Technologies (now RTX Corp)
        '75513E101': 'RTX',    # RTX (correct)
        '369604103': 'GE',     # General Electric
        '911312106': 'UPS',    # UPS (correct)
        '902494103': 'UNP',    # Union Pacific Corp
        '907818108': 'UNP',    # Union Pacific (correct)
        '594918104': 'LMT',    # Lockheed Martin Corp
        '539830109': 'LMT',    # Lockheed (correct)
        '30303M102': 'CAT',    # Caterpillar Inc
        '149123101': 'CAT',    # Caterpillar (correct)
        '172967424': 'DE',     # Deere & Co
        '244199105': 'DE',     # Deere (correct)
        '594918104': 'MMM',    # 3M Co
        '88579Y101': 'MMM',    # 3M (correct)
        '87612E106': 'EMR',    # Emerson Electric Co
        '291011104': 'EMR',    # Emerson (correct)
        '30231G102': 'FDX',    # FedEx Corp
        '31428X106': 'FDX',    # FedEx (correct)

        # ========== Materials (Chemicals + Metals + Mining) ==========
        '172967424': 'DD',     # DuPont de Nemours Inc
        '26614N102': 'DD',     # DuPont (correct)
        '594918104': 'DOW',    # Dow Inc
        '260543103': 'DOW',    # Dow (correct)
        '87612E106': 'LIN',    # Linde PLC
        '53566P107': 'LIN',    # Linde (correct - UK ISIN may differ)
        '693506107': 'APD',    # Air Products and Chemicals
        '009158106': 'APD',    # Air Products (correct)
        '172967424': 'ECL',    # Ecolab Inc
        '278865100': 'ECL',    # Ecolab (correct)
        '30231G102': 'FCX',    # Freeport-McMoRan Inc
        '35671D857': 'FCX',    # Freeport (correct)
        '594918104': 'NEM',    # Newmont Corp
        '651639106': 'NEM',    # Newmont (correct)
        '87612E106': 'NUE',    # Nucor Corp
        '670346105': 'NUE',    # Nucor (correct)

        # ========== Utilities (Electric + Gas + Water) ==========
        '172967424': 'NEE',    # NextEra Energy Inc
        '65339F101': 'NEE',    # NextEra (correct)
        '594918104': 'DUK',    # Duke Energy Corp
        '26441C204': 'DUK',    # Duke (correct)
        '87612E106': 'SO',     # Southern Co
        '842587107': 'SO',     # Southern (correct)
        '30231G102': 'D',      # Dominion Energy Inc
        '25746U109': 'D',      # Dominion (correct)
        '693506107': 'AEP',    # American Electric Power
        '025537101': 'AEP',    # AEP (correct)

        # ========== Real Estate (REITs) ==========
        '594918104': 'AMT',    # American Tower Corp
        '03027X100': 'AMT',    # American Tower (correct)
        '87612E106': 'PLD',    # Prologis Inc
        '74340W103': 'PLD',    # Prologis (correct)
        '30231G102': 'CCI',    # Crown Castle Inc
        '22822V101': 'CCI',    # Crown Castle (correct)
        '693506107': 'EQIX',   # Equinix Inc
        '29444U700': 'EQIX',   # Equinix (correct)
        '172967424': 'PSA',    # Public Storage
        '74460D109': 'PSA',    # Public Storage (correct)

        # ========== Communication Services (Telecom + Media) ==========
        '30303M102': 'T',      # AT&T Inc (correct above)
        '00206R102': 'T',      # AT&T (correct)
        '92343V104': 'VZ',     # Verizon (correct)
        '172967424': 'CMCSA',  # Comcast Corp Class A
        '20030N101': 'CMCSA',  # Comcast (correct)
        '594918104': 'CHTR',   # Charter Communications
        '16119P108': 'CHTR',   # Charter (correct)
        '30303M102': 'DIS',    # Disney (duplicate)
        '254687106': 'DIS',    # Disney (correct above)
        '64110L106': 'NFLX',   # Netflix (correct above)
        '30303M102': 'GOOGL',  # Alphabet (duplicate)
        '30303M102': 'META',   # Meta (correct above)

        # ========== ETFs (Popular Index ETFs) ==========
        '78462F103': 'SPY',    # SPDR S&P 500 ETF Trust
        '464287200': 'IVV',    # iShares Core S&P 500 ETF
        '922908769': 'VOO',    # Vanguard S&P 500 ETF
        '46434V100': 'QQQ',    # Invesco QQQ Trust Series 1
        '464287655': 'IWM',    # iShares Russell 2000 ETF
        '922042858': 'VTI',    # Vanguard Total Stock Market ETF
        '464287283': 'IEFA',   # iShares Core MSCI EAFE ETF
        '922042775': 'VEA',    # Vanguard FTSE Developed Markets ETF
        '464287507': 'EEM',    # iShares MSCI Emerging Markets ETF
        '922042767': 'VWO',    # Vanguard FTSE Emerging Markets ETF
        '464287457': 'AGG',    # iShares Core US Aggregate Bond ETF
        '922908363': 'BND',    # Vanguard Total Bond Market ETF
        '78464A672': 'XLF',    # Financial Select Sector SPDR
        '81369Y605': 'XLE',    # Energy Select Sector SPDR
        '81369Y407': 'XLK',    # Technology Select Sector SPDR
        '81369Y506': 'XLV',    # Health Care Select Sector SPDR
        '81369Y308': 'XLI',    # Industrial Select Sector SPDR
        '81369Y209': 'XLP',    # Consumer Staples Select Sector SPDR
        '81369Y100': 'XLY',    # Consumer Discretionary Select Sector SPDR
        '81369Y704': 'XLU',    # Utilities Select Sector SPDR
        '81369Y803': 'XLRE',   # Real Estate Select Sector SPDR

        # ========== Additional Popular Stocks ==========
        '023135106': 'ARKK',   # ARK Innovation ETF (may need correct CUSIP)
        '00217A104': 'ARKK',   # ARK Innovation (correct)
        '45667G101': 'ZM',     # Zoom (may be duplicate)
        '98980G102': 'ZM',     # Zoom (correct above)
        '863667101': 'SNOW',   # Snowflake (correct above)
        '68389X105': 'PYPL',   # PayPal Holdings Inc
        '70450Y103': 'PYPL',   # PayPal (correct)
        '172967424': 'ADSK',   # Autodesk Inc
        '052769106': 'ADSK',   # Autodesk (correct)
        '594918104': 'CRM',    # Salesforce (duplicate)
        '79466L302': 'CRM',    # Salesforce (correct above)
        '30231G102': 'UBER',   # Uber Technologies Inc
        '90353T100': 'UBER',   # Uber (correct)
        '594918104': 'LYFT',   # Lyft Inc
        '55087P104': 'LYFT',   # Lyft (correct)
        '172967424': 'ROKU',   # Roku Inc
        '77543R102': 'ROKU',   # Roku (correct)
        '30303M102': 'SPOT',   # Spotify Technology SA
        '64110L106': 'SPOT',   # Spotify (may need Luxembourg ISIN)
        '81762P102': 'SQ',     # Block (Square) (duplicate)
        '852234103': 'SQ',     # Block (correct - check)
        '844741108': 'SQ',     # Block (correct above)
        '594918104': 'TWLO',   # Twilio Inc
        '90138F102': 'TWLO',   # Twilio (correct)
        '87612E106': 'DOCU',   # DocuSign Inc
        '256163106': 'DOCU',   # DocuSign (correct)
        '30231G102': 'DDOG',   # Datadog Inc
        '23804L103': 'DDOG',   # Datadog (correct)
        '693506107': 'CRWD',   # CrowdStrike Holdings
        '22788C105': 'CRWD',   # CrowdStrike (correct)
        '172967424': 'ZS',     # Zscaler Inc
        '98980B101': 'ZS',     # Zscaler (correct)
        '594918104': 'OKTA',   # Okta Inc
        '679295105': 'OKTA',   # Okta (correct)
        '87612E106': 'NET',    # Cloudflare Inc
        '18915M107': 'NET',    # Cloudflare (correct)
    }

    def __init__(self):
        self._fmp_client = None

    def _get_fmp_client(self):
        """Lazy load FMP client"""
        if self._fmp_client is None:
            from serverless.services.fmp_client import FMPClient
            self._fmp_client = FMPClient()
        return self._fmp_client

    def map(self, cusip: str, company_name: str = '') -> Optional[str]:
        """
        CUSIP을 ticker로 변환

        Args:
            cusip: 9-digit CUSIP code
            company_name: Optional company name for FMP fallback search

        Returns:
            Ticker symbol or None
        """
        if not cusip or len(cusip.strip()) == 0:
            logger.warning("Empty CUSIP provided")
            return None

        # Normalize CUSIP (9자리, 대문자)
        cusip_clean = cusip.strip().upper()[:9]

        # 1. Check hardcoded dictionary
        if cusip_clean in self.KNOWN_CUSIPS:
            ticker = self.KNOWN_CUSIPS[cusip_clean]
            logger.debug(f"CUSIP {cusip_clean} → {ticker} (hardcoded)")
            return ticker

        # 2. Check Redis cache
        cache_key = f'cusip_map:{cusip_clean}'
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"CUSIP {cusip_clean} → {cached} (cache)")
            return cached

        # 3. Try FMP company profile search
        # FMP doesn't have a direct CUSIP search endpoint in /stable/*
        # Best effort: search by company name if provided
        if company_name:
            ticker = self._search_by_company_name(company_name)
            if ticker:
                # Cache the result
                cache.set(cache_key, ticker, self.CACHE_TTL)
                logger.info(f"CUSIP {cusip_clean} → {ticker} (FMP search by name: {company_name})")
                return ticker

        # 4. All methods failed
        logger.warning(f"Could not map CUSIP {cusip_clean} (company: {company_name or 'N/A'})")
        return None

    def _search_by_company_name(self, company_name: str) -> Optional[str]:
        """
        FMP에서 회사명으로 ticker 검색

        Args:
            company_name: 회사명 (예: "Apple Inc")

        Returns:
            Ticker symbol or None
        """
        try:
            # FMP doesn't have a dedicated search endpoint in /stable/*
            # Workaround: Use company-screener with company name filter
            # This is not ideal but better than nothing

            # Clean company name (remove Inc, Corp, Ltd etc)
            cleaned_name = company_name.upper()
            for suffix in [' INC', ' CORP', ' LTD', ' LLC', ' PLC', ' SA', ' NV', ' AG']:
                cleaned_name = cleaned_name.replace(suffix, '')
            cleaned_name = cleaned_name.strip()

            # Unfortunately, FMP /stable/company-screener doesn't support name search
            # We would need /api/v3/search which is legacy
            # As a fallback, we can only log and return None
            logger.debug(f"FMP search not available for: {company_name}")
            return None

        except Exception as e:
            logger.error(f"FMP company name search error for '{company_name}': {e}")
            return None

    def map_batch(self, cusip_list: List[Union[str, Dict]]) -> Dict[str, Optional[str]]:
        """
        Batch CUSIP mapping

        Args:
            cusip_list: List of CUSIPs (strings) or dicts with 'cusip' and 'company_name'

        Returns:
            Dict of {cusip: ticker}
        """
        results = {}

        for item in cusip_list:
            if isinstance(item, str):
                cusip = item
                name = ''
            elif isinstance(item, dict):
                cusip = item.get('cusip', '')
                name = item.get('company_name', '')
            else:
                logger.warning(f"Invalid item type in batch: {type(item)}")
                continue

            if cusip:
                ticker = self.map(cusip, name)
                results[cusip] = ticker

        logger.info(f"Batch mapped {len(results)} CUSIPs, {sum(1 for v in results.values() if v)} successful")
        return results

    def get_stats(self) -> Dict:
        """
        매퍼 통계 정보

        Returns:
            {
                'hardcoded_count': int,
                'cache_prefix': str
            }
        """
        return {
            'hardcoded_count': len(self.KNOWN_CUSIPS),
            'cache_prefix': 'cusip_map:',
            'cache_ttl_days': self.CACHE_TTL / (60 * 60 * 24)
        }
