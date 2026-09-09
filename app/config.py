import os
import pathlib

DATA_DIR = pathlib.Path(os.environ.get("PORTAL_DATA", "./sample-data")).resolve()
CONFIG_PATH = pathlib.Path(os.environ.get("PORTAL_CONFIG", "./config/portal.yaml")).resolve()
REGISTRY_PATH = DATA_DIR / ".registry.json"
DB_PATH = DATA_DIR / ".portalite.duckdb"

ALLOWED_EXTENSIONS = {".csv", ".json", ".xlsx", ".xls"}
MAX_UPLOAD_BYTES = 200 * 1024 * 1024

GEO_PATTERNS = {
    "iso2": r"^[A-Za-z]{2}$",
    "iso3": r"^[A-Za-z]{3}$",
    "country_name": None,
}
LAT_COLS = {"lat", "latitude", "y"}
LON_COLS = {"lon", "lng", "long", "longitude", "x"}

COUNTRY_NAMES = {
    "afghanistan", "albania", "algeria", "argentina", "armenia", "australia", "austria",
    "azerbaijan", "bahrain", "bangladesh", "belarus", "belgium", "bolivia",
    "bosnia and herzegovina", "botswana", "brazil", "bulgaria", "cambodia", "cameroon",
    "canada", "chad", "chile", "china", "colombia", "costa rica", "croatia", "cuba",
    "dr congo", "democratic republic of the congo",
    "cyprus", "czechia", "denmark", "ecuador", "egypt", "el salvador",
    "eritrea", "estonia", "ethiopia", "finland", "france", "germany",
    "ghana", "greece", "guatemala", "guinea", "haiti", "honduras", "hungary", "iceland", "india", "indonesia", "iran",
    "iraq", "ireland", "israel", "italy", "jamaica", "japan", "jordan", "kazakhstan",
    "kenya", "kuwait", "kyrgyzstan", "laos", "latvia", "lebanon", "libya",
    "lithuania", "luxembourg", "malaysia", "mali", "malta", "mexico", "moldova",
    "mongolia", "montenegro", "morocco", "mozambique", "myanmar", "nepal",
    "netherlands", "new zealand", "nicaragua", "niger", "nigeria", "north macedonia",
    "norway", "oman", "pakistan", "panama", "paraguay", "peru", "philippines",
    "poland", "portugal", "qatar", "romania", "russia", "rwanda", "saudi arabia",
    "senegal", "serbia", "singapore", "slovakia", "slovenia", "somalia",
    "south africa", "south korea", "south sudan", "spain", "sri lanka",
    "sudan", "sweden",
    "switzerland", "syria", "taiwan", "tajikistan", "tanzania", "thailand",
    "tunisia", "turkey", "turkmenistan", "uganda", "ukraine",
    "united arab emirates", "united kingdom", "united states", "uruguay",
    "uzbekistan", "venezuela", "vietnam", "yemen", "zambia", "zimbabwe",
}
