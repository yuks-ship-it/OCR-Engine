# backend/app/services/field_parser.py
import re

# Nepali digit → ASCII digit mapping
NEP_TO_ENG = str.maketrans('०१२३४५६७८९', '0123456789')

OCR_FIXES = {
    'सार्ग': 'मार्ग',
    '=': '-',
    '|': '-',
}

KNOWN_LOCATIONS = [
    'गोङ्गबु', 'गोंगबु', 'बालाजु', 'बानेश्वर', 'कोटेश्वर', 'कालिमाटी',
    'सोह्रखुट्टे', 'महाराजगञ्ज', 'चाबहिल', 'बौद्ध', 'पशुपति', 'थापाथली',
    'नयाँबजार', 'इन्द्रचोक', 'असन', 'ठमेल', 'लाजिम्पाट', 'माइतीघर',
    'पुतलीसडक', 'रत्नपार्क', 'नक्साल', 'दरबारमार्ग', 'नयाँठिमी',
    'भक्तपुर', 'ललितपुर', 'पाटन', 'जावलाखेल', 'सातदोबाटो', 'एकान्तकुना',
    'हात्तीसार', 'तिनकुने', 'मनमैजु', 'टोखा', 'बुढानिलकण्ठ', 'शंखपार्क',
    'कीर्तिपुर', 'धापासी', 'जोरपाटी', 'मिनभवन', 'नागपोखरी',
]


def _normalize(text: str) -> str:
    text = text.replace('\n', ' ').strip()
    for wrong, right in OCR_FIXES.items():
        text = text.replace(wrong, right)
    return text


def _to_english_digits(text: str) -> str:
    return text.translate(NEP_TO_ENG)


class FieldParser:
    def parse(self, text: str) -> dict:
        results = {}
        clean = _normalize(text)
        normalized = _to_english_digits(clean)

        # 1. Plus Code
        plus_match = re.search(r'([A-Z0-9]{4,8}[+][A-Z0-9]{2,4})', normalized)
        if plus_match:
            results["plus_code"] = plus_match.group(1)
        else:
            suffix = re.search(r'([A-Z0-9]{2,4}\+[A-Z0-9]{2,4})', normalized)
            if suffix:
                prefix = re.search(
                    r'([A-Z0-9]{4,8})[\s\S]{0,50}?' + re.escape(suffix.group(1)),
                    normalized
                )
                results["plus_code"] = (
                    prefix.group(1) + suffix.group(1) if prefix else suffix.group(1)
                )

        # 2. KID
        kid = re.search(
            r'(09|०९)[\s\S]{0,50}?(\d{3})[\s\-\|]+(\d{3})[\s\-\|]+(\d{4})',
            normalized
        )
        if kid:
            results["kid"] = f"09-{kid.group(2)}-{kid.group(3)}-{kid.group(4)}"

        # 3. Ward Number - full format like "काठमाडौ महानगरपालिका , वडा नं २६"
        ward_full = re.search(
            r'([अ-ज्ञa-zA-Z\s]+(?:महानगरपालिका|नगरपालिका|गाउँपालिका|Municipality))'
            r'[\s,।]*(?:वडा|ward|Ward)[^\d०-९]*(\d+|[०-९]+)',
            clean, re.IGNORECASE
        )
        if ward_full:
            city = ward_full.group(1).strip()
            ward_num = _to_english_digits(ward_full.group(2))
            results["ward_no"] = f"{city}, वडा नं {ward_num}"
        else:
            ward_simple = re.search(
                r'(?:वडा|ward|Ward)[^\d०-९]*(\d+|[०-९]+)',
                clean, re.IGNORECASE
            )
            if ward_simple:
                results["ward_no"] = f"वडा नं {_to_english_digits(ward_simple.group(1))}"

        # 4. Location - known area names
        for loc in KNOWN_LOCATIONS:
            if loc in clean:
                results["location"] = loc
                break
        if "location" not in results:
            tole = re.search(
                r'([अ-ज्ञa-zA-Z०-९]+(?:\s+[अ-ज्ञa-zA-Z०-९]+)?)\s+(?:टोल|tole|Tole)',
                clean, re.IGNORECASE
            )
            if tole:
                results["location"] = tole.group(1).strip() + " टोल"

        # 5. Marga
        marga = re.search(
            r'([अ-ज्ञa-zA-Z0-9०-९]+\s+[अ-ज्ञa-zA-Z0-9०-९]+\s+'
            r'(?:मार्ग|Marg(?:a)?(?:[,\.]|\b)))',
            clean
        )
        if marga:
            results["marga"] = marga.group(1).strip()
        else:
            marga_single = re.search(
                r'([अ-ज्ञa-zA-Z0-9०-९]+\s+(?:मार्ग|Marg(?:a)?(?:[,\.]|\b)))',
                clean
            )
            if marga_single:
                results["marga"] = marga_single.group(1).strip()

        # 6. Kataho Code
        kataho = re.search(
            r'(09|०९)[\s\S]{0,30}?([अ-ज्ञ]{2,})\s+([अ-ज्ञ]{2,})'
            r'[\s\S]{0,15}?(\d{4}|[०-९]{4})',
            clean
        )
        if kataho:
            results["kataho_code"] = (
                f"{kataho.group(1)} {kataho.group(2)} "
                f"{kataho.group(3)} {_to_english_digits(kataho.group(4))}"
            )

        return results