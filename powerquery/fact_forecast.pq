// Query: fact_forecast
// Source: pDataFolder & "fact_forecast.csv" (UTF-8, comma-separated, header row)
// Grain: month x market x product x level. 12-month forecasts with 80% and 95% intervals.
// level = "Total" rows (product_key 15) and "Product group" rows must not be summed together.
let
    Source   = Csv.Document(File.Contents(pDataFolder & "fact_forecast.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"date_key", Int64.Type}, {"market_key", Int64.Type}, {"product_key", Int64.Type},
        {"level", type text}, {"model", type text}, {"point", type number},
        {"lo80", type number}, {"hi80", type number}, {"lo95", type number}, {"hi95", type number}
    }, "en-US"),
    Result   = Typed
in
    Result
