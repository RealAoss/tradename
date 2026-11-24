"""tradename - match company names across languages, scripts and legal forms.

>>> import tradename
>>> tradename.is_match("شركة الخليج للتجارة والمقاولات ذ.م.م", "Gulf Trading & Contracting Co. LLC")
True
>>> tradename.is_match("Al Rajhi Bank", "Al Rajhi Cement")
False
"""

from .index import CompanyIndex, dedupe
from .legal import LegalForm
from .match import DEFAULT_THRESHOLD, Match, compare, is_match, keys, normalize, score
from .parse import Company, parse

__version__ = "0.1.0"
__all__ = [
    "compare", "score", "is_match", "parse", "normalize", "keys",
    "Match", "Company", "LegalForm", "CompanyIndex", "dedupe", "DEFAULT_THRESHOLD", "__version__",
]
