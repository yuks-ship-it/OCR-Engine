import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'app')))
from services.field_parser import FieldParser

parser = FieldParser()

tests = [
    "Ward No. 5\n7MV7+VG Kathmandu\nMain Road Tole",
    "वडा नं ५\n7MV7+VG\nHouse No. 123",
    "Ward: 05, 8MV8+VG, Street Name",
    "WARD NUMBER 12\nSome random text\nBoudha Tole",
]

for t in tests:
    print(f"Text: {t}")
    print(f"Parsed: {parser.parse(t)}")
    print("-" * 20)
