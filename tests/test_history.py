import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.history import (
    _parse_fed_ddp,
    _parse_sdmx_csv,
    _parse_treasury_csv,
    _TableParser,
)


class HistoryParserTests(unittest.TestCase):
    def test_treasury_parser_filters_missing_values(self):
        text = "Date,10 Yr,30 Yr\n01/02/2026,4.25,4.80\n01/05/2026,N/A,4.82\n"
        points = _parse_treasury_csv(text, "30 Yr")
        self.assertEqual(points, [
            {"date": "2026-01-02", "value": 4.8},
            {"date": "2026-01-05", "value": 4.82},
        ])

    def test_fed_ddp_parser_skips_metadata_and_missing(self):
        text = (
            "Title,Example\n"
            "Time Period,JRXWTFB_N.B\n"
            "2026-01-02,101.5\n"
            "2026-01-05,ND\n"
        )
        self.assertEqual(
            _parse_fed_ddp(text, "JRXWTFB_N.B"),
            [{"date": "2026-01-02", "value": 101.5}],
        )

    def test_sdmx_parser_accepts_semicolon_delimiter(self):
        text = "KEY;TIME_PERIOD;OBS_VALUE\nX;2026-01-02;3.10\nX;2026-01-05;3.12\n"
        self.assertEqual(
            _parse_sdmx_csv(text),
            [
                {"date": "2026-01-02", "value": 3.1},
                {"date": "2026-01-05", "value": 3.12},
            ],
        )

    def test_html_table_parser_preserves_cells(self):
        parser = _TableParser()
        parser.feed("<table><tr><th>Date</th><th>10Y</th></tr><tr><td>2026-01-02</td><td>4.1</td></tr></table>")
        self.assertEqual(parser.rows, [["Date", "10Y"], ["2026-01-02", "4.1"]])


if __name__ == "__main__":
    unittest.main()
