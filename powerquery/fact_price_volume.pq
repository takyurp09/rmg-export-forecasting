// Query: fact_price_volume
// Source: pDataFolder & "fact_price_volume.csv" (UTF-8, comma-separated, header row)
// Grain: month x hs_code, EU27 imports from Bangladesh only (market_key 2).
// hs_code holds "61", "62", "61+62" (product_key 2, 12, 15) and nine HS4 headings
// (product_key blank). The rows overlap: sum only hs_code "61" and "62" for a total.
// Keep hs_code as text.
let
    Source   = Csv.Document(File.Contents(pDataFolder & "fact_price_volume.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"date_key", Int64.Type}, {"market_key", Int64.Type}, {"product_key", Int64.Type}, {"hs_code", type text},
        {"value_usd", type number}, {"value_eur", type number}, {"qty_kg", type number},
        {"unit_value_usd_per_kg", type number}, {"unit_value_eur_per_kg", type number}, {"source", type text}
    }, "en-US"),
    Result   = Typed
in
    Result
