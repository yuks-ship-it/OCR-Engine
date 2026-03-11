# backend/app/services/field_parser.py
import re

class FieldParser:
    def parse(self, text: str):
        """
        Parses OCR text to extract specific fields like Plus Code, Ward Number, and House Address.
        """
        results = {}
        # Normalize text to handle common OCR substitutions
        text_clean = text.replace('\n', ' ').replace('=', '-').strip()
        
        # Nepali digit normalization for Plus Codes (e.g., ९६+४R८ -> 96+4R8)
        nep_to_eng = str.maketrans('०१२३४५६७८९', '0123456789')
        text_normalized = text_clean.translate(nep_to_eng)
        
        # 1. Extract Plus Code (e.g. fragments "7MV7P8" and "76+G68")
        plus_suffix = re.search(r'([A-Z0-9]{2,4}\+[A-Z0-9]{2,4})', text_normalized)
        if plus_suffix:
            plus_part = plus_suffix.group(1)
            # Find the 4-8 char prefix anywhere up to 40 characters before the suffix
            prefix = re.search(r'([A-Z0-9]{4,8})[\s\S]{0,40}?' + re.escape(plus_part), text_normalized)
            if prefix:
                results["plus_code"] = prefix.group(1) + plus_part
            else:
                results["plus_code"] = plus_part

        # 2. Extract KID (e.g. fragments "09" and "294-116-1848")
        # Finds 09, then up to 40 chars of noise, then the 3-3-4 digit blocks
        kid_match = re.search(r'(09|०९)[\s\S]{0,40}?(\d{3})[\s\-\|lI]+(\d{3})[\s\-\|lI]+(\d{4})', text_normalized)
        if kid_match:
            results["kid"] = f"09-{kid_match.group(2)}-{kid_match.group(3)}-{kid_match.group(4)}"

        # 3. Extract Kataho Code (e.g. "०९ सार्ग लक्ष जुरेली Plus १८४८" -> "०९ लक्ष जुरेली १८४८")
        # Looks for 09, then 2 Nepali words, then 4 digits, ignoring noise in between
        kataho_match = re.search(r'(09|०९)[\s\S]{0,30}?([अ-ज्ञ]{2,})\s+([अ-ज्ञ]{2,})[\s\S]{0,15}?(\d{4}|[०-९]{4})', text_clean)
        if kataho_match:
            results["kataho_code"] = f"{kataho_match.group(1)} {kataho_match.group(2)} {kataho_match.group(3)} {kataho_match.group(4)}"
            
        # 4. Extract Marga (grab up to 2 words before 'मार्ग')
        marga_match = re.search(r'([अ-ज्ञa-zA-Z0-9०-९]+\s+[अ-ज्ञa-zA-Z0-9०-९]+\s+(?:मार्ग|सार्ग|Marg|Marga(?:[,\.]|\b)))', text_clean)
        if marga_match:
            results["marga"] = marga_match.group(1).replace('सार्ग', 'मार्ग')
        else:
            # Fallback to just 1 word
            marga_match_single = re.search(r'([अ-ज्ञa-zA-Z0-9०-९]+\s+(?:मार्ग|सार्ग|Marg|Marga(?:[,\.]|\b)))', text_clean)
            if marga_match_single:
                results["marga"] = marga_match_single.group(1).replace('सार्ग', 'मार्ग')

        return results