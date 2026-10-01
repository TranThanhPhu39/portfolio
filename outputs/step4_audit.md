# Step 4: Fama-French (2015) comparison

## Scope and sample

The comparison uses `SMALL LoBM`, value-weighted Size-B/M portfolio returns, and the July 1963–December 2013 sample (606 monthly observations). FF3 uses `Mkt-RF`, `SMB`, and `HML` from the FF3 factor file. FF5 uses `Mkt-RF`, `SMB`, `HML`, `RMW`, and `CMA` from the FF5 factor file. In both models, RF is subtracted from the portfolio return. Alpha is reported in percent per month; t-statistics are conventional OLS t-statistics.

## Table 7 comparison

Table 7 Panel A reports the FF3 intercept and t-stat for Small / Low B/M as **-0.49% per month** and **-5.18**. Panel B reports the FF5 values as **-0.29% per month** and **-3.31**, using `HML^O`. CAPM has no corresponding alpha/t-stat cell in Tables 5 or 7.

| Model | Variant | N | Alpha own | Alpha paper | Delta alpha | t own | t paper | Delta t | R² |
|---|---|---|---|---|---|---|---|---|---|
| CAPM | current FF3 source | 606 | -0.4479 | — | — | -2.2977 | — | — | 0.6449 |
| FF3 | current CSV | 606 | -0.4941 | -0.4900 | -0.0041 | -5.1490 | -5.1800 | 0.0310 | 0.9171 |
| FF3 | July 2014 archive | 606 | -0.5044 | -0.4900 | -0.0144 | -5.3495 | -5.1800 | -0.1695 | 0.9200 |
| FF3 | July 2015 archive | 606 | -0.5057 | -0.4900 | -0.0157 | -5.3614 | -5.1800 | -0.1814 | 0.9199 |
| FF5 | current CSV, raw HML | 606 | -0.2747 | -0.2900 | 0.0153 | -3.0569 | -3.3100 | 0.2531 | 0.9319 |
| FF5 | current CSV, HML^O | 606 | -0.2747 | -0.2900 | 0.0153 | -3.0569 | -3.3100 | 0.2531 | 0.9319 |
| FF5 | July 2015 archive, HML^O | 606 | -0.2892 | -0.2900 | 0.0008 | -3.2454 | -3.3100 | 0.0646 | 0.9333 |

The raw-HML and HML^O FF5 fits have the same alpha, t-stat(alpha), and R-squared within 1e-10 on the current factor file. This confirms the paper's equivalent reparameterization for the metrics being compared.

## Vintage check

The current local CSVs do not encode their source vintage. Official July 2014 FF3 and July 2015 FF3/FF5 factor archives were downloaded from the Kenneth French Data Library and compared on the same 606 dates. These are factor-vintage sensitivity runs only: the LHS portfolio remains the current local `25_portfolios_size_bm.csv`, so they are not full replications with a historical portfolio vintage.

Official archive sources: [FF3 history](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors_archive.html), [FF5 history](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3_archive.html). The downloaded ZIP files are the July 2014 FF3 text archive and July 2015 FF3/FF5 CSV archives.

- Current FF3: alpha -0.4941%/month, t -5.1490; Table 7 target -0.49 and -5.18.
- Current FF5 with HML^O: alpha -0.2747%/month, t -3.0569; Table 7 target -0.29 and -3.31.
- July 2015 archived FF5 factors with current LHS: alpha -0.2892%/month, t -3.2454. Its alpha rounds to the Table 7 value; its t-stat remains +0.0646 away from the published rounded value.
- The Table 7 FF3 result is closer using the current FF3 CSV than the July 2014 or July 2015 archived FF3 factors. Therefore vintage alone does not explain every difference.

The archived ZIPs identify the July 2014 and July 2015 CRSP data cuts. Their official archive pages state that archived factor files are annual July cuts. The current Data Library notes that U.S. research returns switched from FIZ to CIZ beginning January 2025, and that historical returns can change when CRSP revises its database. The accessed 25-portfolio entry exposes the current monthly series but no historical-vintage link, so the original 2015 LHS portfolio series could not be established from that entry.

## Table 5 Panel A aggregate comparison

Table 5 Panel A summarizes all 25 Size-B/M portfolios. The published FF3 `HML` row under 2x3 factors reports GRS 3.62, mean absolute alpha 0.102% per month, and mean-absolute-alpha/deviation ratio 0.54. The FF5 `HML RMW CMA` row reports GRS 2.84, mean absolute alpha 0.094% per month, and ratio 0.50. The team-side mean absolute alpha and ratio are calculated below for all 25 LHS portfolios, using the matched 606-month sample. GRS itself is not calculated here; it remains Step 5.

| Model | Variant | Portfolios | T | Mean abs alpha own | Mean abs alpha paper | Delta | Alpha/deviation own | Alpha/deviation paper |
|---|---|---|---|---|---|---|---|---|
| FF3 | current CSV | 25 | 606 | 0.0979 | 0.1020 | -0.0041 | 0.5285 | 0.5400 |
| FF3 | July 2014 archive | 25 | 606 | 0.0964 | 0.1020 | -0.0056 | 0.5208 | 0.5400 |
| FF3 | July 2015 archive | 25 | 606 | 0.0965 | 0.1020 | -0.0055 | 0.5214 | 0.5400 |
| FF5 | current CSV | 25 | 606 | 0.0939 | 0.0940 | -0.0001 | 0.5069 | 0.5000 |
| FF5 | July 2015 archive | 25 | 606 | 0.0886 | 0.0940 | -0.0054 | 0.4783 | 0.5000 |

For the current files, the team-side mean absolute alpha is 0.0979%/month for FF3 and 0.0939%/month for FF5. FF5 rounds to the published 0.094; FF3 is 0.0041 percentage points/month below 0.102. The corresponding ratios are 0.5285 versus 0.54 for FF3 and 0.5069 versus 0.50 for FF5.

## Audit conclusion

The Table 7 comparison is completed for the selected portfolio with model sources and units aligned. The Table 5 mean-absolute-alpha and ratio summaries are also computed for all 25 portfolios; GRS is reserved for Step 5. FF3 is close to the published rounded intercept and t-stat. Current-vintage FF5 differs more for SMALL LoBM; the July 2015 archived FF5 factors move that intercept to the published rounding, while the t-stat remains different. At the 25-portfolio level, current FF5 summary statistics are very close to Table 5. The HML^O transformation itself is not the source of the discrepancy. The remaining limitation is the unavailable matching 2015 vintage of the 25-portfolio LHS data, plus the lack of vintage metadata in the current local CSVs. No regression-logic error was found in the tested path.

The FF5 factor archive header identifies CRSP 201507 and the one-month T-bill source as Ibbotson and Associates. Archive ZIP SHA-256 values:

- `ff3_july2014.zip`: `e778483cfcf4041821601433a5e470fd4b255082fa0355b35f70307a515f68e9`
- `ff3_july2015.zip`: `d40f89a404b677d1bb071b1554acaa71ec50c7d50b46b1c2037e55230b0d1b4c`
- `ff5_july2015.zip`: `c50321fcd2e82b8a2350af3b14fb55cb8c4f17b2c82cc27eb598b3942ccb411f`

Current test-data SHA-256 values:

- `25_portfolios_size_bm.csv`: `8e5c97c32979efef10dfa07f2446d336d356bee0b5cc1232d6c59f6edee54b91`
- `ff3_factors_monthly.csv`: `490fa48b0a8e94b3b965576c0a203ccf5c70bf30cd25848968de47a996a6cce0`
- `ff5_factors_monthly.csv`: `1edb98f0db0a2ea056cec38fefa5e7b539eceae09679d2af07450a6795bef98f`
