// Query: fact_exports
// Source: pDataFolder & "fact_exports.csv" (UTF-8, comma-separated, header row)
// Grain: month x market x product group. Monthly imports from Bangladesh, HS 61-62.
// No total rows (product_key 15 never appears). Totals come from summing.
let
    Source   = Csv.Document(File.Contents(pDataFolder & "fact_exports.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"date_key", Int64.Type}, {"market_key", Int64.Type}, {"product_key", Int64.Type},
        {"value_usd", type number}, {"value_usd_real2025", type number}, {"source", type text}
    }, "en-US"),
    Result   = Typed
in
    Result
