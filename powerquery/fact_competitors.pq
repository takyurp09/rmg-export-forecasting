// Query: fact_competitors
// Source: pDataFolder & "fact_competitors.csv" (UTF-8, comma-separated, header row)
// Grain: month x market x supplier country. US and EU27 apparel imports (HS 61+62)
// from Bangladesh and 8 competitors, plus a WORLD row (country_key 10) with the
// market total. share_pct is a percentage (0-100), not a fraction.
// Relationships: date -> dim_date[date], market -> dim_market[market],
// country_key -> dim_country[country_key].
let
    Source   = Csv.Document(File.Contents(pDataFolder & "fact_competitors.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"date", type date}, {"market", type text}, {"country_key", Int64.Type}, {"partner", type text},
        {"value_usd", type number}, {"market_total_usd", type number}, {"share_pct", type number}
    }, "en-US"),
    Result   = Typed
in
    Result
