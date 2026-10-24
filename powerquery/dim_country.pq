// Query: dim_country
// Source: pDataFolder & "dim_country.csv" (UTF-8, comma-separated, header row)
// Grain: one row per supplier country. Key: country_key. Key 10 (WORLD) is the
// market total row in fact_competitors; filter it out of share charts.
let
    Source   = Csv.Document(File.Contents(pDataFolder & "dim_country.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"country_key", Int64.Type}, {"partner", type text}, {"iso3", type text},
        {"country", type text}, {"is_bangladesh", type logical}
    }, "en-US"),
    Result   = Typed
in
    Result
