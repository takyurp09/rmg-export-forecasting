// Query: fact_scenarios
// Source: pDataFolder & "fact_scenarios.csv" (UTF-8, comma-separated, header row)
// Grain: scenario x market x product group over a 12-month window. No date key; window is text.
// change_pct is a fraction (-0.10 = -10%). Scenarios 8 and 9 cover both markets.
let
    Source   = Csv.Document(File.Contents(pDataFolder & "fact_scenarios.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"scenario_key", Int64.Type}, {"scenario", type text}, {"market_key", Int64.Type}, {"product_key", Int64.Type},
        {"window", type text}, {"baseline_usd", type number}, {"scenario_usd", type number},
        {"change_usd", type number}, {"change_pct", type number}
    }, "en-US"),
    Result   = Typed
in
    Result
