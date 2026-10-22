// Query: dim_date
// Source: pDataFolder & "dim_date.csv" (UTF-8, comma-separated, header row)
// Grain: one row per month, Jan 1999 to Aug 2027. Key: date_key (yyyymmdd, first of month).
// Mark as date table on [date]; sort month_name by month.
let
    Source   = Csv.Document(File.Contents(pDataFolder & "dim_date.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
        {"date_key", Int64.Type}, {"date", type date}, {"year", Int64.Type}, {"quarter", Int64.Type},
        {"month", Int64.Type}, {"month_name", type text}, {"bd_fiscal_year", Int64.Type}
    }, "en-US"),
    Result   = Table.Sort(Typed, {{"date", Order.Ascending}})
in
    Result
