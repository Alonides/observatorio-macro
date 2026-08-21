import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.official import (
    parse_bea_nipa,
    parse_bls_json,
    parse_boe_csv,
    parse_capex_tracker_csv,
    parse_dbnomics_json,
    parse_eia_json,
    parse_fed_ddp_csv,
    parse_h41_html,
    parse_mof_csv,
    parse_norges_html,
    parse_rrp_json,
    parse_sdmx_csv,
    parse_sofr_json,
    parse_treasury_csv,
)


class OfficialSourceParserTests(unittest.TestCase):
    def test_treasury_csv(self):
        text = 'Date,"2 Yr","10 Yr"\n08/20/2026,4.19,4.69\n'
        parsed = parse_treasury_csv(text)
        self.assertEqual(parsed["10 Yr"], [{"date": "2026-08-20", "value": 4.69}])

    def test_fed_ddp_csv_skips_metadata(self):
        text = '\n'.join([
            '"Series Description","Nominal Broad Dollar Index"',
            '"Unit:","Index"',
            '"Time Period","JRXWTFB_N.B"',
            '2026-08-13,119.1848',
            '2026-08-14,ND',
        ])
        parsed = parse_fed_ddp_csv(text)
        self.assertEqual(parsed["JRXWTFB_N.B"][-1]["value"], 119.1848)

    def test_sofr_json(self):
        payload = {"refRates": [{"effectiveDate": "2026-08-20", "percentRate": 3.63}]}
        self.assertEqual(parse_sofr_json(payload), [{"date": "2026-08-20", "value": 3.63}])

    def test_rrp_json_converts_dollars_to_billions_and_ignores_exercise(self):
        payload = {"repo": {"operations": [
            {"operationDate": "2026-08-20", "totalAmtAccepted": "125000000000", "note": ""},
            {"operationDate": "2026-08-20", "totalAmtAccepted": "1000000", "note": "Small value exercise"},
        ]}}
        self.assertEqual(parse_rrp_json(payload), [{"date": "2026-08-20", "value": 125.0}])

    def test_sdmx_csv(self):
        text = "KEY,TIME_PERIOD,OBS_VALUE\nDE10Y,2026-08-20,2.88\n"
        self.assertEqual(parse_sdmx_csv(text), [{"date": "2026-08-20", "value": 2.88}])

    def test_mof_and_boe_csv(self):
        self.assertEqual(
            parse_mof_csv("Interest rates,,,,\nDate,10-year\n2026/08/20,2.95\n"),
            [{"date": "2026-08-20", "value": 2.95}],
        )
        self.assertEqual(
            parse_boe_csv("DATE,IUDMNPY\n20 Aug 2026,4.71\n"),
            [{"date": "2026-08-20", "value": 4.71}],
        )

    def test_norges_html_selects_ten_year_column(self):
        html = "<table><tr>" + "".join(
            f"<td>{value}</td>" for value in ("2026-08-20", "3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "4.394")
        ) + "</tr></table>"
        self.assertEqual(parse_norges_html(html), [{"date": "2026-08-20", "value": 4.394}])

    def test_h41_html_preserves_thousands_separator(self):
        html = """
        <p><strong>Release Date:</strong> August 20, 2026</p>
        <p>Wednesday Aug 19, 2026</p>
        <table>
          <tr><td>Total assets</td><td>6,745,699</td></tr>
          <tr><td>U.S. Treasury, General Account</td><td>936,406</td></tr>
        </table>
        """
        parsed = parse_h41_html(html)
        self.assertEqual(parsed["WALCL"][0]["date"], "2026-08-19")
        self.assertEqual(parsed["WALCL"][0]["value"], 6745699.0)
        self.assertEqual(parsed["WTREGEN"][0]["value"], 936406.0)

    def test_bls_eia_and_bea(self):
        bls = {"status": "REQUEST_SUCCEEDED", "Results": {"series": [{
            "seriesID": "CUSR0000SA0",
            "data": [{"year": "2026", "period": "M07", "value": "329.2"}],
        }]}}
        self.assertEqual(parse_bls_json(bls)["CUSR0000SA0"][0], {"date": "2026-07-01", "value": 329.2})
        eia = {"response": {"data": [{"period": "2026-08-20", "value": "82.5"}]}}
        self.assertEqual(parse_eia_json(eia), [{"date": "2026-08-20", "value": 82.5}])
        bea = {"BEAAPI": {"Results": {"Data": [{
            "LineNumber": "1", "LineDescription": "Gross domestic product",
            "TimePeriod": "2026Q2", "DataValue": "31,250.4",
        }]}}}
        self.assertEqual(parse_bea_nipa(bea, "Gross domestic product"), [{"date": "2026-06-30", "value": 31250.4}])
        dbnomics = {"series": {"docs": [{"period": ["2026-Q1", "2026-Q2"], "value": [31000, 31250.4]}]}}
        self.assertEqual(parse_dbnomics_json(dbnomics)[-1], {"date": "2026-06-30", "value": 31250.4})
        scaled = parse_dbnomics_json(dbnomics, divisor=1_000)[-1]
        self.assertEqual(scaled["date"], "2026-06-30")
        self.assertAlmostEqual(scaled["value"], 31.2504)

    def test_capex_tracker_uses_headline_basis_and_quarter_end(self):
        text = """# License: CC BY 4.0
company,ticker,period,period_end,cash_capex_usd,headline_usd,headline_basis
microsoft,MSFT,2026-Q2,2026-06-30,35802000000,41000000000,capex_including_finance_leases
alphabet,GOOGL,2026-Q2,2026-06-30,44900000000,44900000000,cash_capex
"""
        parsed = parse_capex_tracker_csv(text)
        self.assertEqual(parsed["CAPEX_MSFT"], [{"date": "2026-06-30", "value": 41.0}])
        self.assertEqual(parsed["CAPEX_GOOG"], [{"date": "2026-06-30", "value": 44.9}])


if __name__ == "__main__":
    unittest.main()
