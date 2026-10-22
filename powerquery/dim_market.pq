// Query: dim_market
// Source: pDataFolder & "dim_market.csv" (UTF-8, comma-separated, header row)
// Grain: one row per importing market (1 = US, 2 = EU). Key: market_key.
let
    Source   = Csv.Document(File.Contents(pDataFolder & "dim_market.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"market_key", Int64.Type}, {"market", type text}, {"market_name", type text}, {"reporter_basis", type text}
    }, "en-US"),
    Result   = Typed
in
    Result
